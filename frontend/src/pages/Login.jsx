import { useState } from 'react'

export default function Login({ onLogin }) {
    const [mode, setMode] = useState('login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [nombre, setNombre] = useState('')
    const [message, setMessage] = useState(null)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)

    const API = 'https://malaquias.onrender.com'

    async function handleSubmit() {
        setLoading(true)
        setError(null)
        setMessage(null)

        try {
            if (mode === 'register') {
                const res = await fetch(`${API}/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password, nombre })
                })
                const data = await res.json()
                if (!res.ok) throw new Error(data.detail)
                setMessage(data.message)

            } else {
                const form = new URLSearchParams()
                form.append('username', email)
                form.append('password', password)

                const res = await fetch(`${API}/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: form
                })
                const data = await res.json()
                if (!res.ok) throw new Error(data.detail)

                localStorage.setItem('token', data.access_token)
                localStorage.setItem('nombre', data.nombre)
                onLogin(data.nombre)
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="login-wrap">
            <div className="login-card">
                <h1 className="login-title">Malaquías</h1>
                <p className="login-sub">Screening de CVs con IA</p>

                <div className="switcher" style={{ marginBottom: '1.5rem' }}>
                    {['login', 'register'].map(m => (
                        <button
                            key={m}
                            className={`switcher-btn ${mode === m ? 'active' : ''}`}
                            onClick={() => setMode(m)}
                            type="button"
                        >
                            {m === 'login' ? 'Iniciar sesión' : 'Registrarse'}
                        </button>
                    ))}
                    <div className="switcher-thumb" style={{
                        transform: `translateX(${mode === 'login' ? '0%' : '100%'})`
                    }} />
                </div>

                {mode === 'register' && (
                    <div className="field">
                        <label>Nombre</label>
                        <input
                            type="text"
                            value={nombre}
                            onChange={e => setNombre(e.target.value)}
                            placeholder="Tu nombre"
                        />
                    </div>
                )}

                <div className="field">
                    <label>Email</label>
                    <input
                        type="email"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        placeholder="tu@email.com"
                    />
                </div>

                <div className="field">
                    <label>Contraseña</label>
                    <input
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        placeholder="••••••••"
                        onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                    />
                </div>

                {error && <p className="login-error">{error}</p>}
                {message && <p className="login-success">{message}</p>}

                <button
                    className="btn-analyze"
                    onClick={handleSubmit}
                    disabled={loading}
                    style={{ marginTop: '1rem' }}
                >
                    {loading ? 'Cargando...' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
                </button>
            </div>
        </div>
    )
}