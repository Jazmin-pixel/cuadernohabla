import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from modelos import Apunte


MODELO = "gemini-3.8-flash"
INSTRUCCION_SISTEMA = (
    "Actúa como un profesor paciente de bachillerato de El Salvador. "
    "Escribe siempre en español salvadoreño claro. Basa tu análisis únicamente "
    "en lo que se ve en la imagen y no inventes temas. Si la foto está borrosa, "
    "dilo en el resumen en vez de inventar contenido. Las opciones incorrectas "
    "del examen deben ser creíbles, no absurdas, y la posición de la respuesta "
    "correcta debe variar entre preguntas."
)


class ImagenIlegible(Exception):
    """Indica que no se pudo obtener un apunte válido a partir de la imagen."""


def crear_cliente(api_key: str) -> genai.Client:
    if not api_key or not api_key.strip():
        raise ValueError("La llave de la API no puede estar vacía.")
    return genai.Client(api_key=api_key)


def analizar_pagina(datos_imagen: bytes, tipo_mime: str, cliente: genai.Client) -> Apunte:
    if not datos_imagen:
        raise ValueError("No se recibió una imagen para analizar.")

    respuesta = cliente.models.generate_content(
        model=MODELO,
        contents=[
            types.Part.from_bytes(data=datos_imagen, mime_type=tipo_mime),
            "Analiza la página y prepara el apunte solicitado.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCCION_SISTEMA,
            response_mime_type="application/json",
            response_schema=Apunte,
            temperature=0.4,
        ),
    )

    if isinstance(respuesta.parsed, Apunte):
        return respuesta.parsed

    if respuesta.parsed:
        raise ImagenIlegible(
            "No pudimos interpretar el contenido de la foto. "
            "Tomá otra imagen clara y bien iluminada de la página."
        )

    try:
        datos = json.loads(respuesta.text)
        return Apunte.model_validate(datos)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
        raise ImagenIlegible(
            "No pudimos leer la página de la foto. "
            "Tomá otra imagen clara, enfocada y con toda la página visible."
        ) from error


def calificar(apunte: Apunte, respuestas: dict[str, str]) -> tuple[int, int]:
    aciertos = 0
    for pregunta in apunte.examen:
        respuesta = respuestas.get(pregunta.enunciado)
        if (
            isinstance(respuesta, str)
            and respuesta.strip().casefold()
            == pregunta.opciones[pregunta.correcta].strip().casefold()
        ):
            aciertos += 1

    return aciertos, len(apunte.examen)
