import time
from collections.abc import Mapping

import bcrypt
import streamlit as st

from dashboard.data_access import get_supabase_client

SESSION_TIMEOUT_SECONDS = 15 * 60
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
MIN_PASSWORD_LENGTH = 12

ROLE_LABELS = {"admin": "Administrador", "viewer": "Viewer"}

LOGIN_CSS = """
<style>
/* ── Hide sidebar on login ── */
[data-testid="stSidebar"] { display: none; }

/* ── Compact main block for login ── */
.stMainBlockContainer { padding-top: 1rem !important; padding-bottom: 0 !important; }

/* ── Login container ── */
[data-testid="stForm"] {
    max-width: 420px;
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

/* ── Responsive ── */
@media (max-width: 480px) {
    [data-testid="stForm"] { padding: 1.5rem 1.2rem; }
}
</style>
"""

LOGIN_HEADER = """
<div style="text-align: center; padding: 1rem 0 1.2rem 0;">
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
<div style="text-align: center; padding: 0.8rem 0 0;">
    <p style="color: rgba(160, 160, 160, 0.6); font-size: 0.75rem; letter-spacing: 0.5px;">
        Powered by AI &middot; v1.0
    </p>
</div>
"""


def _deep_copy_secrets(section: str) -> dict:
    raw = st.secrets.get(section, {})
    return _to_plain_dict(raw)


def _to_plain_dict(obj) -> dict:
    result = {}
    src = dict(obj) if isinstance(obj, Mapping) else {}
    for k, v in src.items():
        if isinstance(v, Mapping):
            result[k] = _to_plain_dict(v)
        elif isinstance(v, list):
            result[k] = [_to_plain_dict(i) if isinstance(i, Mapping) else i for i in v]
        else:
            result[k] = v
    return result


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _authenticate_secrets(username: str, password: str) -> dict | None:
    """Authenticate against Streamlit Secrets (admin fallback)."""
    credentials = _deep_copy_secrets("credentials")
    user_data = credentials.get(username)
    if not user_data:
        return None
    stored_hash = user_data.get("password", "")
    if not _verify_password(password, stored_hash):
        return None
    return {
        "username": username,
        "name": user_data.get("name", username),
        "role": user_data.get("role", "viewer"),
        "source": "secrets",
        "must_change_password": False,
    }


def _authenticate_supabase(username: str, password: str) -> dict | None:
    """Authenticate against app_users table in Supabase."""
    try:
        client = get_supabase_client()
        resp = (
            client.table("app_users")
            .select("*")
            .eq("username", username)
            .eq("is_active", True)
            .execute()
        )
        if not resp.data:
            return None
        user = resp.data[0]
        if not _verify_password(password, user["password_hash"]):
            return None
        return {
            "username": user["username"],
            "name": user["name"],
            "role": user["role"],
            "source": "supabase",
            "must_change_password": user.get("must_change_password", False),
            "user_id": user["id"],
        }
    except Exception:
        return None


def _force_logout():
    st.session_state["authentication_status"] = None
    st.session_state["name"] = None
    st.session_state["username"] = None
    st.session_state.pop("session_start", None)
    st.session_state.pop("user_source", None)
    st.session_state.pop("user_role", None)
    st.session_state.pop("must_change_password", None)
    st.session_state.pop("user_id", None)


def _check_session_timeout() -> bool:
    start = st.session_state.get("session_start")
    if start is None:
        st.session_state["session_start"] = time.time()
        return False
    if time.time() - start > SESSION_TIMEOUT_SECONDS:
        _force_logout()
        return True
    return False


def get_current_user() -> dict | None:
    if not st.session_state.get("authentication_status"):
        return None
    return {
        "username": st.session_state.get("username", ""),
        "name": st.session_state.get("name", ""),
        "role": st.session_state.get("user_role", "viewer"),
    }


def require_admin() -> bool:
    user = get_current_user()
    if not user or user["role"] != "admin":
        st.error("Acceso restringido. Se requiere rol de administrador.")
        return False
    return True


def _is_locked_out() -> bool:
    attempts = st.session_state.get("login_attempts", 0)
    lockout_time = st.session_state.get("lockout_until", 0)
    if attempts >= MAX_LOGIN_ATTEMPTS and time.time() < lockout_time:
        return True
    if time.time() >= lockout_time:
        st.session_state["login_attempts"] = 0
    return False


def _record_failed_attempt():
    attempts = st.session_state.get("login_attempts", 0) + 1
    st.session_state["login_attempts"] = attempts
    if attempts >= MAX_LOGIN_ATTEMPTS:
        st.session_state["lockout_until"] = time.time() + LOCKOUT_SECONDS


