import os
import json
import math
import re
import subprocess
import urllib.parse
import random

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").replace("\r", "").replace("\n", "").strip()
OUT_DIR = os.getenv("BROLL_DIR", "out/broll")
PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"

STOP_WORDS = {
    "sound", "whispering", "silence", "audio", "voice", "sfx", "music",
    "zoom", "slow", "vibe", "atmosphere", "mood"
}

FALLBACKS = [
    "dark hallway apartment night",
    "security camera hallway night",
    "door chain lock night",
    "stairs apartment night",
    "elevator hallway night",
    "shadow wall night",
    "empty corridor night",
    "street night fog",
]

def die(msg: str):
    raise RuntimeError(msg)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def curl_json(url: str) -> dict:
    if not PEXELS_API_KEY:
        die("PEXELS_API_KEY is missing. Add GitHub secret PEXELS_API_KEY.")

    cmd = [
        "curl", "-sS", "--fail",
        "-H", f"Authorization: {PEXELS_API_KEY}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: terror-shorts-bot/1.0",
        url
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=30)
    except subprocess.CalledProcessError as e:
        body = e.output.decode("utf-8", errors="replace")
        die(f"[pexels] curl failed. Output:\n{body[:600]}")
    except subprocess.TimeoutExpired:
        die("[pexels] curl timed out.")

    try:
        return json.loads(out.decode("utf-8"))
    except json.JSONDecodeError as e:
        die(f"[pexels] curl returned non-JSON: {e}")

def download_file(url: str, out_path: str):
    cmd = [
        "curl", "-L", "-sS", "--fail",
        "-H", "User-Agent: terror-shorts-bot/1.0",
        url, "-o", out_path
    ]
    try:
        subprocess.check_call(cmd, timeout=120)
    except subprocess.CalledProcessError as e:
        die(f"[broll] Download failed for {url}: {e}")
    except subprocess.TimeoutExpired:
        die(f"[broll] Download timed out for {url}")

def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def sanitize_keywords(keywords: list[str]) -> list[str]:
    clean = []
    for k in keywords:
        k = norm(str(k))
        if not k:
            continue
        # si viene como frase, separamos
        parts = [p for p in k.split() if p and p not in STOP_WORDS]
        clean.extend(parts)
    # dedupe preservando orden
    seen = set()
    out = []
    for w in clean:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:10]

def build_query(words: list[str]) -> str:
    """
    Construye un query más "stock-friendly":
    - prioriza 4-6 palabras máximo
    - intenta meter 'night' si no está
    - evita palabras vagas
    """
    if not words:
        return random.choice(FALLBACKS)

    # empuja night si no viene
    if "night" not in words and "dark" in words:
        words = words + ["night"]

    # frases típicas que sí regresan contenido
    preferred_order = ["dark", "night", "hallway", "corridor", "apartment", "door", "stairs", "elevator", "shadow", "mirror", "phone", "security", "camera"]
    ordered = []
    for p in preferred_order:
        if p in words and p not in ordered:
            ordered.append(p)

    # agrega el resto
    for w in words:
        if w not in ordered:
            ordered.append(w)

    query = " ".join(ordered[:6]).strip()
    if len(query.split()) < 3:
        query = random.choice(FALLBACKS)
    return query

def pexels_search(query: str, per_page: int = 18) -> list:
    params = {
        "query": query,
        "per_page": str(per_page),
        "orientation": "portrait",  # intentamos vertical
        "size": "large",
    }
    url = PEXELS_VIDEO_SEARCH + "?" + urllib.parse.urlencode(params)
    data = curl_json(url)
    return data.get("videos") or []

