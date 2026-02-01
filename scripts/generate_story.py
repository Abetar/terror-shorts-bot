import os
import json
import re
from openai import OpenAI

MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

PROMPT = """Escribe UNA historia corta de terror PSICOLÓGICO para video vertical (30–40s), en ESPAÑOL, contada EN PRIMERA PERSONA.

OBJETIVO: que el espectador entienda exactamente qué pasó, sin incoherencias.

REGLAS OBLIGATORIAS:
- 8 a 10 frases en "segments".
- Máximo 12 palabras por frase.
- Cada frase DEBE conectar causalmente con la anterior (sin saltos).
- Nada de frases meta tipo: "este video no debería existir", "dicen", "rumores".
- Debe ocurrir en una sola noche y un solo lugar (casa/depa/oficina).
- Terror cotidiano: pasillo, puerta, espejo, luz, cámara, vecino, elevador, etc.
- El giro final NO es amenaza genérica: debe reinterpretar una señal anterior.

VISUAL_PLAN OBLIGATORIO:
- Crea "visual_plan" con EXACTAMENTE 3 bloques.
- Cada bloque debe tener:
  - "shot": descripción corta en español (qué se ve en pantalla).
  - "keywords": lista de 5 a 8 keywords EN INGLÉS, stock-friendly (cosas visibles, no sonidos).
  - "duration_sec": número (12–16 aprox) por bloque.
- Keywords permitidas: hallway, corridor, apartment, night, door, shadow, phone screen, security camera, mirror, stairs, elevator, flickering light, close up, hands, empty room.
- Prohibido usar: sound, whisper, audio, voice, zoom, slow (Pexels no los indexa bien).

FORMATO DE SALIDA:
Devuelve SOLO JSON válido, sin texto adicional.

{
  "title": "",
  "segments": ["..."],
  "visual_plan": [
    { "shot": "", "keywords": ["..."], "duration_sec": 14 },
    { "shot": "", "keywords": ["..."], "duration_sec": 13 },
    { "shot": "", "keywords": ["..."], "duration_sec": 13 }
  ],
  "cta": "Sígueme para más historias de terror."
}

IMPORTANTE:
- El texto debe sonar como alguien hablando en voz baja, con pausas (usa comas y puntos).
"""

def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return json.loads(m.group(0))

def count_words(s: str) -> int:
    return len([w for w in re.split(r"\s+", s.strip()) if w])

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)

    resp = client.responses.create(
        model=MODEL,
        input=PROMPT,
        temperature=0.85,
        max_output_tokens=650,
    )

    out_text = ""
    for item in resp.output:
        if item.type == "message":
            for c in item.content:
                if c.type == "output_text":
                    out_text += c.text

    data = extract_json(out_text)

    # Validaciones mínimas
    title = data.get("title")
    segments = data.get("segments")
    visual_plan = data.get("visual_plan")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("Invalid JSON: missing title.")
    if not isinstance(segments, list) or not (8 <= len(segments) <= 10):
        raise ValueError("Invalid JSON: segments must be a list of 8–10 strings.")
    for s in segments:
        if not isinstance(s, str) or not s.strip():
            raise ValueError("Invalid JSON: empty segment.")
        if count_words(s) > 12:
            raise ValueError(f"Invalid JSON: segment too long (>12 words): {s}")

    if not isinstance(visual_plan, list) or len(visual_plan) != 3:
        raise ValueError("Invalid JSON: visual_plan must have exactly 3 items.")
    for b in visual_plan:
        if not isinstance(b, dict):
            raise ValueError("Invalid JSON: visual_plan item not object.")
        if not isinstance(b.get("shot"), str) or not b["shot"].strip():
            raise ValueError("Invalid JSON: visual_plan.shot missing.")
        kws = b.get("keywords")
        if not isinstance(kws, list) or not (5 <= len(kws) <= 8):
            raise ValueError("Invalid JSON: visual_plan.keywords must be 5–8 items.")
        if not isinstance(b.get("duration_sec"), (int, float)):
            raise ValueError("Invalid JSON: visual_plan.duration_sec missing/invalid.")

    with open("story.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK: story.json generated")

if __name__ == "__main__":
    main()