def _do_login(username: str, password: str) -> dict | None:
    """Try Secrets first, then Supabase."""
    result = _authenticate_secrets(username, password)
    if result:
        st.session_state["login_attempts"] = 0
        return result
    result = _authenticate_supabase(username, password)
    if result:
        st.session_state["login_attempts"] = 0
    return result


def _handle_password_change():
    """Force password change dialog for first-time users."""
    st.warning("Debes cambiar tu contraseña antes de continuar.")
    with st.form("change_password_form"):
        new_pass = st.text_input("Nueva contraseña", type="password")
        confirm_pass = st.text_input("Confirmar contraseña", type="password")
        submitted = st.form_submit_button("Cambiar contraseña", use_container_width=True)

    if submitted:
        if not new_pass or len(new_pass) < MIN_PASSWORD_LENGTH:
            st.error(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
            return False
        if new_pass != confirm_pass:
            st.error("Las contraseñas no coinciden.")
            return False
        try:
            client = get_supabase_client()
            client.table("app_users").update(
                {
                    "password_hash": _hash_password(new_pass),
                    "must_change_password": False,
                }
            ).eq("id", st.session_state["user_id"]).execute()
            st.session_state["must_change_password"] = False
            st.success("Contraseña actualizada correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al cambiar contraseña: {e}")
            return False
    return False


def check_auth() -> bool:
    if st.session_state.get("authentication_status"):
        expired = _check_session_timeout()
        if expired:
            st.warning("Tu sesion ha expirado (15 min). Inicia sesion nuevamente.")
            st.rerun()
        if st.session_state.get("must_change_password"):
            _handle_password_change()
            return False
        return True

    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(LOGIN_HEADER, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar sesion", use_container_width=True)

    if submitted and username and password:
        if _is_locked_out():
            remaining = int((st.session_state.get("lockout_until", 0) - time.time()) / 60)
            st.error(
                f"Demasiados intentos fallidos. Intenta de nuevo en {max(1, remaining)} minutos."
            )
        else:
            user = _do_login(username, password)
            if user:
                st.session_state["authentication_status"] = True
                st.session_state["username"] = user["username"]
                st.session_state["name"] = user["name"]
                st.session_state["user_role"] = user["role"]
                st.session_state["user_source"] = user["source"]
                st.session_state["must_change_password"] = user["must_change_password"]
                st.session_state["session_start"] = time.time()
                if user.get("user_id"):
                    st.session_state["user_id"] = user["user_id"]
                st.rerun()
            else:
                _record_failed_attempt()

    _, center, _ = st.columns([1.5, 2, 1.5])
    with center:
        if submitted and username and password and not _is_locked_out():
            st.error("Usuario o contraseña incorrectos")

        if not submitted:
            st.info("Ingresa tus credenciales para acceder")

        if st.button("📋 Solicitar acceso", key="btn_register", use_container_width=True):
            _show_access_request()

        st.markdown(LOGIN_FOOTER, unsafe_allow_html=True)

    return False


@st.dialog("Solicitar Acceso")
def _show_access_request():
    st.markdown(
        '<p style="color:#a5d6a7; font-size:0.9rem;">'
        "Completa el formulario para solicitar acceso como Viewer.</p>",
        unsafe_allow_html=True,
    )
    name = st.text_input("Nombre completo")
    email = st.text_input("Email")
    reason = st.text_area("Motivo (opcional)", height=80)

    if st.button("Enviar solicitud", use_container_width=True, type="primary"):
        if not name or not email:
            st.warning("Nombre y email son obligatorios.")
            return
        try:
            client = get_supabase_client()
            client.table("access_requests").insert(
                {"name": name, "email": email, "reason": reason}
            ).execute()
        except Exception:
            pass
        st.success(
            "Solicitud enviada correctamente. "
            "El administrador revisara tu solicitud y te contactara por email."
        )


def render_user_menu():
    user = get_current_user()
    if not user:
        return

    remaining = SESSION_TIMEOUT_SECONDS - (
        time.time() - st.session_state.get("session_start", time.time())
    )
    minutes_left = max(0, int(remaining // 60))
    role_label = ROLE_LABELS.get(user["role"], user["role"])

    _, col_user = st.columns([8, 2])
    with col_user:
        with st.popover(f"👤 {user['name']}", use_container_width=True):
            st.markdown(
                f'<p style="margin:0;color:#e0e0e0;font-weight:600;">{user["name"]}</p>'
                f'<p style="margin:0.2rem 0 0 0;color:#81C784;font-size:0.8rem;">'
                f"{role_label}</p>",
                unsafe_allow_html=True,
            )
            st.divider()
            st.caption(f"⏱ {minutes_left} min restantes")
            if st.button("🚪 Cerrar sesion", use_container_width=True):
                _force_logout()
                st.rerun()
