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
    border-radius: 11px !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    background: #11151b !important;
    font-size: 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #eef1f5 !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(22,196,127,0.35) !important;
    box-shadow: 0 0 0 1px rgba(22,196,127,0.1) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #6b7382 !important;
}
</style>
"""
st.markdown(ADVISOR_CSS, unsafe_allow_html=True)

st.markdown(
    '<div style="margin-bottom:0.5rem;">'
    '<div style="font-size:12px;font-weight:600;letter-spacing:0.12em;'
    "text-transform:uppercase;color:#16c47f;margin-bottom:6px;"
    "font-family:'DM Sans',sans-serif;\">"
    "Asistente · IA conversacional</div>"
    '<span style="font-size:1.4rem;font-weight:700;color:#eef1f5;letter-spacing:-0.02em;'
    "font-family:'Sora',sans-serif;\">"
    "Asesor Virtual</span>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="color:#8b94a2;font-size:0.88rem;margin:0 0 16px 0;">'
    "Pregunta sobre cualquier partido o equipo...</p>",
    unsafe_allow_html=True,
)

WELCOME = (
    "Hola! Soy tu asesor de predicciones. Puedo ayudarte con:\n\n"
    "• **Consultar un partido** — _Argentina vs Algeria_\n"
    "• **Proximos partidos** — _Francia_ o _partidos de hoy_\n"
    "• **Mejores picks** — _mejores predicciones_\n"
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
