"""Gemini AI integration for the advisor with rate limiting."""

import logging
import os
import re
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

MAX_PER_HOUR = 20
MAX_PER_DAY = 100

_usage: dict[str, list[float]] = defaultdict(list)

SYSTEM_PROMPT = (
    "Eres el asesor deportivo de Master Prediction, plataforma de inteligencia deportiva.\n\n"
    "Reglas estrictas:\n"
    "- Responde en español, máximo 150 palabras\n"
    "- Usa SOLO los datos proporcionados, nunca inventes estadísticas ni resultados\n"
    "- Incluye probabilidades y nivel de confianza cuando estén disponibles\n"
    "- Análisis deportivo objetivo, no fomentes apuestas irresponsables\n"
    "- Usa **negritas** y • listas para organizar\n"
    "- Si no hay datos suficientes, dilo claramente\n"
    "- No respondas preguntas fuera del ámbito deportivo/predicciones\n"
    "- Ligas cubiertas: Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League"
)


def check_rate_limit(user_id: str) -> bool:
    now = time.time()
    _usage[user_id] = [t for t in _usage[user_id] if now - t < 86400]
    hour = sum(1 for t in _usage[user_id] if now - t < 3600)
    return hour < MAX_PER_HOUR and len(_usage[user_id]) < MAX_PER_DAY


def get_remaining(user_id: str) -> dict:
    now = time.time()
    _usage[user_id] = [t for t in _usage[user_id] if now - t < 86400]
    hour = sum(1 for t in _usage[user_id] if now - t < 3600)
    return {"hour": MAX_PER_HOUR - hour, "day": MAX_PER_DAY - len(_usage[user_id])}


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html).strip()


def _md_to_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return text


def enhance_response(
    user_message: str,
    data_context: str,
    history: list[dict] | None = None,
    user_id: str = "default",
) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — AI enhancement disabled")
        return None
    if not check_rate_limit(user_id):
        logger.info("Rate limit hit for user %s", user_id)
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        clean_data = _strip_html(data_context)
        prompt = (
            f"--- DATOS DEL SISTEMA ---\n{clean_data}\n\n"
            f"--- MENSAJE DEL USUARIO ---\n{user_message}"
        )

        contents = []
        if history:
            for msg in history[-6:]:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=_strip_html(msg["content"]))],
                    )
                )
        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=400,
                temperature=0.7,
            ),
        )

        _usage[user_id].append(time.time())
        return _md_to_html(response.text) if response.text else None

    except Exception as e:
        logger.warning("Gemini failed: %s", e)
        return None
