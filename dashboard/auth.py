import base64
import hashlib
import hmac
import time
from collections.abc import Mapping

import bcrypt
import streamlit as st

from dashboard.data_access import get_supabase_client

SESSION_TIMEOUT_SECONDS = 15 * 60
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
MIN_PASSWORD_LENGTH = 12

REMEMBER_COOKIE = "mp_remember"
REMEMBER_DAYS = 30
REMEMBER_TIMEOUT = REMEMBER_DAYS * 24 * 60 * 60

ROLE_LABELS = {"admin": "Administrador", "viewer": "Viewer"}

LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

/* ── Hide sidebar on login ── */
[data-testid="stSidebar"] { display: none; }

/* ── Base ── */
.stApp { background: #07090c !important; }
.stMainBlockContainer {
    padding-top: 1rem !important;
    padding-bottom: 0 !important;
    font-family: 'DM Sans', system-ui, sans-serif !important;
}

/* ── Login container ── */
[data-testid="stForm"] {
    max-width: 400px;
    margin: 0 auto;
    background: #0c1015;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 18px;
    padding: 2rem 2.5rem;
}

/* ── Input fields ── */
[data-testid="stForm"] input {
    background: #11151b !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 11px !important;
    color: #eef1f5 !important;
    padding: 0.65rem 1rem !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: all 0.2s ease !important;
}

[data-testid="stForm"] input:focus {
    border-color: rgba(22, 196, 127, 0.35) !important;
    box-shadow: 0 0 0 3px rgba(22, 196, 127, 0.08) !important;
    background: #11151b !important;
}

/* ── Login button ── */
[data-testid="stForm"] button[type="submit"] {
    background: linear-gradient(135deg, #16c47f, #0fa268) !important;
    color: #06140e !important;
    border: none !important;
    border-radius: 11px !important;
    padding: 0.65rem 2rem !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    width: 100%;
    transition: all 0.25s ease !important;
    box-shadow: 0 10px 30px rgba(22, 196, 127, 0.30) !important;
}

[data-testid="stForm"] button[type="submit"]:hover {
    box-shadow: 0 8px 26px rgba(22, 196, 127, 0.34) !important;
    transform: translateY(-1px) !important;
}

/* ── Labels ── */
[data-testid="stForm"] label {
    color: #8b94a2 !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ── Remember checkbox ── */
[data-testid="stForm"] [data-testid="stCheckbox"] label {
    text-transform: none !important;
    letter-spacing: normal !important;
    font-size: 0.82rem !important;
    color: #6b7382 !important;
}

/* ── Responsive ── */
@media (max-width: 480px) {
    [data-testid="stForm"] { padding: 1.5rem 1.2rem; }
}
</style>
"""

LOGIN_HEADER = """
<div style="text-align:center;padding:2rem 0 1.5rem;
    background:radial-gradient(120% 90% at 15% 0%, #0f3b2c 0%, #0a1714 38%, #07090c 78%);
    border-radius:18px;margin-bottom:1rem;">
    <div style="font-size:12px;font-weight:600;letter-spacing:0.12em;
        text-transform:uppercase;color:#16c47f;margin-bottom:12px;
        font-family:'DM Sans',sans-serif;">
        Inteligencia deportiva &middot; IA
    </div>
    <h1 style="
        color:#eef1f5;font-size:2.2rem;font-weight:800;margin:0;
        letter-spacing:-0.02em;font-family:'Sora',sans-serif;
    ">Predice el partido antes<br>del pitido inicial.</h1>
    <p style="
        color:#8b94a2;font-size:0.88rem;margin-top:12px;max-width:480px;
        margin-left:auto;margin-right:auto;line-height:1.5;
        font-family:'DM Sans',sans-serif;
    ">Modelos probabilisticos entrenados sobre miles de encuentros.
    Probabilidades 1X2, goles esperados y BTTS en tiempo real.</p>
    <div style="display:flex;justify-content:center;gap:32px;margin-top:20px;">
        <div>
            <div style="color:#eef1f5;font-size:1.6rem;font-weight:800;
                font-family:'Sora',sans-serif;">12.4k</div>
            <div style="color:#6b7382;font-size:0.72rem;text-transform:uppercase;
                letter-spacing:0.06em;font-weight:500;">partidos analizados</div>
        </div>
        <div>
            <div style="color:#eef1f5;font-size:1.6rem;font-weight:800;
                font-family:'Sora',sans-serif;">68%</div>
            <div style="color:#6b7382;font-size:0.72rem;text-transform:uppercase;
                letter-spacing:0.06em;font-weight:500;">acierto alta conf.</div>
        </div>
        <div>
            <div style="color:#eef1f5;font-size:1.6rem;font-weight:800;
                font-family:'Sora',sans-serif;">6</div>
            <div style="color:#6b7382;font-size:0.72rem;text-transform:uppercase;
                letter-spacing:0.06em;font-weight:500;">ligas cubiertas</div>
        </div>
    </div>
</div>
<div style="text-align:center;margin-bottom:8px;">
    <h2 style="color:#eef1f5;font-size:1.2rem;font-weight:700;margin:0;
        font-family:'Sora',sans-serif;">Bienvenido de vuelta</h2>
    <p style="color:#6b7382;font-size:0.82rem;margin:4px 0 0;">
        Ingresa tus credenciales para acceder al panel.</p>
</div>
"""

LOGIN_FOOTER = """
<div style="text-align:center;padding:1rem 0 0;font-family:'DM Sans',sans-serif;">
    <p style="color:#6b7382;font-size:0.72rem;letter-spacing:0.04em;">
        Powered by AI &middot; v1.0
    </p>
</div>
"""


# ── Helpers ──────────────────────────────────────────────────────────────


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


# ── Remember-session token ───────────────────────────────────────────────


def _get_signing_key() -> str:
    try:
        raw = st.secrets.get("SUPABASE_SERVICE_KEY", "") or st.secrets.get("SUPABASE_KEY", "")
        if not raw:
            raw = st.secrets.get("supabase", {}).get("key", "")
    except Exception:
        raw = ""
    return hashlib.sha256(f"mp-remember:{raw}".encode()).hexdigest()


def _make_remember_token(username: str) -> str:
    expires = int(time.time()) + REMEMBER_TIMEOUT
    payload = f"{username}:{expires}"
    sig = hmac.new(_get_signing_key().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()


def _verify_remember_token(token: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        parts = raw.rsplit(":", 2)
        if len(parts) != 3:
            return None
        username, expires_str, sig = parts
        if time.time() > int(expires_str):
            return None
        payload = f"{username}:{expires_str}"
        expected = hmac.new(
            _get_signing_key().encode(), payload.encode(), hashlib.sha256
        ).hexdigest()[:32]
        if not hmac.compare_digest(sig, expected):
            return None
        return username
    except Exception:
        return None


def _get_remember_cookie() -> str | None:
    try:
        return st.context.cookies.get(REMEMBER_COOKIE)
    except Exception:
        return None


def _set_remember_cookie(token: str):
    st.markdown(
        f"<script>"
        f'document.cookie="{REMEMBER_COOKIE}={token};'
        f'max-age={REMEMBER_TIMEOUT};path=/;SameSite=Strict";'
        f"</script>",
        unsafe_allow_html=True,
    )


def _clear_remember_cookie():
    st.markdown(
        f'<script>document.cookie="{REMEMBER_COOKIE}=;max-age=0;path=/";</script>',
        unsafe_allow_html=True,
    )


def _lookup_user(username: str) -> dict | None:
    credentials = _deep_copy_secrets("credentials")
    user_data = credentials.get(username)
    if user_data:
        return {
            "username": username,
            "name": user_data.get("name", username),
            "role": user_data.get("role", "viewer"),
            "source": "secrets",
            "must_change_password": False,
        }
    try:
        client = get_supabase_client()
        resp = (
            client.table("app_users")
            .select("*")
            .eq("username", username)
            .eq("is_active", True)
            .execute()
        )
        if resp.data:
            user = resp.data[0]
            return {
                "username": user["username"],
                "name": user["name"],
                "role": user["role"],
                "source": "supabase",
                "must_change_password": user.get("must_change_password", False),
                "user_id": user["id"],
            }
    except Exception:
        pass
    return None


# ── Auth core ────────────────────────────────────────────────────────────


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


def _set_session(user: dict, *, remembered: bool = False):
    st.session_state["authentication_status"] = True
    st.session_state["username"] = user["username"]
    st.session_state["name"] = user["name"]
    st.session_state["user_role"] = user["role"]
    st.session_state["user_source"] = user["source"]
    st.session_state["must_change_password"] = user["must_change_password"]
    st.session_state["session_start"] = time.time()
    st.session_state["remembered_session"] = remembered
    if user.get("user_id"):
        st.session_state["user_id"] = user["user_id"]


def _force_logout():
    st.session_state["authentication_status"] = None
    st.session_state["name"] = None
    st.session_state["username"] = None
    st.session_state.pop("session_start", None)
    st.session_state.pop("user_source", None)
    st.session_state.pop("user_role", None)
    st.session_state.pop("must_change_password", None)
    st.session_state.pop("user_id", None)
    st.session_state.pop("remembered_session", None)
    st.session_state["_clear_remember_cookie"] = True


def _check_session_timeout() -> bool:
    start = st.session_state.get("session_start")
    if start is None:
        st.session_state["session_start"] = time.time()
        return False
    timeout = (
        REMEMBER_TIMEOUT if st.session_state.get("remembered_session") else SESSION_TIMEOUT_SECONDS
    )
    if time.time() - start > timeout:
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
    if st.session_state.pop("_clear_remember_cookie", False):
        _clear_remember_cookie()

    if st.session_state.get("authentication_status"):
        pending = st.session_state.pop("_pending_remember_token", None)
        if pending:
            _set_remember_cookie(pending)

        expired = _check_session_timeout()
        if expired:
            _clear_remember_cookie()
            st.warning("Tu sesion ha expirado. Inicia sesion nuevamente.")
            st.rerun()
        if st.session_state.get("must_change_password"):
            _handle_password_change()
            return False
        return True

    token = _get_remember_cookie()
    if token:
        username = _verify_remember_token(token)
        if username:
            user_data = _lookup_user(username)
            if user_data and not user_data.get("must_change_password"):
                _set_session(user_data, remembered=True)
                st.rerun()
        _clear_remember_cookie()

    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(LOGIN_HEADER, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        remember = st.checkbox("Recordar sesion")
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
                _set_session(user, remembered=remember)
                if remember:
                    st.session_state["_pending_remember_token"] = _make_remember_token(username)
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
        '<p style="color:#888; font-size:0.88rem;">'
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

    is_remembered = st.session_state.get("remembered_session", False)
    elapsed = time.time() - st.session_state.get("session_start", time.time())

    if is_remembered:
        days_left = max(0, int((REMEMBER_TIMEOUT - elapsed) / 86400))
        time_label = f"🔒 Sesion recordada · {days_left}d"
    else:
        minutes_left = max(0, int((SESSION_TIMEOUT_SECONDS - elapsed) / 60))
        time_label = f"⏱ {minutes_left} min restantes"

    role_label = ROLE_LABELS.get(user["role"], user["role"])

    _, col_user = st.columns([8, 2])
    with col_user:
        with st.popover(f"👤 {user['name']}", use_container_width=True):
            st.markdown(
                f'<p style="margin:0;color:#eef1f5;font-weight:600;">{user["name"]}</p>'
                f'<p style="margin:0.2rem 0 0 0;color:#16c47f;font-size:0.78rem;'
                f' font-weight:500;">'
                f"{role_label}</p>",
                unsafe_allow_html=True,
            )
            st.divider()
            st.caption(time_label)
            if st.button("🚪 Cerrar sesion", use_container_width=True):
                _force_logout()
                st.rerun()
