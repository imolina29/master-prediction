import streamlit as st

st.set_page_config(
    page_title="Master Prediction",
    page_icon="⚽",
    layout="wide",
)

st.title("Master Prediction")
st.markdown("### Plataforma de Inteligencia Deportiva")
st.markdown("""
Selecciona una pagina en la barra lateral:

- **Vista de Liga** — Tabla de posiciones enriquecida con xG y racha
- **Analisis de Equipo** — Analisis profundo de un equipo
- **Comparador de Partidos** — Comparacion cabeza a cabeza
""")
