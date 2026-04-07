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
        <div style="font-family: 'Inter', system-ui, sans-serif; max-width: 500px; margin: 0 auto; padding: 3rem 2rem; background-color: #0a0a0a; color: #e5e2e1; border-radius: 16px; border: 1px solid #2a2a2a;">
            <div style="margin-bottom: 2rem;">
                <span style="font-size: 10px; font-weight: 800; letter-spacing: 0.1em; color: #c6c6c6; text-transform: uppercase;">Malaquías Recruiting Suite</span>
                <h2 style="font-size: 28px; font-weight: 900; margin: 0.5rem 0 0 0; color: #ffffff; letter-spacing: -0.02em;">Acceso Concedido</h2>
            </div>
            
            <p style="font-size: 15px; line-height: 1.6; color: #c6c6c6; margin-bottom: 2rem;">
                Hola <strong>{nombre}</strong>,<br><br>
                Tu cuenta ha sido pre-aprobada para utilizar el motor de inteligencia artificial de Malaquías. Haz clic en el siguiente enlace para verificar tu correo electrónico y habilitar el acceso.
            </p>
            
            <a href="{confirm_url}" 
               style="display: inline-block; padding: 14px 28px; background: linear-gradient(145deg, #ffffff 0%, #d4d4d4 100%); 
                      color: #1a1c1c; text-decoration: none; border-radius: 9999px; font-weight: 700; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em;">
                Verificar y Entrar
            </a>
            
            <hr style="border: none; border-top: 1px solid #2a2a2a; margin: 3rem 0 1.5rem 0;">
            <p style="color: #474747; font-size: 12px; margin: 0; text-align: center;">
                Si no solicitaste acceso a Malaquías, puedes ignorar de forma segura este mensaje.<br>
                © Malaquías Engine AI
            </p>
        </div>
        """
    })