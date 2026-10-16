from io import BytesIO

from gtts import gTTS


def decir(texto: str, idioma: str = "es") -> bytes | None:
    if not texto or not texto.strip():
        return None

    try:
        audio = BytesIO()
        sintesis = gTTS(text=texto[:1500], lang=idioma)
        sintesis.write_to_fp(audio)
        resultado = audio.getvalue()
        return resultado or None
    except Exception:
        return None
