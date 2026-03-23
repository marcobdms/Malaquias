import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")
FROM_EMAIL = "Malaquías <onboarding@resend.dev>"

def send_confirmation_email(to_email: str, nombre: str, token: str):
    confirm_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/confirm?token={token}"
    
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": to_email,
        "subject": "Confirma tu cuenta en Malaquías",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 2rem;">
            <h2 style="font-size: 20px; font-weight: 600;">Hola {nombre}</h2>
            <p style="color: #666; margin: 1rem 0;">Confirma tu cuenta haciendo clic en el botón:</p>
            <a href="{confirm_url}" 
               style="display: inline-block; padding: 10px 24px; background: #1a1a1a; 
                      color: #fff; text-decoration: none; border-radius: 8px; font-size: 14px;">
                Confirmar cuenta
            </a>
            <p style="color: #999; font-size: 12px; margin-top: 2rem;">
                Si no creaste esta cuenta puedes ignorar este email.
            </p>
        </div>
        """
    })