import { useEffect, useState } from 'react'

export default function Confirm() {
    const [status, setStatus] = useState('loading')

    useEffect(() => {
        const token = new URLSearchParams(window.location.search).get('token')
        if (!token) { setStatus('error'); return }

        fetch(`https://malaquias.onrender.com/confirm?token=${token}`)
            .then(res => res.json())
            .then(data => setStatus(data.message ? 'ok' : 'error'))
            .catch(() => setStatus('error'))
    }, [])

    return (
        <div className="login-wrap">
            <div className="login-card">
                {status === 'loading' && <p className="login-sub">Confirmando cuenta...</p>}
                {status === 'ok' && <p className="login-success">Cuenta confirmada. Ya puedes iniciar sesión.</p>}
                {status === 'error' && <p className="login-error">Token inválido o expirado.</p>}
            </div>
        </div>
    )
}