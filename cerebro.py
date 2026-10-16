import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from modelos import Apunte


MODELO = "gemini-3.5-flash-lite"
INSTRUCCION_SISTEMA = (
    "Actúa como un profesor paciente de bachillerato de El Salvador. "
    "Escribe siempre en español salvadoreño claro. Basa tu análisis únicamente "
    "en lo que se ve en la imagen y no inventes temas. Si la foto está borrosa, "
    "dilo en el resumen en vez de inventar contenido. Las opciones incorrectas "
    "del examen deben ser creíbles, no absurdas, y la posición de la respuesta "
    "correcta debe variar entre preguntas. Incluye al menos 3 conceptos, "
    "5 tarjetas y 3 preguntas de examen. Cada pregunta debe tener exactamente "
    "4 opciones distintas y un índice de respuesta correcta entre 0 y 3."
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

    error_validacion: ValidationError | None = None
    if respuesta.parsed is not None:
        try:
            return Apunte.model_validate(respuesta.parsed)
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                error_validacion = error

    texto = respuesta.text
    if isinstance(texto, str) and texto.strip():
        try:
            datos = json.loads(texto)
            return Apunte.model_validate(datos)
        except json.JSONDecodeError as error:
            raise ImagenIlegible(
                "La IA respondió en un formato que no se pudo interpretar. "
                "La foto no necesariamente está borrosa; intentá analizarla de nuevo."
            ) from error
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                error_validacion = error

    if error_validacion is not None:
        detalles = "; ".join(
            f"{'.'.join(str(parte) for parte in detalle['loc'])}: {detalle['msg']}"
            for detalle in error_validacion.errors(include_input=False)[:3]
        )
        raise ImagenIlegible(
            "La IA respondió, pero el apunte no cumplió el formato requerido. "
            "La foto no necesariamente está borrosa; intentá analizarla de nuevo. "
            f"Detalle: {detalles}"
        ) from error_validacion

    raise ImagenIlegible(
        "La IA no devolvió contenido para el apunte. "
        "Intentá analizar la imagen de nuevo; si sigue pasando, probá con otra foto."
    )


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
