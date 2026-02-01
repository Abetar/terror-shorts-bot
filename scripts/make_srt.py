import os
import re
from openai import OpenAI

MAX_CHARS = 14          # por línea (duro)
MAX_LINES = 2
MIN_BLOCK_SEC = 0.55    # no tan rápido
MAX_BLOCK_SEC = 1.80    # no tan lento

def sec_to_ts(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def clean_text(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("“", '"').replace("”", '"').replace("’", "'")
    return t

def break_long_words(text: str, max_len: int) -> str:
    """
    Si una palabra sola es más larga que max_len, la partimos con guion.
    """
    out = []
    for w in text.split():
        if len(w) <= max_len:
            out.append(w)
        else:
            # cortar en piezas de max_len-1 + "-"
            i = 0
            while i < len(w):
                part = w[i:i + (max_len - 1)]
                i += (max_len - 1)
                if i < len(w):
                    out.append(part + "-")
                else:
                    out.append(part)
    return " ".join(out)

def wrap_lines(chunk: str, max_chars: int) -> str:
    """
    1–2 líneas, cada una <= max_chars.
    """
    words = chunk.split()
    if not words:
        return ""

    lines = []
    cur = ""

    for w in words:
        add = (cur + " " + w).strip()
        if len(add) <= max_chars:
            cur = add
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) >= MAX_LINES - 1:
                break

    if cur and len(lines) < MAX_LINES:
        lines.append(cur)

    return "\n".join(lines[:MAX_LINES]).strip()

def split_into_chunks(text: str, max_chars: int) -> list[str]:
    """
    Chunking pensado para que después wrap_lines NO explote.
    En vez de max_chars*MAX_LINES, usamos un límite un poco menor
    para forzar 1–2 líneas cortas.
    """
    words = text.split()
    if not words:
        return []

    # límite por bloque (2 líneas pero conservador)
    max_len = (max_chars * MAX_LINES) - 2  # margen extra
    chunks = []
    cur = ""

    for w in words:
        add = (cur + " " + w).strip()
        if len(add) <= max_len:
            cur = add
        else:
            if cur:
                chunks.append(cur)
            cur = w

    if cur:
        chunks.append(cur)

    return chunks

def seg_get(seg, key: str, default=None):
    if hasattr(seg, key):
        return getattr(seg, key)
    if isinstance(seg, dict):
        return seg.get(key, default)
    return default

def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    if not os.path.exists("voice.mp3"):
        raise RuntimeError("voice.mp3 not found.")

    client = OpenAI(api_key=api_key)

    with open("voice.mp3", "rb") as f:
        tr = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            language="es",
        )

    segments = getattr(tr, "segments", None) or (tr.get("segments") if isinstance(tr, dict) else None) or []
    if not segments:
        raise RuntimeError("No transcription segments returned by whisper.")

    blocks = []
    idx = 1

    for seg in segments:
        start = float(seg_get(seg, "start", 0.0))
        end = float(seg_get(seg, "end", 0.0))
        text = clean_text(seg_get(seg, "text", "") or "")

        if not text or end <= start:
            continue

        # rompe palabras largas ANTES de chunking
        text = break_long_words(text, MAX_CHARS)

        dur = end - start
        chunks = split_into_chunks(text, MAX_CHARS)
        if not chunks:
            continue

        # reparto por longitud (pero luego normalizamos para no pasarnos de end)
        lengths = [max(1, len(c)) for c in chunks]
        total = sum(lengths)

        # genera porciones clamp
        portions = []
        for L in lengths:
            p = dur * (L / total)
            p = clamp(p, MIN_BLOCK_SEC, MAX_BLOCK_SEC)
            portions.append(p)

        # normaliza porciones para que sumen <= dur (si clamp infló)
        sum_p = sum(portions)
        if sum_p > dur and sum_p > 0:
            scale = dur / sum_p
            portions = [p * scale for p in portions]

        t = start
        for c, p in zip(chunks, portions):
            t2 = min(end, t + p)
            wrapped = wrap_lines(c, MAX_CHARS)

            if wrapped:
                blocks.append(
                    f"{idx}\n{sec_to_ts(t)} --> {sec_to_ts(t2)}\n{wrapped}\n"
                )
                idx += 1

            t = t2
            if t >= end - 0.03:
                break

    if idx == 1:
        raise RuntimeError("No subtitle blocks created.")

    with open("subs.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(blocks))

    print(f"OK: subs.srt generated (tiktok chunks) ({idx-1} blocks)")

if __name__ == "__main__":
    main()
