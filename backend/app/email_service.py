import os

import resend

from .config import load_environment


load_environment()

FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "Malaquias <onboarding@resend.dev>")


def email_confirmation_enabled() -> bool:
    return bool(os.getenv("RESEND_API_KEY", "").strip())


def send_confirmation_email(to_email: str, nombre: str, token: str) -> None:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        return

    resend.api_key = api_key
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5175").rstrip("/")
    confirm_url = f"{frontend_url}/confirm?token={token}"

    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": to_email,
        "subject": "Confirma tu cuenta en Malaquias",
        "html": f"""
        <div style="font-family: Inter, system-ui, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px; background-color: #0a0a0a; color: #e5e2e1; border-radius: 16px; border: 1px solid #2a2a2a;">
            <p style="font-size: 11px; font-weight: 800; letter-spacing: 0.12em; color: #c6c6c6; text-transform: uppercase; margin: 0 0 12px;">Malaquias Recruiting Suite</p>
            <h2 style="font-size: 28px; font-weight: 900; margin: 0 0 24px; color: #ffffff;">Confirma tu cuenta</h2>
            <p style="font-size: 15px; line-height: 1.6; color: #c6c6c6;">
                Hola <strong>{nombre}</strong>, confirma tu correo para activar el acceso a Malaquias.
            </p>
            <a href="{confirm_url}" style="display: inline-block; margin-top: 20px; padding: 14px 24px; background: #ffffff; color: #111111; text-decoration: none; border-radius: 9999px; font-weight: 700; font-size: 14px;">
                Verificar cuenta
            </a>
            <p style="color: #777777; font-size: 12px; margin-top: 28px;">
                Si no solicitaste esta cuenta, puedes ignorar este mensaje.
            </p>
        </div>
        """,
    })
