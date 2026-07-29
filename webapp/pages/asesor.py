"""Asesor Virtual — chat interface for prediction queries."""

from nicegui import app, ui

from webapp.data import get_supabase_client
from webapp.theme import render_mini_strip

WELCOME = (
    "Hola! Soy tu asesor de predicciones. Puedo ayudarte con:\n\n"
    "- **Consultar un partido** — _Argentina vs Algeria_\n"
    "- **Proximos partidos** — _Francia_ o _partidos de hoy_\n"
    "- **Mejores picks** — _mejores predicciones_\n"
    "- **Track record** — _racha del modelo_"
)


def _load_known_teams() -> list[str]:
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
        return sorted(teams)
    except Exception:
        return []


def render():
    render_mini_strip("Asesor Virtual", "IA conversacional", "chat")

    if "advisor_messages" not in app.storage.user:
        app.storage.user["advisor_messages"] = [{"role": "assistant", "content": WELCOME}]
    if "advisor_context" not in app.storage.user:
        app.storage.user["advisor_context"] = {}

    messages = app.storage.user["advisor_messages"]

    chat_log = (
        ui.column()
        .classes("w-full")
        .style("max-height:500px;overflow-y:auto;gap:12px;margin-bottom:16px")
    )

    def _render_messages():
        chat_log.clear()
        with chat_log:
            for msg in messages:
                role = msg["role"]
                is_bot = role == "assistant"
                align = "items-start" if is_bot else "items-end"
                bg = "var(--surface)" if is_bot else "var(--flame-dim)"
                border = "var(--edge)" if is_bot else "var(--flame)"
                with ui.row().classes(f"w-full {align}"):
                    ui.html(
                        f'<div style="background:{bg};border:1px solid {border};'
                        f"border-radius:var(--radius);padding:10px 14px;max-width:80%;"
                        f'font-size:13px;line-height:1.5">'
                        f"{msg['content']}</div>"
                    )

    _render_messages()

    with ui.row().classes("w-full items-center gap-2"):
        text_input = (
            ui.input(placeholder="Ej: Argentina vs Algeria, mejores picks de hoy...")
            .props('outlined dense dark color="orange-8"')
            .classes("flex-grow")
        )

        send_btn = ui.button("Enviar").props('unelevated color="orange-8"').classes("h-10")

    async def send_message():
        prompt = text_input.value.strip()
        if not prompt:
            return
        text_input.value = ""

        messages.append({"role": "user", "content": prompt})
        _render_messages()

        try:
            import os

            import httpx

            api_url = os.environ.get("BACKEND_API_URL", "http://localhost:8081")
            api_key = os.environ.get("API_KEY_WEBAPP", "")
            known_teams = _load_known_teams()
            ctx = app.storage.user.get("advisor_context", {})
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.post(
                    f"{api_url}/api/chat",
                    json={"message": prompt, "known_teams": known_teams, "context": ctx},
                    headers={"X-API-Key": api_key},
                )
            resp.raise_for_status()
            data = resp.json()
            response = data["response"]
            app.storage.user["advisor_context"] = data.get("context", {})
        except Exception as e:
            response = f"Error al conectar con el servicio: {e}"

        messages.append({"role": "assistant", "content": response})
        app.storage.user["advisor_messages"] = messages
        _render_messages()

    send_btn.on_click(send_message)
    text_input.on("keydown.enter", send_message)
