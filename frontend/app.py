"""
Frontend Streamlit del Agente RAG DNI.

Para ejecutar:
    streamlit run frontend/app.py

Permite hacer preguntas al agente y muestra la respuesta, las fuentes citadas
y los chunks recuperados (en un expander), ademas de las metricas de la
consulta.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st

# Anyadir la raiz del repo al sys.path para poder importar consultar.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from consultar import consultar  # noqa: E402


st.set_page_config(
    page_title="Agente RAG DNI",
    page_icon="🤝",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Cabecera
# ----------------------------------------------------------------------------
st.title("🤝 Asistente DNI Valencia")
st.caption(
    "Pregunta lo que quieras sobre la asociacion **Damos Nuestra Ilusion**. "
    "El asistente responde basandose unicamente en la documentacion oficial."
)

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("Sobre el agente")
    st.markdown(
        """
        Este asistente es un sistema **RAG** (Retrieval-Augmented Generation):

        1. Convierte tu pregunta en un vector
        2. Busca los fragmentos mas similares en el corpus
        3. Pide al LLM una respuesta basada solo en esos fragmentos
        4. Te muestra la respuesta y las fuentes consultadas

        **Importante:** si la informacion no esta en el corpus, el agente
        responde *"No tengo esa informacion en mis fuentes"*. No inventa.
        """
    )

    st.divider()
    st.subheader("Preguntas de ejemplo")
    ejemplos = [
        "¿Que es DNI?",
        "¿Donde son los desayunos solidarios?",
        "¿Como me apunto al refuerzo escolar?",
        "¿En que se diferencian RESIS y COLES?",
        "¿A que hora son los desayunos?",  # contradiccion del corpus
    ]
    for ej in ejemplos:
        if st.button(ej, key=f"ej_{ej}", use_container_width=True):
            st.session_state["pregunta_actual"] = ej

    st.divider()
    st.caption("v1.0 · Practica Agentes IA · GTI")


# ----------------------------------------------------------------------------
# Historial de la conversacion (en session_state)
# ----------------------------------------------------------------------------
if "historial" not in st.session_state:
    st.session_state["historial"] = []
if "pregunta_actual" not in st.session_state:
    st.session_state["pregunta_actual"] = ""


# ----------------------------------------------------------------------------
# Mostrar historial
# ----------------------------------------------------------------------------
for turno in st.session_state["historial"]:
    with st.chat_message("user"):
        st.markdown(turno["pregunta"])
    with st.chat_message("assistant"):
        st.markdown(turno["respuesta"])
        if turno["fuentes"]:
            with st.expander(f"📚 Fuentes citadas ({len(turno['fuentes'])})"):
                for f in turno["fuentes"]:
                    st.markdown(f"- `{f}`")
        if turno.get("chunks"):
            with st.expander(f"🔍 Chunks recuperados ({len(turno['chunks'])})"):
                for i, c in enumerate(turno["chunks"]):
                    st.markdown(f"**Fragmento {i + 1}**")
                    st.text(c)
        if turno.get("metricas"):
            with st.expander("📊 Metricas"):
                m = turno["metricas"]
                col1, col2, col3 = st.columns(3)
                col1.metric("Latencia", f"{m.get('latencia_total_s', 0)}s")
                col2.metric("Tokens out", m.get("tokens_salida", 0))
                col3.metric("tok/s", m.get("tokens_por_segundo", 0))
                st.caption(f"Modelo: `{m.get('modelo', '?')}` · Backend: `{m.get('backend', '?')}`")


# ----------------------------------------------------------------------------
# Caja de pregunta
# ----------------------------------------------------------------------------
pregunta = st.chat_input("Escribe tu pregunta sobre DNI...")

# Si se ha pulsado un ejemplo del sidebar, lo cogemos como pregunta
if not pregunta and st.session_state["pregunta_actual"]:
    pregunta = st.session_state["pregunta_actual"]
    st.session_state["pregunta_actual"] = ""

if pregunta:
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en el corpus y generando respuesta..."):
            try:
                resultado = consultar(pregunta)
                st.markdown(resultado["respuesta"])

                if resultado["fuentes"]:
                    with st.expander(f"📚 Fuentes citadas ({len(resultado['fuentes'])})"):
                        for f in resultado["fuentes"]:
                            st.markdown(f"- `{f}`")

                if resultado.get("chunks"):
                    with st.expander(f"🔍 Chunks recuperados ({len(resultado['chunks'])})"):
                        for i, c in enumerate(resultado["chunks"]):
                            st.markdown(f"**Fragmento {i + 1}**")
                            st.text(c)

                if resultado.get("metricas"):
                    with st.expander("📊 Metricas"):
                        m = resultado["metricas"]
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Latencia", f"{m.get('latencia_total_s', 0)}s")
                        col2.metric("Tokens out", m.get("tokens_salida", 0))
                        col3.metric("tok/s", m.get("tokens_por_segundo", 0))
                        st.caption(
                            f"Modelo: `{m.get('modelo', '?')}` · "
                            f"Backend: `{m.get('backend', '?')}`"
                        )

                # Guardar en historial
                st.session_state["historial"].append({
                    "pregunta": pregunta,
                    "respuesta": resultado["respuesta"],
                    "fuentes": resultado["fuentes"],
                    "chunks": resultado.get("chunks", []),
                    "metricas": resultado.get("metricas", {}),
                })

            except Exception as e:
                st.error(f"Error al consultar el agente: {e}")
                st.info(
                    "Comprueba que Ollama esta arrancado (`ollama serve`) y que tienes "
                    "los modelos descargados (`ollama pull llama3.2:3b nomic-embed-text`)."
                )
