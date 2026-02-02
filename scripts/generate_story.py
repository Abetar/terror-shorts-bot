import os
import json
import re
from openai import OpenAI

MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

ATTEMPTS = int(os.getenv("STORY_ATTEMPTS", "3"))
TARGET_N = 9  # fijo

PROMPT = """Eres un guionista profesional especializado en terror psicológico REALISTA para TikTok y YouTube Shorts.

TAREA:
Genera UNA historia corta de terror psicológico para video vertical (30–40 segundos), en ESPAÑOL, contada EN PRIMERA PERSONA.

OBJETIVO:
Provocar incomodidad y miedo porque los hechos son cotidianos, claros y visuales.
El espectador debe poder imaginar exactamente qué pasó.

REGLAS OBLIGATORIAS (NO NEGOCIABLES):
- Devuelve SOLO el JSON final. Nada fuera del JSON.
- NO incluyas instrucciones de narración, actuación o voz.
- EXACTAMENTE 9 frases en "segments".
- Máximo 12 palabras por frase.
- Una sola noche y un solo lugar (departamento, pasillo, elevador, escalera).
- Cada frase debe describir UNA ACCIÓN, SEÑAL o CONSECUENCIA visible.
- Cada frase debe ser consecuencia directa de la anterior.
- Prohibido: “dicen”, “rumores”, “se dice”, “este video…”, “no debería existir”.
- Terror cotidiano y creíble, no paranormal exagerado.

ESTRUCTURA OBLIGATORIA DE LOS 9 SEGMENTS:
1. Situación normal específica (hora + lugar).
2. Primera anomalía pequeña, casi ignorada.
3. Acción del narrador para comprobar.
4. Evidencia visual concreta (algo que se VE).
5. Decisión equivocada del narrador.
6. Segunda evidencia más clara (algo que se VE).
7. Conexión inquietante con algo anterior (menciona la pista de 4 o 6).
8. Revelación que cambia el significado de todo (debe referirse a esa pista).
9. Golpe final incómodo y personal (FINAL SILENCIOSO, sin CTA).

REGLA DE GIRO (CRÍTICA):
- La frase 8 debe mencionar explícitamente una pista visual vista en la frase 4 o 6.
- La frase 9 debe reinterpretar esa misma pista, sin explicar de más.

VISUAL_PLAN (CRÍTICO):
- EXACTAMENTE 3 bloques, cada uno corresponde a 3 segmentos consecutivos (1-3, 4-6, 7-9).
- Cada bloque debe poder grabarse con video realista.
- NO describas emociones, SOLO lo que se ve.

Cada bloque debe incluir:
- "shot": descripción clara en español de la escena visual.
- "keywords": 5 a 8 palabras en INGLÉS, objetos o lugares visibles (stock-friendly).
- "duration_sec": número entre 12 y 16.

Keywords permitidas:
hallway, corridor, apartment, night, door, shadow, phone screen, security camera, mirror, stairs, elevator, flickering light, close up, hands, empty room

Prohibido en keywords:
sound, whisper, audio, voice, zoom, slow

CTA:
- "cta" debe existir y ser UNA sola frase breve (8–12 palabras).
- El CTA NO debe estar dentro de "segments".
- Debe invitar a seguir y comentar, sin romper el tono.

FORMATO DE SALIDA (JSON):
{
  "title": "",
  "segments": ["..."],
  "visual_plan": [
    { "shot": "", "keywords": ["..."], "duration_sec": 14 },
    { "shot": "", "keywords": ["..."], "duration_sec": 13 },
    { "shot": "", "keywords": ["..."], "duration_sec": 13 }
  ],
  "cta": ""
}
"""

META_BANNED = [
    "lee esto", "lee en voz", "en voz", "voz baja", "tensión contenida", "pausas",
    "narración", "instrucción", "prompt", "este video"
]

# Si se filtra CTA dentro de segments, lo matamos
CTA_LEAK_BANNED = [
    "sígueme", "sigueme", "comenta", "comenten", "follow", "suscríbete", "suscribete"
]

