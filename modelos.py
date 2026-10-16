from pydantic import BaseModel, Field, field_validator, model_validator


class Concepto(BaseModel):
    termino: str = Field(description="Término importante identificado en los apuntes del estudiante.")
    explicacion: str = Field(description="Explicación clara y fiel al contenido de la página.")


class Tarjeta(BaseModel):
    pregunta: str = Field(description="Pregunta breve para repasar un contenido de la página.")
    respuesta: str = Field(description="Respuesta correcta y concisa a la pregunta.")


class Pregunta(BaseModel):
    enunciado: str = Field(description="Enunciado de una pregunta de opción múltiple sobre el contenido.")
    opciones: list[str] = Field(description="Lista de opciones de respuesta para la pregunta.")
    correcta: int = Field(description="Índice, empezando desde 0, de la opción correcta en la lista de opciones.")

    @field_validator("opciones")
    @classmethod
    def validar_opciones(cls, opciones: list[str]) -> list[str]:
        if len(opciones) != 4:
            raise ValueError("La pregunta debe tener exactamente cuatro opciones.")

        opciones_normalizadas = [opcion.casefold() for opcion in opciones]
        if len(set(opciones_normalizadas)) != 4:
            raise ValueError("Las cuatro opciones deben ser distintas, sin diferencias solo de mayúsculas y minúsculas.")

        return opciones

    @model_validator(mode="after")
    def validar_correcta(self) -> "Pregunta":
        if not 0 <= self.correcta < len(self.opciones):
            raise ValueError(
                f"El índice de la opción correcta debe estar entre 0 y {len(self.opciones) - 1}; "
                f"se recibió {self.correcta}."
            )
        return self


class Apunte(BaseModel):
    titulo: str = Field(description="Título breve que describa el tema principal de la página.")
    materia: str = Field(description="Materia escolar a la que pertenece el contenido.")
    resumen: str = Field(description="Resumen claro de las ideas principales de la página.")
    conceptos: list[Concepto] = Field(description="Conceptos importantes de la página con sus explicaciones.")
    tarjetas: list[Tarjeta] = Field(description="Tarjetas de pregunta y respuesta para estudiar el contenido.")
    examen: list[Pregunta] = Field(description="Preguntas de opción múltiple para evaluar la comprensión del contenido.")
    dificultad: int = Field(description="Nivel de dificultad general del contenido de la página.")

    def a_markdown(self) -> str:
        lineas = [
            f"# {self.titulo}",
            f"**Materia:** {self.materia}",
            f"**Dificultad:** {'⭐' * self.dificultad}",
            "",
            "## Resumen",
            self.resumen,
            "",
            "## Conceptos",
        ]
        lineas.extend(
            f"- **{concepto.termino}:** {concepto.explicacion}"
            for concepto in self.conceptos
        )
        lineas.extend(["", "## Tarjetas de repaso"])
        for indice, tarjeta in enumerate(self.tarjetas[:5], start=1):
            lineas.extend(
                [
                    f"{indice}. **{tarjeta.pregunta}**",
                    f"   **Respuesta:** {tarjeta.respuesta}",
                ]
            )

        letras = ("a", "b", "c", "d")
        lineas.extend(["", "## Examen"])
        for indice, pregunta in enumerate(self.examen, start=1):
            lineas.append(f"{indice}. {pregunta.enunciado}")
            for letra, opcion_indice in zip(letras, range(4)):
                opcion = pregunta.opciones[opcion_indice]
                if opcion_indice == pregunta.correcta:
                    lineas.append(f"   - **{letra}) {opcion} (respuesta correcta)**")
                else:
                    lineas.append(f"   - {letra}) {opcion}")
        return "\n".join(lineas)

    @field_validator("dificultad")
    @classmethod
    def validar_dificultad(cls, dificultad: int) -> int:
        if not 1 <= dificultad <= 5:
            raise ValueError(f"La dificultad debe estar entre 1 y 5; se recibió {dificultad}.")
        return dificultad

    @field_validator("conceptos")
    @classmethod
    def validar_cantidad_conceptos(cls, conceptos: list[Concepto]) -> list[Concepto]:
        if len(conceptos) < 3:
            raise ValueError(f"Debe haber al menos 3 conceptos; se recibieron {len(conceptos)}.")
        return conceptos

    @field_validator("tarjetas")
    @classmethod
    def validar_cantidad_tarjetas(cls, tarjetas: list[Tarjeta]) -> list[Tarjeta]:
        if len(tarjetas) < 5:
            raise ValueError(f"Debe haber al menos 5 tarjetas; se recibieron {len(tarjetas)}.")
        return tarjetas

    @field_validator("examen")
    @classmethod
    def validar_cantidad_preguntas(cls, examen: list[Pregunta]) -> list[Pregunta]:
        if len(examen) < 3:
            raise ValueError(f"Debe haber al menos 3 preguntas de examen; se recibieron {len(examen)}.")
        return examen
