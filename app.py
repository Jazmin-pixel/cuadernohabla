import streamlit as st
from google.genai.errors import ClientError, ServerError

from cerebro import ImagenIlegible, analizar_pagina, calificar, crear_cliente
from voz import decir


st.set_page_config(page_title="Mi cuaderno habla", page_icon="📓", layout="centered")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error(
        "No se encontró la llave GEMINI_API_KEY. Agregala en "
        "`.streamlit/secrets.toml` con este formato: "
        '`GEMINI_API_KEY = "tu_llave_de_api"`.'
    )
    st.stop()

# Streamlit vuelve a ejecutar el archivo en cada interacción; estos datos conservan
# el apunte y el progreso del examen entre esos reruns.
if "apunte" not in st.session_state:
    st.session_state.apunte = None
if "respuestas_examen" not in st.session_state:
    st.session_state.respuestas_examen = {}
if "examen_entregado" not in st.session_state:
    st.session_state.examen_entregado = False
if "version_examen" not in st.session_state:
    st.session_state.version_examen = 0
if "texto_voz_resumen" not in st.session_state:
    st.session_state.texto_voz_resumen = None
if "audio_resumen" not in st.session_state:
    st.session_state.audio_resumen = None


def procesar_imagen(archivo) -> None:
    if archivo is None:
        st.error("Primero tomá una foto o seleccioná una imagen de la página.")
        return

    try:
        with st.spinner("Analizando la página..."):
            cliente = crear_cliente(api_key)
            apunte = analizar_pagina(
                datos_imagen=archivo.getvalue(),
                tipo_mime=archivo.type,
                cliente=cliente,
            )
        st.session_state.apunte = apunte
        st.session_state.respuestas_examen = {}
        st.session_state.examen_entregado = False
        st.session_state.version_examen += 1
        st.session_state.texto_voz_resumen = None
        st.session_state.audio_resumen = None
    except ImagenIlegible as error:
        st.warning(str(error))
    except ServerError as error:
        if error.code == 503:
            st.warning(
                "Gemini está recibiendo muchas solicitudes en este momento. "
                "Esperá un minuto y volvé a tocar «Analizar la página»."
            )
        else:
            st.error(f"Gemini no pudo analizar la imagen (error {error.code}).")
    except ClientError as error:
        if error.code == 404:
            st.error(
                "Google no reconoce el modelo de análisis configurado. "
                "Actualizá la aplicación y volvé a intentarlo."
            )
        elif error.code in (401, 403):
            st.error("Google rechazó la llave API o no tiene permiso para usar Gemini.")
        elif error.code == 429:
            st.warning("Se alcanzó el límite temporal de solicitudes de Gemini. Esperá un momento y volvé a intentarlo.")
        else:
            st.error(f"Google rechazó la solicitud de análisis (error {error.code}).")
    except Exception as error:
        st.error(f"No se pudo analizar la página. Revisá tu conexión e intentá de nuevo. Detalle: {error}")


st.title("Mi cuaderno habla")
st.write("Tomá una foto de tus apuntes o subí una imagen para crear tu guía de estudio.")

pestana_foto, pestana_subir = st.tabs(["Tomar foto", "Subir imagen"])

with pestana_foto:
    foto = st.camera_input("Tomá una foto de la página")
    if st.button("Analizar la página", key="analizar_foto", use_container_width=True):
        procesar_imagen(foto)

with pestana_subir:
    imagen_subida = st.file_uploader(
        "Seleccioná una imagen de la página",
        type=["png", "jpg", "jpeg", "webp"],
    )
    if st.button("Analizar la página", key="analizar_subida", use_container_width=True):
        procesar_imagen(imagen_subida)

apunte = st.session_state.apunte
if apunte is not None:
    st.header(apunte.titulo)
    st.write(f"**Materia:** {apunte.materia}")
    st.write(f"**Dificultad:** {'⭐' * apunte.dificultad}")
    st.subheader("Resumen")
    st.write(apunte.resumen)
    escuchar_resumen = st.toggle("🔊 Escuchar el resumen")
    if escuchar_resumen:
        texto_resumen = f"{apunte.titulo}. {apunte.resumen}"
        if st.session_state.texto_voz_resumen != texto_resumen:
            try:
                st.session_state.audio_resumen = decir(texto_resumen)
            except Exception:
                st.session_state.audio_resumen = None
            st.session_state.texto_voz_resumen = texto_resumen

        if st.session_state.audio_resumen is not None:
            st.audio(st.session_state.audio_resumen, format="audio/mp3")
        else:
            st.caption("La voz no está disponible en este momento.")
    elif st.session_state.audio_resumen is None:
        st.session_state.texto_voz_resumen = None

    st.subheader("Conceptos")
    for concepto in apunte.conceptos:
        st.markdown(f"- **{concepto.termino}:** {concepto.explicacion}")

    st.subheader("Tarjetas de repaso")
    for indice, tarjeta in enumerate(apunte.tarjetas):
        with st.expander(tarjeta.pregunta):
            st.write(tarjeta.respuesta)

    st.subheader("Examen")
    respuestas_actuales = {}
    for indice, pregunta in enumerate(apunte.examen):
        seleccion = st.radio(
            pregunta.enunciado,
            options=pregunta.opciones,
            index=None,
            key=f"respuesta_{st.session_state.version_examen}_{indice}",
        )
        if seleccion is not None:
            respuestas_actuales[pregunta.enunciado] = seleccion
    st.session_state.respuestas_examen = respuestas_actuales

    if st.button("Entregar examen", key="entregar_examen", use_container_width=True):
        st.session_state.examen_entregado = True

    if st.session_state.examen_entregado:
        aciertos, total = calificar(apunte, st.session_state.respuestas_examen)
        st.metric("Puntaje", f"{aciertos} / {total}")
        for pregunta in apunte.examen:
            respuesta_correcta = pregunta.opciones[pregunta.correcta]
            respuesta_elegida = st.session_state.respuestas_examen.get(pregunta.enunciado)
            if respuesta_elegida is None:
                st.warning(f"Sin responder: {pregunta.enunciado}")
                st.info(f"Respuesta correcta: {respuesta_correcta}")
            elif respuesta_elegida.strip().casefold() == respuesta_correcta.strip().casefold():
                st.success(f"Correcta: {pregunta.enunciado}")
            else:
                st.error(f"Incorrecta: {pregunta.enunciado}")
                st.info(f"Respuesta correcta: {respuesta_correcta}")
        if total > 0 and aciertos == total:
            st.balloons()

    st.download_button(
        "Descargar guía de estudio",
        data=apunte.a_markdown(),
        file_name="guia_de_estudio.md",
        mime="text/markdown",
        use_container_width=True,
    )
