import secrets
import string
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from backend.notifications.email import send_welcome_email
from dashboard.auth import _deep_copy_secrets, _hash_password, get_current_user, require_admin
from dashboard.components.theme import page_header, section_header, stat_card
from dashboard.data_access import get_supabase_client

if not require_admin():
    st.stop()

st.markdown(page_header("⚙️", "Admin"), unsafe_allow_html=True)

client = get_supabase_client()
admin_user = get_current_user()

STATUS_LABELS = {
    "pending": "⏳ Pendiente",
    "approved": "✅ Aprobada",
    "rejected": "❌ Rechazada",
}


def _generate_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _create_username(name: str, email: str) -> str:
    base = email.split("@")[0].lower().replace(".", "_").replace("-", "_")
    base = "".join(c for c in base if c.isalnum() or c == "_")
    try:
        existing = client.table("app_users").select("username").eq("username", base).execute()
        if existing.data:
            base = f"{base}_{secrets.randbelow(999):03d}"
    except Exception:
        pass
    return base


@st.dialog("Aprobar Solicitud")
def _approve_request(req: dict):
    st.markdown(f"**Nombre:** {req['name']}")
    st.markdown(f"**Email:** {req['email']}")

    username = st.text_input("Usuario", value=_create_username(req["name"], req["email"]))
    temp_password = _generate_temp_password()
    st.text_input("Contraseña temporal", value=temp_password, disabled=True)
    st.caption("El usuario debera cambiar esta contraseña en su primer inicio de sesion.")

    if st.button("Confirmar aprobacion", type="primary", use_container_width=True):
        try:
            client.table("app_users").insert(
                {
                    "username": username,
                    "name": req["name"],
                    "email": req["email"],
                    "password_hash": _hash_password(temp_password),
                    "role": "viewer",
                    "is_active": True,
                    "must_change_password": True,
                }
            ).execute()

            now = datetime.now(timezone.utc).isoformat()
            client.table("access_requests").update(
                {
                    "status": "approved",
                    "reviewed_at": now,
                    "reviewed_by": admin_user["username"],
                }
            ).eq("id", req["id"]).execute()

            st.success(f"Usuario **{username}** creado exitosamente.")

            email_sent = send_welcome_email(req["email"], req["name"], username, temp_password)
            if email_sent:
                st.info(f"📧 Email con credenciales enviado a {req['email']}")
            else:
                st.markdown(
                    f"**Credenciales para compartir manualmente:**\n\n"
                    f"- Usuario: `{username}`\n"
                    f"- Contraseña: `{temp_password}`"
                )
                st.caption(
                    "No se pudo enviar email. Copia estas credenciales"
                    " antes de cerrar este dialogo."
                )
        except Exception as e:
            err = str(e).lower()
            if "duplicate" in err or "unique" in err:
                st.error(
                    "Ya existe un usuario con ese nombre. Cambia el usuario e intenta de nuevo."
                )
            else:
                st.error(f"Error al crear usuario: {e}")


