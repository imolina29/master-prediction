"""Asesor Virtual — chat interactivo con el modelo de predicciones."""

import streamlit as st

from backend.advisor.engine import get_response
from dashboard.data_access import get_supabase_client

ADVISOR_CSS = """
<style>
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
}
[data-testid="stChatInput"] textarea {
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    background: rgba(255,255,255,0.02) !important;
    font-size: 0.9rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(76,175,80,0.3) !important;
    box-shadow: 0 0 0 1px rgba(76,175,80,0.1) !important;
}
</style>
"""
st.markdown(ADVISOR_CSS, unsafe_allow_html=True)

st.markdown(
    '<div style="margin-bottom:0.5rem;">'
    '<span style="font-size:1.4rem;font-weight:700;color:#fff;letter-spacing:-0.02em;">'
    "⚽ Asesor Virtual</span>"
    '<span style="color:#555;font-size:0.82rem;margin-left:10px;">Master Prediction</span>'
    "</div>",
    unsafe_allow_html=True,
)
st.caption("Preguntame sobre partidos, predicciones o recomendaciones de apuestas.")

WELCOME = (
    "Hola! Soy tu asesor de predicciones. Puedo ayudarte con:\n\n"
    "• **Consultar un partido** — _Argentina vs Algeria_\n"
    "• **Proximos partidos** — _Francia_ o _partidos de hoy_\n"
    "• **Mejores picks** — _mejores apuestas_\n"
    "• **Track record** — _racha del modelo_"
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
    avatar = "⚽" if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("Ej: Argentina vs Algeria, mejores picks de hoy..."):
    st.session_state.advisor_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="⚽"):
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
        st.markdown(response, unsafe_allow_html=True)

    st.session_state.advisor_messages.append({"role": "assistant", "content": response})