BANNED_KW = {"sound", "whisper", "audio", "voice", "zoom", "slow"}


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


def contains_cta_leak(s: str) -> bool:
    low = s.lower()
    return any(b in low for b in CTA_LEAK_BANNED)


def normalize_segments(segments: list[str]) -> list[str]:
    """
    Normalización segura:
    - Si hay >9: recorta manteniendo causalidad y el giro final.
    - Si hay <9: NO inventa filler (mata calidad). Fuerza reintento.
    """
    segs = [s.strip() for s in segments if isinstance(s, str) and s.strip()]

    if len(segs) == TARGET_N:
        return segs

    if len(segs) > TARGET_N:
        # Mantén 1-6 (setup + escalada) y conserva 8-9 del final (giro/impacto)
        # Tomamos: primeros 6 + últimos 3 = 9
        head = segs[:6]
        tail = segs[-3:]
        segs = (head + tail)[:TARGET_N]
        return segs

    # < 9: reintentar, no rellenar basura
    raise ValueError(f"segments too short: got {len(segs)}, need {TARGET_N}")


def validate_story(data: dict) -> None:
    title = data.get("title")
    segments = data.get("segments")
    visual_plan = data.get("visual_plan")
    cta = data.get("cta")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("Invalid JSON: missing title.")

    if not isinstance(segments, list) or len(segments) != TARGET_N:
        raise ValueError("Invalid JSON: segments must be a list of exactly 9 strings.")

    for i, s in enumerate(segments, start=1):
        if not isinstance(s, str) or not s.strip():
            raise ValueError("Invalid JSON: empty segment.")
        if count_words(s) > 12:
            raise ValueError(f"Invalid JSON: segment too long (>12 words): {s}")
        if contains_meta(s):
            raise ValueError(f"Invalid JSON: meta/instruction leaked into segment: {s}")
        # CTA NO debe estar en segments
        if contains_cta_leak(s):
            raise ValueError(f"Invalid JSON: CTA leaked into segments (segment {i}): {s}")

    if not isinstance(cta, str) or not cta.strip():
        raise ValueError("Invalid JSON: missing cta.")
    if count_words(cta) < 4 or count_words(cta) > 12:
        raise ValueError("Invalid JSON: cta should be ~8–12 words (4–12 allowed).")
    if contains_meta(cta):
        raise ValueError(f"Invalid JSON: meta/instruction leaked into cta: {cta}")

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

        for kw in kws:
            if isinstance(kw, str) and kw.strip().lower() in BANNED_KW:
                raise ValueError(f"Invalid JSON: banned keyword in visual_plan.keywords: {kw}")


def call_model(client: OpenAI, prompt: str) -> str:
    resp = client.responses.create(
        model=MODEL,
        input=prompt,
        temperature=0.85,
        max_output_tokens=650,
    )
    out_text = ""
    for item in resp.output:
        if item.type == "message":
            for c in item.content:
                if c.type == "output_text":
                    out_text += c.text
    return out_text.strip()


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)

    last_err = None
    data = None

    for attempt in range(1, ATTEMPTS + 1):
        try:
            prompt = PROMPT

            # En intentos >1, refuerzo directo para cortar outputs “creativos”
            if attempt > 1:
                prompt += (
                    f"\n\nRECORDATORIO FINAL: "
                    f"segments DEBE tener EXACTAMENTE {TARGET_N} frases. "
                    f"NO metas CTA dentro de segments. "
                    f"Entrega SOLO JSON.\n"
                )

            out_text = call_model(client, prompt)

            try:
                data = json.loads(out_text)
            except Exception:
                data = extract_json(out_text)

            # normaliza o fuerza reintento si <9
            if isinstance(data.get("segments"), list):
                data["segments"] = normalize_segments(data["segments"])

            validate_story(data)
            break

        except Exception as e:
            last_err = e
            data = None

    if data is None:
        raise RuntimeError(
            f"Failed to generate valid story after {ATTEMPTS} attempts. Last error: {last_err}"
        )

    with open("story.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK: story.json generated")


if __name__ == "__main__":
    main()
