import os
import json
import re
from openai import OpenAI

MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

PROMPT = """Escribe UNA historia corta de terror para un video vertical de 30–40 segundos.

OBJETIVO: Retención alta. Debe sentirse REAL y verificable (tipo registro/cámara/log).

REGLAS OBLIGATORIAS:
- Narración en PRIMERA PERSONA.
- UNA sola escena concreta (un lugar, una hora, un objeto).
- CERO frases de relleno. Cada línea avanza la historia.
- Prohibido: “se dice”, “dicen”, “rumores”.
- Terror psicológico, cotidiano, creíble (sin gore).
- Final con giro personal que reinterpreta lo anterior.

ESTRUCTURA (muy importante):
1) Línea 1 (HOOK): una frase brutal que obligue a seguir (ej: “Este video no debería existir.”)
2) Líneas 2–5: anomalía específica + escalada lógica
3) Líneas 6–7: revelación inquietante
4) Línea 8 (FINAL): giro corto y frío

SALIDA:
Devuelve SOLO JSON válido (sin texto extra), con este formato:

{
  "title": "",
  "segments": ["..."],
  "visual_plan": [
    { "keywords": ["..."], "duration_sec": 14 },
    { "keywords": ["..."], "duration_sec": 13 },
    { "keywords": ["..."], "duration_sec": 13 }
  ],
  "cta": "Sígueme para más historias reales de terror."
}

RESTRICCIONES:
- segments: EXACTAMENTE 8 líneas
- Máximo 14 palabras por línea
- Español natural, como confesión en voz baja
- visual_plan:
  - EXACTAMENTE 3 bloques
  - keywords en INGLÉS (3–6 palabras por bloque)
  - Deben ser escenas “stock-friendly” (pasillo oscuro, cámara de seguridad, calle nocturna, puerta, sombra)
  - duration_sec debe sumar 40 (14 + 13 + 13)
"""

def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return json.loads(m.group(0))

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)

    resp = client.responses.create(
        model=MODEL,
        input=PROMPT,
        temperature=0.9,
        max_output_tokens=500,
    )

    out_text = ""
    for item in resp.output:
        if item.type == "message":
            for c in item.content:
                if c.type == "output_text":
                    out_text += c.text

    data = extract_json(out_text)

    # Validaciones mínimas
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError("Invalid JSON: missing title.")

    segments = data.get("segments")
    if not isinstance(segments, list) or len(segments) != 8:
        raise ValueError("Invalid JSON: segments must be a list of exactly 8 strings.")
    for s in segments:
        if not isinstance(s, str) or not s.strip():
            raise ValueError("Invalid JSON: each segment must be a non-empty string.")

    vp = data.get("visual_plan")
    if not isinstance(vp, list) or len(vp) != 3:
        raise ValueError("Invalid JSON: visual_plan must be a list of exactly 3 items.")

    total_dur = 0
    for block in vp:
        if not isinstance(block, dict):
            raise ValueError("Invalid JSON: each visual_plan item must be an object.")
        kws = block.get("keywords")
        dur = block.get("duration_sec")
        if not isinstance(kws, list) or not (3 <= len(kws) <= 6) or not all(isinstance(k, str) and k.strip() for k in kws):
            raise ValueError("Invalid JSON: visual_plan.keywords must be 3–6 non-empty strings.")
        if not isinstance(dur, int) or dur <= 0:
            raise ValueError("Invalid JSON: visual_plan.duration_sec must be a positive integer.")
        total_dur += dur

    if total_dur != 40:
        raise ValueError(f"Invalid JSON: visual_plan duration_sec must sum to 40, got {total_dur}.")

    with open("story.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK: story.json generated")

if __name__ == "__main__":
    main()