def pick_best_file(video_obj: dict) -> dict:
    """
    Regresa el mejor archivo descargable (dict con link/width/height).
    """
    files = video_obj.get("video_files") or []
    if not files:
        return {}

    # Ordena por área (resolución)
    files_sorted = sorted(
        files,
        key=lambda f: (int(f.get("width", 0)) * int(f.get("height", 0))),
        reverse=True
    )

    # preferimos >= 1080 en el lado largo si existe
    for f in files_sorted:
        w = int(f.get("width", 0))
        h = int(f.get("height", 0))
        link = f.get("link") or ""
        if link and max(w, h) >= 1080:
            return {"link": link, "width": w, "height": h}

    # si no, >= 720
    for f in files_sorted:
        w = int(f.get("width", 0))
        h = int(f.get("height", 0))
        link = f.get("link") or ""
        if link and max(w, h) >= 720:
            return {"link": link, "width": w, "height": h}

    f0 = files_sorted[0]
    return {"link": f0.get("link") or "", "width": int(f0.get("width", 0)), "height": int(f0.get("height", 0))}

def score_video(video_obj: dict, query_words: list[str], target_sec: float) -> float:
    """
    Puntaje: más alto mejor.
    - resolución grande
    - duración cerca de target
    - match de palabras en metadata (lo poco que haya)
    """
    duration = float(video_obj.get("duration") or 0)
    best = pick_best_file(video_obj)
    w = best.get("width", 0)
    h = best.get("height", 0)
    area = max(1, w * h)

    # match textual: Pexels trae url y user.name; a veces es lo único
    text = norm(str(video_obj.get("url", ""))) + " " + norm(str((video_obj.get("user") or {}).get("name", "")))

    hits = 0
    for qw in query_words:
        if qw and qw in text:
            hits += 1

    # score parts
    res_score = math.log(area)  # log para no explotar
    dur_penalty = abs(duration - target_sec)  # menor es mejor
    hit_score = hits * 1.8

    # si el video no es vertical, penaliza un poco
    vertical_bonus = 0.0
    if w and h:
        if h >= w:
            vertical_bonus = 1.2
        else:
            vertical_bonus = -0.8

    return res_score + hit_score + vertical_bonus - (dur_penalty * 0.25)

def choose_best_video(videos: list, query_words: list[str], target_sec: float) -> dict:
    ranked = []
    for v in videos:
        s = score_video(v, query_words, target_sec)
        ranked.append((s, v))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1] if ranked else {}

def main():
    print(f"[broll] PEXELS_API_KEY length: {len(PEXELS_API_KEY)}")
    if len(PEXELS_API_KEY) < 20:
        die("PEXELS_API_KEY looks too short. Check GitHub secret PEXELS_API_KEY.")

    with open("story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    visual_plan = story.get("visual_plan")
    if not isinstance(visual_plan, list) or len(visual_plan) != 3:
        die("story.json must include visual_plan with exactly 3 items.")

    ensure_dir(OUT_DIR)

    for i, block in enumerate(visual_plan, start=1):
        kws = block.get("keywords")
        target_sec = float(block.get("duration_sec") or 14)

        if not isinstance(kws, list) or not kws:
            kws = []

        words = sanitize_keywords([str(k) for k in kws])
        query = build_query(words)
        query_words = query.split()

        print(f"[broll] Searching Pexels for: {query} (target ~{target_sec}s)")
        videos = pexels_search(query, per_page=24)

        if not videos:
            fb = random.choice(FALLBACKS)
            print(f"[broll] No results. Fallback search: {fb}")
            videos = pexels_search(fb, per_page=24)
            query = fb
            query_words = fb.split()

        if not videos:
            die("No Pexels videos found (even fallback).")

        chosen = choose_best_video(videos, query_words, target_sec)
        best = pick_best_file(chosen)
        link = best.get("link") or ""
        if not link:
            die("Could not pick a downloadable video file from Pexels response.")

        out_path = os.path.join(OUT_DIR, f"clip{i}.mp4")
        print(f"[broll] Downloading clip{i} -> {out_path}")
        download_file(link, out_path)

        size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        print(f"[broll] clip{i} size: {size} bytes")
        if size < 250_000:
            die(f"[broll] clip{i} looks too small. Download likely failed/blocking.")

    print("OK: B-roll clips downloaded to out/broll/")

if __name__ == "__main__":
    main()
