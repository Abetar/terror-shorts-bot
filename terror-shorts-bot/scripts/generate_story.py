import os, json, re
from openai import OpenAI

MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

PROMPT = """Escribe UNA historia corta de terror para un video vertical de 60–70 segundos.

Estilo:
- Mezcla creepypasta, leyenda urbana y caso real inspirado
- Terror psicológico (sin gore)
- Español claro, frases cortas
- Gancho fuerte en la primera línea
- Última línea perturbadora

Devuelve SOLO JSON estricto, sin texto extra, con este formato:
{
  "title": "",
  "segments": [""],
  "cta": "Sígueme para más historias de terror."
}

Reglas:
- 8 a 10 oraciones
- Cada oración <= 14 palabras
"""

def extract_json(text: str) -> dict:
    # Por si el modelo mete texto extra, intentamos rescatar el primer bloque JSON
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("No JSON found in model output")
    return json.loads(m.group(0))

def main():
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    resp = client.responses.create(
        model=MODEL,
        input=PROMPT,
        temperature=0.9,
        max_output_tokens=450,  # controla costo
    )

    # Responses API devuelve output como items; extraemos texto concatenado
    out_text = ""
    for item in resp.output:
        if item.type == "message":
            for c in item.content:
                if c.type == "output_text":
                    out_text += c.text

    data = extract_json(out_text)

    # Validación mínima
    assert isinstance(data.get("title"), str) and data["title"].strip()
    assert isinstance(data.get("segments"), list) and 8 <= len(data["segments"]) <= 10

    with open("story.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("OK: story.json generado")

if __name__ == "__main__":
    main()
