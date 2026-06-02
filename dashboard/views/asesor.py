"""Asesor Virtual — chat interactivo con el modelo de predicciones."""

import streamlit as st

from backend.advisor.engine import get_response
from dashboard.data_access import get_supabase_client

st.markdown(
    '<h1 style="font-size:2rem;">🤖 Asesor Virtual</h1>',
    unsafe_allow_html=True,
)
st.caption("Preguntame sobre partidos, predicciones o recomendaciones de apuestas.")

WELCOME = (
    "👋 Hola! Soy el asesor virtual de **Master Prediction**. "
    "Puedo ayudarte con:\n\n"
    "• **Consultar un partido** — _Argentina vs Algeria_\n"
    "• **Ver proximos partidos de un equipo** — _Francia_\n"
    "• **Mejores picks** — _mejores apuestas de hoy_\n"
    "• **Track record** — _racha del modelo_\n\n"
    "Escribe tu consulta abajo 👇"
)

if "advisor_messages" not in st.session_state:
    st.session_state.advisor_messages = [{"role": "assistant", "content": WELCOME}]

if "advisor_context" not in st.session_state:
    st.session_state.advisor_context = {}

if "advisor_teams" not in st.session_state:
    try:
        client = get_supabase_client()
        resp = client.table("predictions").select("home_team,away_team").execute()
        teams = set()
        for row in resp.data or []:
            teams.add(row["home_team"])
            teams.add(row["away_team"])

        resp2 = (
            client.table("matches")
            .select("home_team,away_team")
            .not_.is_("ft_result", "null")
            .order("match_date", desc=True)
            .limit(2000)
            .execute()
        )
        for row in resp2.data or []:
            teams.add(row["home_team"])
            teams.add(row["away_team"])

        st.session_state.advisor_teams = sorted(teams)
    except Exception:
        st.session_state.advisor_teams = []

for msg in st.session_state.advisor_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ej: Argentina vs Algeria, mejores picks de hoy..."):
    st.session_state.advisor_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizando..."):
            try:
                client = get_supabase_client()
                response, new_ctx = get_response(
                    client,
                    prompt,
                    st.session_state.advisor_teams,
                    st.session_state.advisor_context,
                )
                st.session_state.advisor_context = new_ctx
            except Exception as e:
                response = f"Error al procesar tu consulta: {e}"
        st.markdown(response)

    st.session_state.advisor_messages.append({"role": "assistant", "content": response})
