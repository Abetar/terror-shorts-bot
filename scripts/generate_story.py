import os
import json
import re
from openai import OpenAI

MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

PROMPT = """Eres un guionista profesional de terror psicológico para TikTok/Shorts.

TAREA:
Genera UNA historia corta de terror PSICOLÓGICO para video vertical (30–40s), en ESPAÑOL, contada EN PRIMERA PERSONA.

OBJETIVO:
Que el espectador entienda exactamente qué pasó, sin incoherencias.

REGLAS OBLIGATORIAS (NO NEGOCIABLES):
- Devuelve SOLO el JSON final. NO incluyas explicaciones, notas, instrucciones, ni texto fuera del JSON.
- NO incluyas instrucciones de narración en el texto (ej: "lee esto...", "voz baja...", "pausas...").
- 8 a 10 frases en "segments".
- Máximo 12 palabras por frase.
- Cada frase DEBE conectar causalmente con la anterior (sin saltos ni cambios de escena).
- Prohibido: "dicen", "rumores", "se dice", "este video...", "lee esto", "en voz", "narración".
- Ocurre en una sola noche y un solo lugar (casa/depa/oficina/pasillo del edificio).
- Terror cotidiano y visual (pasillo, puerta, espejo, luz, cámara, elevador, vecino).
- El giro final debe reinterpretar una SEÑAL anterior (no amenaza genérica).

VISUAL_PLAN OBLIGATORIO:
- Crea "visual_plan" con EXACTAMENTE 3 bloques.
- Cada bloque debe tener:
  - "shot": descripción corta en español (qué se ve en pantalla).
  - "keywords": lista de 5 a 8 keywords EN INGLÉS, stock-friendly (solo cosas visibles, no sonidos).
  - "duration_sec": número (12–16 aprox) por bloque.
- Keywords permitidas (puedes combinar): hallway, corridor, apartment, night, door, shadow, phone screen, security camera, mirror, stairs, elevator, flickering light, close up, hands, empty room.
- Prohibido usar en keywords: sound, whisper, audio, voice, zoom, slow.

CHECK FINAL (ANTES DE ENTREGAR):
1) ¿Cada frase sigue la misma escena y misma noche? Si no, reescribe.
2) ¿Hay causalidad clara entre frases? Si no, reescribe.
3) ¿Hay alguna instrucción meta o técnica en segments? Si sí, reescribe.
4) ¿El giro final reinterpreta una señal anterior? Si no, reescribe.

FORMATO DE SALIDA (JSON válido):
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
"""

META_BANNED = [
    "lee esto", "lee en voz", "en voz", "voz baja", "tensión contenida", "pausas",
    "narración", "instrucción", "prompt", "este video"
]

def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return json.loads(m.group(0))

def count_words(s: str) -> int:
    return len([w for w in re.split(r"\s+", s.strip()) if w])

def contains_meta(s: str) -> bool:
    low = s.lower()
    return any(b in low for b in META_BANNED)

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
        # Fuerza JSON (si el modelo lo soporta, esto reduce basura fuera del objeto)
        response_format={"type": "json_object"},
    )

    out_text = ""
    for item in resp.output:
        if item.type == "message":
            for c in item.content:
                if c.type == "output_text":
                    out_text += c.text

    # Si response_format funcionó, out_text ya es JSON. Igual dejamos fallback.
    try:
        data = json.loads(out_text)
    except Exception:
        data = extract_json(out_text)

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
        if contains_meta(s):
            raise ValueError(f"Invalid JSON: meta/instruction leaked into segment: {s}")

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

        # Extra: evita keywords prohibidas (por si acaso)
        banned_kw = {"sound", "whisper", "audio", "voice", "zoom", "slow"}
        for kw in kws:
            if isinstance(kw, str) and kw.strip().lower() in banned_kw:
                raise ValueError(f"Invalid JSON: banned keyword in visual_plan.keywords: {kw}")

    with open("story.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK: story.json generated")

if __name__ == "__main__":
    main()
