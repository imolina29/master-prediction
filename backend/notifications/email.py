import logging
import os

logger = logging.getLogger(__name__)


def send_welcome_email(to_email: str, name: str, username: str, temp_password: str) -> bool:
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.info("RESEND_API_KEY not set, skipping email")
        return False

    from_email = os.environ.get("RESEND_FROM_EMAIL", "Master Prediction <onboarding@resend.dev>")
    dashboard_url = os.environ.get("DASHBOARD_URL", "")

    try:
        import resend

        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": from_email,
                "to": [to_email],
                "subject": "Bienvenido a Master Prediction - Tus credenciales de acceso",
                "html": _build_welcome_html(name, username, temp_password, dashboard_url),
            }
        )
        logger.info("Welcome email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def _build_welcome_html(name: str, username: str, temp_password: str, dashboard_url: str) -> str:
    dashboard_link = (
        f'<a href="{dashboard_url}" style="color: #4CAF50;">{dashboard_url}</a>'
        if dashboard_url
        else "el dashboard"
    )
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;
                background: #1a1a2e; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <span style="font-size: 2.5rem;">⚽</span>
            <h1 style="color: #4CAF50; margin: 0.5rem 0 0;">Master Prediction</h1>
        </div>

        <p>Hola <b>{name}</b>,</p>
        <p>Tu solicitud de acceso ha sido aprobada. Aqui estan tus credenciales:</p>

        <div style="background: #16213e; padding: 1rem 1.5rem; border-radius: 8px;
                    border-left: 3px solid #4CAF50; margin: 1rem 0;">
            <p style="margin: 0.3rem 0;"><b>Usuario:</b> <code>{username}</code></p>
            <p style="margin: 0.3rem 0;"><b>Contraseña:</b> <code>{temp_password}</code></p>
        </div>

        <p style="color: #FFD700; font-size: 0.9rem;">
            ⚠️ Deberas cambiar tu contraseña en el primer inicio de sesion.
        </p>

        <p>Accede al dashboard: {dashboard_link}</p>

        <hr style="border: none; border-top: 1px solid #333; margin: 1.5rem 0;">
        <p style="color: #888; font-size: 0.8rem; text-align: center;">
            Master Prediction · Inteligencia Deportiva con IA
        </p>
    </div>
    """
