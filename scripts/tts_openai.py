import os
import json
from openai import OpenAI

TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)

    with open("story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    text = " ".join([s.strip() for s in story.get("segments", []) if isinstance(s, str) and s.strip()])
    if not text:
        raise ValueError("No text found in story.json segments.")

    audio = client.audio.speech.create(
        model=TTS_MODEL,
        voice=VOICE,
        input=text,
        format="mp3",
    )

    with open("voice.mp3", "wb") as f:
        f.write(audio.read())

    print("OK: voice.mp3 generated")

if __name__ == "__main__":
    main()
