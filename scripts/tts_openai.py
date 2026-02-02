import os
import json
import re
from openai import OpenAI

TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")

# 0 = NO CTA (final silencioso)  |  1 = agrega CTA al final del audio
INCLUDE_CTA_AUDIO = os.getenv("INCLUDE_CTA_AUDIO", "0").strip() == "1"

# pausa entre frases (en saltos de línea). 2 = más pausa.
LINE_BREAKS_BETWEEN = int(os.getenv("TTS_LINE_BREAKS", "2"))  # 1 o 2 recomendado

def clean_text(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"\s+", " ", t)
    # normaliza comillas raras
    t = t.replace("“", '"').replace("”", '"').replace("’", "'")
    return t

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)

    with open("story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    segments = [
        clean_text(s)
        for s in story.get("segments", [])
        if isinstance(s, str) and clean_text(s)
    ]
    if not segments:
        raise ValueError("No text found in story.json segments.")

    # Pausas naturales SIN instrucciones:
    # - saltos de línea = pausas
    # - elipsis unicode = micro pausa
    sep = ("…\n" * max(1, LINE_BREAKS_BETWEEN)).rstrip("\n") + "\n"
    body = sep.join(segments).strip()

    text = body

    # CTA opcional (para A/B testing)
    if INCLUDE_CTA_AUDIO:
        cta = clean_text(story.get("cta", ""))
        if cta:
            # pausa más larga antes del CTA
            text = text + "\n\n…\n\n" + cta

    audio = client.audio.speech.create(
        model=TTS_MODEL,
        voice=VOICE,
        input=text,
        response_format="mp3",
    )

    with open("voice.mp3", "wb") as f:
        f.write(audio.read())

    print("OK: voice.mp3 generated")
    print(f"INCLUDE_CTA_AUDIO={int(INCLUDE_CTA_AUDIO)}  LINE_BREAKS={LINE_BREAKS_BETWEEN}")

if __name__ == "__main__":
    main()
