import json

WPM = 165  # palabras/min aproximado
PAD_START = 0.25
PAD_END = 0.15

def sec_to_ts(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def est_duration(text: str) -> float:
    words = max(1, len(text.split()))
    return (words / WPM) * 60.0

def main():
    with open("story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    segments = [s.strip() for s in story.get("segments", []) if isinstance(s, str) and s.strip()]
    if not segments:
        raise ValueError("No segments found for subtitles.")

    t = 0.0
    blocks = []
    idx = 1

    for seg in segments:
        d = est_duration(seg)
        start = t + PAD_START
        end = t + d + PAD_END
        blocks.append(f"{idx}\n{sec_to_ts(start)} --> {sec_to_ts(end)}\n{seg}\n")
        idx += 1
        t += d

    with open("subs.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))

    print("OK: subs.srt generated")

if __name__ == "__main__":
    main()
