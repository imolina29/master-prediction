import copy
import time

import streamlit as st
import streamlit_authenticator as stauth

SESSION_TIMEOUT_SECONDS = 30 * 60

LOGIN_CSS = """
<style>
/* ── Hide sidebar on login ── */
[data-testid="stSidebar"] { display: none; }

/* ── Login container ── */
[data-testid="stForm"] {
    max-width: 380px;
    margin: 0 auto;
    background: linear-gradient(145deg, rgba(27, 94, 32, 0.15), rgba(14, 17, 23, 0.95));
    border: 1px solid rgba(76, 175, 80, 0.25);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

/* ── Input fields ── */
[data-testid="stForm"] input {
    background: rgba(14, 17, 23, 0.8) !important;
    border: 1px solid rgba(76, 175, 80, 0.3) !important;
    border-radius: 8px !important;
    color: #e0e0e0 !important;
    padding: 0.6rem 1rem !important;
}
[data-testid="stForm"] input:focus {
    border-color: #4CAF50 !important;
    box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2) !important;
}

/* ── Login button ── */
[data-testid="stForm"] button[type="submit"] {
    background: linear-gradient(135deg, #2E7D32, #1B5E20) !important;
    color: #FFD700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    width: 100%;
    transition: all 0.3s ease !important;
}
[data-testid="stForm"] button[type="submit"]:hover {
    background: linear-gradient(135deg, #388E3C, #2E7D32) !important;
    box-shadow: 0 4px 16px rgba(46, 125, 50, 0.4) !important;
}

/* ── Labels ── */
[data-testid="stForm"] label {
    color: #a5d6a7 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* ── Error/info alerts on login ── */
.login-page [data-testid="stAlert"] {
    max-width: 380px;
    margin: 1rem auto;
    border-radius: 10px;
}
</style>
"""

LOGIN_HEADER = """
<div style="text-align: center; padding: 3rem 0 1.5rem 0;">
    <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">⚽</div>
    <h1 style="
        color: #4CAF50;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 1px;
    ">MASTER PREDICTION</h1>
    <p style="
        color: #81C784;
        font-size: 0.95rem;
        margin-top: 0.3rem;
        letter-spacing: 2px;
        text-transform: uppercase;
    ">Inteligencia Deportiva</p>
    <div style="
        width: 60px;
        height: 2px;
        background: linear-gradient(90deg, transparent, #FFD700, transparent);
        margin: 1rem auto 0;
    "></div>
</div>
"""

LOGIN_FOOTER = """
<div style="text-align: center; padding: 2rem 0 1rem 0;">
    <p style="color: rgba(160, 160, 160, 0.6); font-size: 0.75rem; letter-spacing: 0.5px;">
        Powered by AI &middot; v1.0
    </p>
</div>
"""


def _deep_copy_secrets(section: str) -> dict:
    raw = st.secrets.get(section, {})
    return copy.deepcopy(dict(raw))


def _force_logout():
    st.session_state["authentication_status"] = None
    st.session_state["name"] = None
    st.session_state["username"] = None
    st.session_state.pop("session_start", None)


def _check_session_timeout() -> bool:
    start = st.session_state.get("session_start")
    if start is None:
        st.session_state["session_start"] = time.time()
        return False
    if time.time() - start > SESSION_TIMEOUT_SECONDS:
        _force_logout()
        return True
    return False


def check_auth() -> bool:
    credentials = _deep_copy_secrets("credentials")
    if not credentials:
        return True

    cookie = _deep_copy_secrets("cookie")

    authenticator = stauth.Authenticate(
        {"usernames": credentials},
        cookie.get("name", "master_prediction_auth"),
        cookie.get("key", "default_key"),
        cookie.get("expiry_days", 0.0208),
    )

    if st.session_state.get("authentication_status"):
        expired = _check_session_timeout()
        if expired:
            st.warning("Tu sesion ha expirado (30 min). Inicia sesion nuevamente.")
            st.rerun()

        remaining = SESSION_TIMEOUT_SECONDS - (
            time.time() - st.session_state.get("session_start", time.time())
        )
        minutes_left = max(0, int(remaining // 60))

        with st.sidebar:
            st.markdown(f"**{st.session_state.get('name', '')}**")
            st.caption(f"Sesion: {minutes_left} min restantes")
            authenticator.logout("Cerrar sesion", "sidebar")
        return True

    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(LOGIN_HEADER, unsafe_allow_html=True)

    st.markdown('<div class="login-page">', unsafe_allow_html=True)
    authenticator.login()

    if st.session_state.get("authentication_status"):
        st.session_state["session_start"] = time.time()
        st.rerun()

    if st.session_state.get("authentication_status") is False:
        st.error("Usuario o contraseña incorrectos")

    if st.session_state.get("authentication_status") is None:
        st.info("Ingresa tus credenciales para acceder")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(LOGIN_FOOTER, unsafe_allow_html=True)

    return False
