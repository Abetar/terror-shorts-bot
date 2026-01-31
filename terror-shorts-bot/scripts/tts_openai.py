import os, json
from openai import OpenAI

TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")  # hay varias voces; alloy suele ser neutral

def main():
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    with open("story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    text = " ".join([s.strip() for s in story["segments"] if s.strip()])

    # Audio API speech
    audio = client.audio.speech.create(
        model=TTS_MODEL,
        voice=VOICE,
        input=text,
        format="mp3",
    )

    with open("voice.mp3", "wb") as f:
        f.write(audio.read())

    print("OK: voice.mp3 generado")

if __name__ == "__main__":
    main()