@st.dialog("Rechazar Solicitud")
def _reject_request(req: dict):
    st.markdown(f"¿Rechazar la solicitud de **{req['name']}** ({req['email']})?")

    if st.button("Confirmar rechazo", type="primary", use_container_width=True):
        try:
            now = datetime.now(timezone.utc).isoformat()
            client.table("access_requests").update(
                {
                    "status": "rejected",
                    "reviewed_at": now,
                    "reviewed_by": admin_user["username"],
                }
            ).eq("id", req["id"]).execute()
            st.success("Solicitud rechazada.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


@st.dialog("Resetear Contraseña")
def _reset_password(user: dict):
    st.markdown(f"Resetear contraseña de **{user['name']}** ({user['username']})")
    new_temp = _generate_temp_password()
    st.text_input("Nueva contraseña temporal", value=new_temp, disabled=True)

    if st.button("Confirmar reset", type="primary", use_container_width=True):
        try:
            client.table("app_users").update(
                {
                    "password_hash": _hash_password(new_temp),
                    "must_change_password": True,
                }
            ).eq("id", user["id"]).execute()
            st.success("Contraseña reseteada.")
            st.markdown(
                f"**Credenciales para compartir:**\n\n"
                f"- Usuario: `{user['username']}`\n"
                f"- Contraseña: `{new_temp}`"
            )
        except Exception as e:
            st.error(f"Error: {e}")


@st.dialog("Eliminar Usuario")
def _delete_user(user: dict):
    st.markdown(
        f"⚠️ ¿Eliminar permanentemente a **{user['name']}** ({user['username']})?\n\n"
        "Esta accion no se puede deshacer."
    )

    if st.button("Confirmar eliminacion", type="primary", use_container_width=True):
        try:
            client.table("app_users").delete().eq("id", user["id"]).execute()
            st.success("Usuario eliminado.")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ── Solicitudes de acceso ──
st.markdown(section_header("📋", "Solicitudes de Acceso"), unsafe_allow_html=True)

try:
    req_resp = (
        client.table("access_requests")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    requests_data = req_resp.data or []
except Exception as e:
    st.error(f"Error al cargar solicitudes: {e}")
    requests_data = []

pending_requests = [r for r in requests_data if r.get("status", "pending") == "pending"]

if pending_requests:
    st.warning(f"{len(pending_requests)} solicitud(es) pendiente(s) de revision")

    for req in pending_requests:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(
                    f"**{req['name']}** · {req['email']}\n\n"
                    f"Fecha: {req.get('created_at', '')[:10]} · "
                    f"Motivo: {req.get('reason') or 'No especificado'}",
                )
            with c2:
                if st.button("✅ Aprobar", key=f"approve_{req['id']}", use_container_width=True):
                    _approve_request(req)
            with c3:
                if st.button("❌ Rechazar", key=f"reject_{req['id']}", use_container_width=True):
                    _reject_request(req)

elif requests_data:
    with st.expander("Historial de solicitudes"):
        rows = []
        for r in requests_data:
            rows.append(
                {
                    "Fecha": r.get("created_at", "")[:10],
                    "Nombre": r.get("name", "—"),
                    "Email": r.get("email", "—"),
                    "Estado": STATUS_LABELS.get(r.get("status", "pending"), r.get("status")),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No hay solicitudes de acceso.")


# ── Usuarios registrados ──
st.markdown(section_header("👥", "Usuarios Registrados"), unsafe_allow_html=True)

try:
    users_resp = client.table("app_users").select("*").order("created_at", desc=True).execute()
    db_users = users_resp.data or []
except Exception as e:
    st.error(f"Error al cargar usuarios: {e}")
    db_users = []

secrets_users = _deep_copy_secrets("credentials")
total_users = len(db_users) + len(secrets_users)
active_count = sum(1 for u in db_users if u.get("is_active", True)) + len(secrets_users)

c1, c2 = st.columns(2)
with c1:
    st.markdown(
        stat_card("Total Usuarios", str(total_users), "registrados"),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        stat_card("Activos", str(active_count), f"de {total_users}"),
        unsafe_allow_html=True,
    )

if secrets_users:
    st.caption("Usuarios del sistema (Streamlit Secrets)")
    secret_rows = []
    for username, data in secrets_users.items():
        secret_rows.append(
            {
                "Usuario": username,
                "Nombre": data.get("name", "—"),
                "Rol": data.get("role", "viewer"),
                "Estado": "🟢 Activo",
                "Origen": "Sistema",
            }
        )
    st.dataframe(pd.DataFrame(secret_rows), use_container_width=True, hide_index=True)

if db_users:
    st.caption("Usuarios gestionados")
    user_rows = []
    for u in db_users:
        status = "🟢 Activo" if u.get("is_active", True) else "🔴 Desactivado"
        user_rows.append(
            {
                "Usuario": u["username"],
                "Nombre": u["name"],
                "Email": u.get("email", "—"),
                "Rol": u["role"],
                "Estado": status,
                "Creado": u.get("created_at", "")[:10],
            }
        )
    st.dataframe(pd.DataFrame(user_rows), use_container_width=True, hide_index=True)

    st.markdown(section_header("🔧", "Gestionar Usuario"), unsafe_allow_html=True)

    usernames = [u["username"] for u in db_users]
    selected_username = st.selectbox("Seleccionar usuario", usernames)

    if selected_username:
        selected_user = next(u for u in db_users if u["username"] == selected_username)

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            new_role = st.selectbox(
                "Rol",
                ["viewer", "admin"],
                index=0 if selected_user["role"] == "viewer" else 1,
                key="role_select",
            )
            if new_role != selected_user["role"]:
                if st.button("Cambiar rol", use_container_width=True):
                    client.table("app_users").update({"role": new_role}).eq(
                        "id", selected_user["id"]
                    ).execute()
                    st.success(f"Rol cambiado a **{new_role}**")
                    st.rerun()

        with col_b:
            is_active = selected_user.get("is_active", True)
            label = "🔴 Desactivar" if is_active else "🟢 Activar"
            if st.button(label, use_container_width=True):
                client.table("app_users").update({"is_active": not is_active}).eq(
                    "id", selected_user["id"]
                ).execute()
                action = "desactivado" if is_active else "activado"
                st.success(f"Usuario **{action}**")
                st.rerun()

        with col_c:
            if st.button("🔑 Reset password", use_container_width=True):
                _reset_password(selected_user)

        with col_d:
            if st.button("🗑️ Eliminar", use_container_width=True):
                _delete_user(selected_user)

elif not secrets_users:
    st.info("No hay usuarios registrados.")
