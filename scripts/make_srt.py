import json

WPM = 155  # más realista para narración lenta/tense
PAD_START = 0.20
PAD_END = 0.20
MAX_LINE_CHARS = 34  # para celular, evita líneas largas

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

def wrap_two_lines(text: str) -> str:
    """Corta a máximo 2 líneas, intentando partir por espacios cerca del centro."""
    t = " ".join(text.split())
    if len(t) <= MAX_LINE_CHARS:
        return t

    # Si es muy largo, intenta partir en dos líneas
    mid = len(t) // 2
    # busca el espacio más cercano al medio
    left = t.rfind(" ", 0, mid)
    right = t.find(" ", mid)
    if left == -1 and right == -1:
        return t  # sin espacios (raro)
    if left == -1:
        cut = right
    elif right == -1:
        cut = left
    else:
        cut = left if (mid - left) <= (right - mid) else right

    line1 = t[:cut].strip()
    line2 = t[cut:].strip()

    # Si la segunda línea sigue siendo enorme, no hacemos 3 líneas; la dejamos así.
    return f"{line1}\n{line2}"

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

        subtitle_text = wrap_two_lines(seg)
        blocks.append(f"{idx}\n{sec_to_ts(start)} --> {sec_to_ts(end)}\n{subtitle_text}\n")

        idx += 1
        t += d

    with open("subs.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))

    print("OK: subs.srt generated")

if __name__ == "__main__":
    main()
