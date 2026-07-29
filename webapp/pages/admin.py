"""Admin — user management and access requests."""

import secrets
import string
from datetime import datetime, timezone

import bcrypt
from nicegui import app, ui

from webapp.data import get_supabase_client
from webapp.theme import render_mini_strip


def _gen_password() -> str:
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def render():
    render_mini_strip("Admin", "Sistema", "gear")

    role = app.storage.user.get("role", "viewer")
    if role != "admin":
        ui.html(
            '<div class="placeholder-box">'
            '<div class="ph-icon">🔒</div>'
            '<div class="ph-title">Acceso restringido a administradores.</div>'
            "</div>"
        )
        return

    client = get_supabase_client()

    # ── Access Requests ──
    try:
        req_resp = (
            client.table("access_requests")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        requests_data = req_resp.data or []
    except Exception:
        requests_data = []

    pending = [r for r in requests_data if r.get("status") == "pending"]

    if pending:
        ui.html(
            f'<div class="kpi-row">'
            f'<div class="kpi"><div class="kpi-val" style="color:var(--draw-color)">{len(pending)}</div>'
            f'<div class="kpi-lbl">Solicitudes pendientes</div></div>'
            f"</div>"
        )

        for req in pending:
            with ui.element("div").style(
                "background:var(--surface);border:1px solid var(--edge);"
                "border-radius:var(--radius);padding:14px 16px;margin-bottom:8px"
            ):
                ui.html(
                    f'<div style="font-size:14px;font-weight:600">{req["name"]}</div>'
                    f'<div style="font-size:12px;color:var(--text-3)">'
                    f"{req['email']} · {req.get('created_at', '')[:10]}"
                    f"</div>"
                    f'<div style="font-size:11px;color:var(--text-3);margin-top:4px">'
                    f"Motivo: {req.get('reason') or 'No especificado'}</div>"
                )
                with ui.row().classes("gap-2 mt-2"):

                    def _approve(r=req):
                        base = r["email"].split("@")[0].lower().replace(".", "_")
                        base = "".join(c for c in base if c.isalnum() or c == "_")
                        pwd = _gen_password()
                        hashed = _hash_password(pwd)
                        try:
                            client.table("app_users").insert(
                                {
                                    "username": base,
                                    "name": r["name"],
                                    "email": r["email"],
                                    "password_hash": hashed,
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
                                    "reviewed_by": app.storage.user.get("username"),
                                }
                            ).eq("id", r["id"]).execute()
                            ui.notify(f"Usuario {base} creado. Password: {pwd}", type="positive")
                            ui.navigate.to("/admin")
                        except Exception as e:
                            ui.notify(f"Error: {e}", type="negative")

                    def _reject(r=req):
                        try:
                            now = datetime.now(timezone.utc).isoformat()
                            client.table("access_requests").update(
                                {
                                    "status": "rejected",
                                    "reviewed_at": now,
                                    "reviewed_by": app.storage.user.get("username"),
                                }
                            ).eq("id", r["id"]).execute()
                            ui.notify("Solicitud rechazada", type="warning")
                            ui.navigate.to("/admin")
                        except Exception as e:
                            ui.notify(f"Error: {e}", type="negative")

                    ui.button("Aprobar", on_click=_approve).props(
                        'unelevated dense color="positive" size="sm"'
                    )
                    ui.button("Rechazar", on_click=_reject).props(
                        'unelevated dense color="negative" size="sm"'
                    )

    # ── Load Users ──
    try:
        users_resp = client.table("app_users").select("*").order("created_at", desc=True).execute()
        db_users = users_resp.data or []
    except Exception:
        db_users = []

    total = len(db_users) + 1
    active = sum(1 for u in db_users if u.get("is_active", True)) + 1

    ui.html(
        f'<div class="kpi-row" style="margin-top:20px">'
        f'<div class="kpi"><div class="kpi-val">{total}</div>'
        f'<div class="kpi-lbl">Total usuarios</div></div>'
        f'<div class="kpi"><div class="kpi-val" style="color:var(--hit)">{active}</div>'
        f'<div class="kpi-lbl">Activos</div></div>'
        f"</div>"
    )

    # ── Create User Form ──
    with (
        ui.expansion("Crear usuario manual")
        .classes("mt-4")
        .style("background:var(--surface);border:1px solid var(--edge);border-radius:var(--radius)")
    ):
        with ui.column().classes("w-full gap-2 p-2"):
            cr_name = (
                ui.input("Nombre").props('outlined dense dark color="orange-8"').classes("w-full")
            )
            cr_email = (
                ui.input("Email").props('outlined dense dark color="orange-8"').classes("w-full")
            )
            cr_user = (
                ui.input("Username").props('outlined dense dark color="orange-8"').classes("w-full")
            )
            cr_role = (
                ui.select(
                    {"viewer": "Viewer", "admin": "Admin"},
                    value="viewer",
                    label="Rol",
                )
                .props('outlined dense dark color="orange-8"')
                .classes("w-40")
            )

            def _auto_suggest():
                if cr_email.value and not cr_user.value:
                    base = cr_email.value.split("@")[0].lower().replace(".", "_")
                    cr_user.value = "".join(c for c in base if c.isalnum() or c == "_")

            cr_email.on("blur", _auto_suggest)

            def _create_user():
                if not cr_name.value or not cr_email.value or not cr_user.value:
                    ui.notify("Nombre, email y username son requeridos", type="warning")
                    return
                pwd = _gen_password()
                hashed = _hash_password(pwd)
                try:
                    client.table("app_users").insert(
                        {
                            "username": cr_user.value.strip(),
                            "name": cr_name.value.strip(),
                            "email": cr_email.value.strip(),
                            "password_hash": hashed,
                            "role": cr_role.value,
                            "is_active": True,
                            "must_change_password": True,
                        }
                    ).execute()
                    ui.notify(
                        f"Usuario {cr_user.value} creado. Password temporal: {pwd}", type="positive"
                    )
                    ui.navigate.to("/admin")
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")

            ui.button("Crear usuario", on_click=_create_user).props('unelevated color="orange-8"')

    # ── User Table (Interactive) ──
    ui.html(
        '<div class="standings-panel" style="margin-top:16px">'
        '<div class="ml-head"><h2>Usuarios</h2></div>'
        "</div>"
    )

    # System user row (no actions)
    with (
        ui.row()
        .classes("w-full items-center gap-3")
        .style(
            "background:var(--surface);border:1px solid var(--edge);"
            "border-radius:var(--radius);padding:10px 14px;margin-bottom:6px"
        )
    ):
        ui.label("ivan (sistema)").style("font-size:13px;font-weight:600;min-width:140px")
        ui.label("—").style("font-size:11px;color:var(--text-3);min-width:160px")
        ui.label("admin").style("font-size:11px;color:var(--flame);min-width:60px")
        ui.label("Activo").style("font-size:11px;color:var(--hit)")

    # DB users with action buttons
    for u in db_users:
        _render_user_row(u, client)

    # ── Request History ──
    if requests_data:
        with (
            ui.expansion("Historial de solicitudes")
            .classes("mt-4")
            .style(
                "background:var(--surface);border:1px solid var(--edge);border-radius:var(--radius)"
            )
        ):
            status_labels = {
                "pending": "Pendiente",
                "approved": "Aprobada",
                "rejected": "Rechazada",
            }
            h_html = '<div style="padding:8px">'
            for r in requests_data:
                status = status_labels.get(r.get("status", "pending"), r.get("status"))
                h_html += (
                    f'<div style="font-size:12px;padding:6px 0;border-bottom:1px solid var(--edge)">'
                    f"{r.get('created_at', '')[:10]} · "
                    f"<strong>{r.get('name', '—')}</strong> ({r.get('email', '—')}) · "
                    f"{status}</div>"
                )
            h_html += "</div>"
            ui.html(h_html)


def _render_user_row(u: dict, client):
    is_active = u.get("is_active", True)
    status_text = "Activo" if is_active else "Inactivo"
    s_color = "var(--hit)" if is_active else "var(--miss)"
    r_color = "var(--flame)" if u["role"] == "admin" else "var(--text-2)"

    with (
        ui.row()
        .classes("w-full items-center gap-3")
        .style(
            "background:var(--surface);border:1px solid var(--edge);"
            "border-radius:var(--radius);padding:10px 14px;margin-bottom:6px"
        )
    ):
        ui.label(u["username"]).style("font-size:13px;font-weight:600;min-width:140px")
        ui.label(u.get("email", "—")).style("font-size:11px;color:var(--text-3);min-width:160px")
        ui.label(u["role"]).style(f"font-size:11px;color:{r_color};min-width:60px")
        ui.label(status_text).style(f"font-size:11px;color:{s_color};min-width:60px")

        with ui.row().classes("gap-1 ml-auto"):
            new_role = "admin" if u["role"] == "viewer" else "viewer"

            def _toggle_role(uid=u["id"], nr=new_role):
                try:
                    client.table("app_users").update({"role": nr}).eq("id", uid).execute()
                    ui.notify(f"Rol cambiado a {nr}", type="info")
                    ui.navigate.to("/admin")
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")

            def _toggle_active(uid=u["id"], current=is_active):
                try:
                    client.table("app_users").update({"is_active": not current}).eq(
                        "id", uid
                    ).execute()
                    state = "desactivado" if current else "activado"
                    ui.notify(f"Usuario {state}", type="info")
                    ui.navigate.to("/admin")
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")

            def _reset_pw(uid=u["id"], uname=u["username"]):
                pwd = _gen_password()
                hashed = _hash_password(pwd)
                try:
                    client.table("app_users").update(
                        {
                            "password_hash": hashed,
                            "must_change_password": True,
                        }
                    ).eq("id", uid).execute()
                    ui.notify(f"Password de {uname}: {pwd}", type="positive")
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")

            def _delete(uid=u["id"], uname=u["username"]):
                confirm_dialog = ui.dialog()
                with confirm_dialog, ui.card():
                    ui.label(f"Eliminar usuario {uname}?").classes("font-bold")
                    ui.label("Esta accion no se puede deshacer.").style(
                        "font-size:12px;color:var(--text-3)"
                    )
                    with ui.row().classes("gap-2 mt-3"):

                        def _do_delete():
                            try:
                                client.table("app_users").delete().eq("id", uid).execute()
                                ui.notify(f"Usuario {uname} eliminado", type="warning")
                                confirm_dialog.close()
                                ui.navigate.to("/admin")
                            except Exception as e:
                                ui.notify(f"Error: {e}", type="negative")

                        ui.button("Eliminar", on_click=_do_delete).props(
                            'unelevated dense color="negative" size="sm"'
                        )
                        ui.button("Cancelar", on_click=confirm_dialog.close).props(
                            'flat dense size="sm"'
                        )
                confirm_dialog.open()

            ui.button(icon="swap_horiz", on_click=_toggle_role).props(
                'flat dense round size="sm"'
            ).tooltip(f"Cambiar a {new_role}")
            ui.button(
                icon="toggle_on" if is_active else "toggle_off",
                on_click=_toggle_active,
            ).props('flat dense round size="sm"').tooltip("Desactivar" if is_active else "Activar")
            ui.button(icon="lock_reset", on_click=_reset_pw).props(
                'flat dense round size="sm"'
            ).tooltip("Resetear password")
            ui.button(icon="delete", on_click=_delete).props(
                'flat dense round size="sm" color="negative"'
            ).tooltip("Eliminar usuario")
