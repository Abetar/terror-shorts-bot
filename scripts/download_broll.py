import os
import json
import random
import urllib.parse
import urllib.request

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
OUT_DIR = os.getenv("BROLL_DIR", "out/broll")

PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"

def die(msg: str):
    raise RuntimeError(msg)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def pick_best_file(video_obj: dict) -> str:
    """
    Escoge un mp4 razonable (>=720p si existe), priorizando vertical si aparece,
    si no, el más grande disponible.
    """
    files = video_obj.get("video_files") or []
    if not files:
        return ""

    # Ordena por resolución (width*height) desc
    files_sorted = sorted(
        files,
        key=lambda f: (int(f.get("width", 0)) * int(f.get("height", 0))),
        reverse=True
    )

    # Preferir >= 720p
    for f in files_sorted:
        w = int(f.get("width", 0))
        h = int(f.get("height", 0))
        link = f.get("link") or ""
        if link and (w >= 720 or h >= 720):
            return link

    # Si no, el mejor que haya
    return files_sorted[0].get("link") or ""

def pexels_search(query: str, per_page: int = 10) -> list:
    if not PEXELS_API_KEY:
        die("PEXELS_API_KEY is missing. Add it as a GitHub Actions secret.")

    params = {
        "query": query,
        "per_page": str(per_page),
        "orientation": "portrait",  # ayuda para shorts
        "size": "large",
    }
    url = PEXELS_VIDEO_SEARCH + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("Authorization", PEXELS_API_KEY)

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data.get("videos") or []

def download_file(url: str, out_path: str):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp, open(out_path, "wb") as f:
        f.write(resp.read())

def main():
    with open("story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    visual_plan = story.get("visual_plan")
    if not isinstance(visual_plan, list) or len(visual_plan) != 3:
        die("story.json must include visual_plan with exactly 3 items.")

    ensure_dir(OUT_DIR)

    for i, block in enumerate(visual_plan, start=1):
        kws = block.get("keywords")
        if not isinstance(kws, list) or not kws:
            die("Each visual_plan item must have keywords list.")

        # query tipo: "security camera hallway night"
        query = " ".join([k.strip() for k in kws if isinstance(k, str) and k.strip()])
        if not query:
            die("visual_plan keywords are empty.")

        print(f"[broll] Searching Pexels for: {query}")
        videos = pexels_search(query, per_page=12)

        if not videos:
            # fallback: query más genérico
            fallback = "dark hallway night"
            print(f"[broll] No results. Fallback search: {fallback}")
            videos = pexels_search(fallback, per_page=12)

        if not videos:
            die("No Pexels videos found (even fallback).")

        chosen = random.choice(videos)
        link = pick_best_file(chosen)
        if not link:
            die("Could not pick a downloadable video file from Pexels response.")

        out_path = os.path.join(OUT_DIR, f"clip{i}.mp4")
        print(f"[broll] Downloading clip{i} -> {out_path}")
        download_file(link, out_path)

    print("OK: B-roll clips downloaded to out/broll/")

if __name__ == "__main__":
    main()
