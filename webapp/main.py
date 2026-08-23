"""Master Prediction — NiceGUI app with V3 broadcast design."""

import os
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from nicegui import app, ui

from backend.api.chat import router as chat_router
from backend.api.performance import router as perf_router
from webapp.theme import CSS, SIDEBAR_ICONS, render_footer

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

USERS = {
    "ivan": {
        "name": "Ivan Molina",
        "password_hash": "$2b$12$yRuUr8CjGABqhcRU5PCnBe7KfThGCLLK..zkV2KlRCictRTMmAbd2",
        "role": "admin",
    },
}

NAV = [
    {"icon": "home", "path": "/", "label": "Home"},
    {"icon": "trophy", "path": "/mundial", "label": "Mundial"},
    {"sep": True},
    {"icon": "grid", "path": "/liga", "label": "Ligas"},
    {"icon": "search", "path": "/equipo", "label": "Equipo"},
    {"icon": "scale", "path": "/comparador", "label": "Comparador"},
    {"sep": True},
    {"icon": "clock", "path": "/predicciones", "label": "Predicciones"},
    {"icon": "chat", "path": "/asesor", "label": "Asesor"},
    {"sep": True},
    {"icon": "target", "path": "/calibracion", "label": "Calibracion"},
    {"icon": "pulse", "path": "/tendencias", "label": "Tendencias"},
    {"sep": True},
    {"icon": "gear", "path": "/admin", "label": "Admin"},
]


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _check_auth() -> bool:
    return app.storage.user.get("authenticated", False)


def _sidebar(current_path: str = "/"):
    initials = app.storage.user.get("name", "U")[0].upper()
    name = app.storage.user.get("name", "Usuario")
    items_html = ""
    for item in NAV:
        if item.get("sep"):
            items_html += '<div class="s-sep"></div>'
            continue
        icon_svg = SIDEBAR_ICONS.get(item["icon"], "")
        active = "active" if item["path"] == current_path else ""
        items_html += (
            f'<a href="{item["path"]}" class="s-item {active}">'
            f'<span class="s-icon">{icon_svg}</span>'
            f'<span class="s-label">{item["label"]}</span>'
            f"</a>"
        )

    with ui.column().classes("h-full"):
        ui.html(
            f'<div class="mp-sidebar" style="padding-bottom:0">'
            f'<div class="s-brand"><div class="s-logo">MP</div>'
            f'<span class="s-brand-text">Master Prediction</span></div>'
            f'<div class="s-nav">{items_html}</div>'
            f"</div>"
        )
        with (
            ui.row()
            .classes("items-center w-full gap-2")
            .style("margin-top:auto;padding:12px 16px 16px")
        ):
            ui.html(f'<div class="s-avatar">{initials}</div>')
            ui.label(name).style("font-size:12px;color:var(--text-2);font-weight:500")
            ui.button(
                icon="logout",
                on_click=_logout,
            ).props('flat dense round size="sm" color="grey-6"').style("margin-left:auto")


def _logout():
    app.storage.user.clear()
    ui.navigate.to("/login")


def _page_shell(path: str):
    """Common page wrapper: CSS, auth check, sidebar."""
    ui.add_css(CSS)
    if not _check_auth():
        ui.navigate.to("/login")
        return False
    with (
        ui.left_drawer(value=True, fixed=True)
        .classes("p-0")
        .style(
            "width: 220px; min-width: 220px; background: var(--surface); "
            "border-right: 1px solid var(--edge)"
        )
    ):
        _sidebar(path)

    if app.storage.user.get("must_change_password"):
        _show_password_change_dialog()

    return True


def _show_password_change_dialog():
    """Modal dialog forcing user to change their temporary password."""
    dialog = ui.dialog().props("persistent")
    with dialog, ui.card().classes("w-80"):
        ui.label("Cambiar contrasena").classes("text-lg font-bold")
        ui.label("Debes cambiar tu contrasena temporal antes de continuar.").style(
            "font-size:12px;color:var(--text-3);margin-bottom:12px"
        )
        new_pw = (
            ui.input("Nueva contrasena", password=True, password_toggle_button=True)
            .props('outlined dense dark color="orange-8"')
            .classes("w-full mb-2")
        )
        confirm_pw = (
            ui.input("Confirmar contrasena", password=True, password_toggle_button=True)
            .props('outlined dense dark color="orange-8"')
            .classes("w-full mb-2")
        )
        err = ui.label("").classes("text-red-400 text-xs")
        err.set_visibility(False)

        def save_password():
            if len(new_pw.value) < 6:
                err.text = "Minimo 6 caracteres"
                err.set_visibility(True)
                return
            if new_pw.value != confirm_pw.value:
                err.text = "Las contrasenas no coinciden"
                err.set_visibility(True)
                return
            try:
                from webapp.data import get_supabase_client

                hashed = bcrypt.hashpw(new_pw.value.encode(), bcrypt.gensalt()).decode()
                client = get_supabase_client()
                client.table("app_users").update(
                    {
                        "password_hash": hashed,
                        "must_change_password": False,
                    }
                ).eq("username", app.storage.user["username"]).execute()
                del app.storage.user["must_change_password"]
                dialog.close()
                ui.notify("Contrasena actualizada", type="positive")
            except Exception as e:
                err.text = f"Error: {e}"
                err.set_visibility(True)

        ui.button("Guardar", on_click=save_password).props('unelevated color="orange-8"').classes(
            "w-full"
        )
    dialog.open()


