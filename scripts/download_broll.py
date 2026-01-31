import os
import json
import random
import subprocess
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").replace("\r", "").replace("\n", "").strip()
OUT_DIR = os.getenv("BROLL_DIR", "out/broll")

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"

STOP_WORDS = {"sound", "whispering", "silence", "audio", "voice", "sfx", "music", "zoom", "slow"}

def die(msg: str):
    raise RuntimeError(msg)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def sanitize_keywords(keywords: list[str]) -> str:
    clean = []
    for k in keywords:
        k = (k or "").strip().lower()
        if not k or k in STOP_WORDS:
            continue
        k = "".join(ch for ch in k if ch.isalnum() or ch.isspace())
        k = " ".join(k.split())
        if k:
            clean.append(k)
    if not clean:
        return ""
    return " ".join(clean[:6])

def pick_best_file(video_obj: dict) -> str:
    files = video_obj.get("video_files") or []
    if not files:
        return ""
    files_sorted = sorted(
        files,
        key=lambda f: (int(f.get("width", 0)) * int(f.get("height", 0))),
        reverse=True
    )
    for f in files_sorted:
        w = int(f.get("width", 0))
        h = int(f.get("height", 0))
        link = f.get("link") or ""
        if link and (w >= 720 or h >= 720):
            return link
    return files_sorted[0].get("link") or ""

def curl_json(url: str) -> dict:
    if not PEXELS_API_KEY:
        die("PEXELS_API_KEY is missing. Add GitHub secret PEXELS_API_KEY.")

    # curl suele pasar Cloudflare donde urllib falla
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

def pexels_search(query: str, per_page: int = 10) -> list:
    if not PEXELS_API_KEY:
        die("PEXELS_API_KEY is missing. Add it as a GitHub Actions secret named PEXELS_API_KEY.")

    params = {
        "query": query,
        "per_page": str(per_page),
        "orientation": "portrait",
        "size": "large",
    }
    url = PEXELS_VIDEO_SEARCH + "?" + urllib.parse.urlencode(params)

    # 1) Intento con curl (más fiable en GitHub Actions)
    data = curl_json(url)
    return data.get("videos") or []

def download_file(url: str, out_path: str):
    # Descarga también con curl para evitar bloqueos
    cmd = [
        "curl", "-L", "-sS", "--fail",
        "-H", "User-Agent: terror-shorts-bot/1.0",
        url, "-o", out_path
    ]
    try:
        subprocess.check_call(cmd, timeout=90)
    except subprocess.CalledProcessError as e:
        die(f"[broll] Download failed for {url}: {e}")
    except subprocess.TimeoutExpired:
        die(f"[broll] Download timed out for {url}")

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

    fallbacks = [
        "security camera hallway night",
        "dark hallway night",
        "empty corridor night",
        "street night fog",
        "door shadow silhouette"
    ]

    for i, block in enumerate(visual_plan, start=1):
        kws = block.get("keywords")
        if not isinstance(kws, list) or not kws:
            die("Each visual_plan item must have keywords list.")

        query = sanitize_keywords([str(k) for k in kws])
        if not query:
            query = random.choice(fallbacks)

        print(f"[broll] Searching Pexels for: {query}")
        videos = pexels_search(query, per_page=12)

        if not videos:
            fb = random.choice(fallbacks)
            print(f"[broll] No results. Fallback search: {fb}")
            videos = pexels_search(fb, per_page=12)

        if not videos:
            die("No Pexels videos found (even fallback).")

        chosen = random.choice(videos)
        link = pick_best_file(chosen)
        if not link:
            die("Could not pick a downloadable video file from Pexels response.")

        out_path = os.path.join(OUT_DIR, f"clip{i}.mp4")
        print(f"[broll] Downloading clip{i} -> {out_path}")
        download_file(link, out_path)

        # Verificación tamaño
        size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        print(f"[broll] clip{i} size: {size} bytes")
        if size < 200_000:  # demasiado pequeño = descarga mala
            die(f"[broll] clip{i} looks too small. Download likely failed/blocking.")

    print("OK: B-roll clips downloaded to out/broll/")

if __name__ == "__main__":
    main()
