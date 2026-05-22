import copy

import streamlit as st
import streamlit_authenticator as stauth


def _deep_copy_secrets(section: str) -> dict:
    raw = st.secrets.get(section, {})
    return copy.deepcopy(dict(raw))


def check_auth() -> bool:
    credentials = _deep_copy_secrets("credentials")
    if not credentials:
        return True

    cookie = _deep_copy_secrets("cookie")

    authenticator = stauth.Authenticate(
        {"usernames": credentials},
        cookie.get("name", "master_prediction_auth"),
        cookie.get("key", "default_key"),
        cookie.get("expiry_days", 30),
    )

    authenticator.login()

    if st.session_state.get("authentication_status"):
        with st.sidebar:
            st.markdown(f"**{st.session_state.get('name', '')}**")
            authenticator.logout("Cerrar sesion", "sidebar")
        return True

    if st.session_state.get("authentication_status") is False:
        st.error("Usuario o contraseña incorrectos")

    if st.session_state.get("authentication_status") is None:
        st.info("Ingresa tus credenciales para acceder")

    return False