@ui.page("/login")
def login_page():
    ui.add_css(CSS)
    if _check_auth():
        ui.navigate.to("/")
        return

    with ui.element("div").classes("login-wrap"):
        with ui.element("div").classes("login-box"):
            ui.html(
                '<div class="login-header">'
                '<div class="login-icon">MP</div>'
                "<h1>Master <span>Prediction</span></h1>"
                "<p>Ingresa tus credenciales para acceder</p>"
                "</div>"
            )

            with ui.element("div").classes("login-form"):
                username = (
                    ui.input("Usuario")
                    .props('outlined dense dark color="orange-8"')
                    .classes("w-full mb-3")
                )
                password = (
                    ui.input("Contrasena", password=True, password_toggle_button=True)
                    .props('outlined dense dark color="orange-8"')
                    .classes("w-full mb-4")
                )
                error_label = ui.label("").classes("text-red-400 text-xs mb-2")
                error_label.set_visibility(False)

                def do_login():
                    u = username.value.strip()
                    p = password.value
                    if not u or not p:
                        error_label.text = "Ingresa usuario y contrasena"
                        error_label.set_visibility(True)
                        return

                    user_data = USERS.get(u)
                    if user_data:
                        if not _verify_password(p, user_data["password_hash"]):
                            error_label.text = "Usuario o contrasena incorrectos"
                            error_label.set_visibility(True)
                            return
                        app.storage.user["authenticated"] = True
                        app.storage.user["username"] = u
                        app.storage.user["name"] = user_data["name"]
                        app.storage.user["role"] = user_data["role"]
                        ui.navigate.to("/")
                        return

                    try:
                        from webapp.data import get_supabase_client

                        client = get_supabase_client()
                        resp = client.table("app_users").select("*").eq("username", u).execute()
                        if not resp.data:
                            error_label.text = "Usuario o contrasena incorrectos"
                            error_label.set_visibility(True)
                            return
                        db_user = resp.data[0]
                        if not db_user.get("is_active", False):
                            error_label.text = "Cuenta desactivada. Contacta al administrador."
                            error_label.set_visibility(True)
                            return
                        if not _verify_password(p, db_user["password_hash"]):
                            error_label.text = "Usuario o contrasena incorrectos"
                            error_label.set_visibility(True)
                            return
                        app.storage.user["authenticated"] = True
                        app.storage.user["username"] = u
                        app.storage.user["name"] = db_user.get("name", u)
                        app.storage.user["role"] = db_user.get("role", "viewer")
                        if db_user.get("must_change_password"):
                            app.storage.user["must_change_password"] = True
                        ui.navigate.to("/")
                    except Exception:
                        error_label.text = "Error de conexion. Intenta de nuevo."
                        error_label.set_visibility(True)

                ui.button("Iniciar sesion", on_click=do_login).classes("w-full").props("unelevated")
                password.on("keydown.enter", do_login)

            ui.html(
                '<div class="login-stats">'
                '<div class="login-stat"><div class="val">12.4k</div><div class="lbl">Partidos analizados</div></div>'
                '<div class="login-stat"><div class="val">68%</div><div class="lbl">Acierto alta conf.</div></div>'
                '<div class="login-stat"><div class="val">6</div><div class="lbl">Ligas cubiertas</div></div>'
                "</div>"
            )


@ui.page("/")
def home_page():
    if not _page_shell("/"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.home import render

        render()
        render_footer()


@ui.page("/mundial")
def mundial_page():
    if not _page_shell("/mundial"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.mundial import render

        render()
        render_footer()


@ui.page("/predicciones")
def predicciones_page():
    if not _page_shell("/predicciones"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.predicciones import render

        render()
        render_footer()


@ui.page("/liga")
def liga_page():
    if not _page_shell("/liga"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.liga import render

        render()
        render_footer()


@ui.page("/equipo")
def equipo_page():
    if not _page_shell("/equipo"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.equipo import render

        render()
        render_footer()


@ui.page("/comparador")
def comparador_page():
    if not _page_shell("/comparador"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.comparador import render

        render()
        render_footer()


@ui.page("/asesor")
def asesor_page():
    if not _page_shell("/asesor"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.asesor import render

        render()
        render_footer()


@ui.page("/calibracion")
def calibracion_page():
    if not _page_shell("/calibracion"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.calibracion import render

        render()
        render_footer()


@ui.page("/tendencias")
def tendencias_page():
    if not _page_shell("/tendencias"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.tendencias import render

        render()
        render_footer()


@ui.page("/admin")
def admin_page():
    if not _page_shell("/admin"):
        return
    with ui.column().classes("w-full px-6 pb-8").style("max-width: 1200px; margin: 0 auto"):
        from webapp.pages.admin import render

        render()
        render_footer()


app.add_static_files("/static", str(Path(__file__).parent / "static"))

app.include_router(chat_router)
app.include_router(perf_router)

ui.run(
    title="Master Prediction",
    favicon="⚽",
    port=int(os.environ.get("PORT", 8080)),
    dark=True,
    storage_secret=os.environ.get("SUPABASE_KEY", "master-prediction-secret-key"),
    show=False,
    reload=False,
)
