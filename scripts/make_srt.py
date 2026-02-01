import os
from openai import OpenAI

def sec_to_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def clamp_text(t: str) -> str:
    t = " ".join((t or "").strip().split())
    return t

def wrap_two_lines(text: str, max_chars: int = 22) -> str:
    """
    Rompe en 1-2 líneas para que NO tape pantalla.
    """
    words = text.split()
    if not words:
        return ""
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
            if len(lines) == 2:
                break
    if cur and len(lines) < 2:
        lines.append(cur)
    return "\n".join(lines[:2]).strip()

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    if not os.path.exists("voice.mp3"):
        raise RuntimeError("voice.mp3 not found. Run tts first.")

    client = OpenAI(api_key=api_key)

    # Whisper para timestamps reales
    with open("voice.mp3", "rb") as f:
        tr = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            language="es",
        )

    segments = getattr(tr, "segments", None) or tr.get("segments") or []
    if not segments:
        raise RuntimeError("No transcription segments returned by whisper.")

    blocks = []
    idx = 1
    for seg in segments:
        start = float(seg["start"])
        end = float(seg["end"])
        text = clamp_text(seg.get("text", ""))
        if not text:
            continue

        text = wrap_two_lines(text, max_chars=24)

        blocks.append(
            f"{idx}\n{sec_to_ts(start)} --> {sec_to_ts(end)}\n{text}\n"
        )
        idx += 1

    if idx == 1:
        raise RuntimeError("No subtitle blocks created.")

    with open("subs.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))

    print(f"OK: subs.srt generated from whisper ({idx-1} blocks)")

if __name__ == "__main__":
    main()
