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
        if (loading || !email || !password || (mode === 'register' && !nombre)) return;

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
                setLoading(false)
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
                
                // Animación de éxito antes de navegar a dashboard
                setLoading('success')
                setTimeout(() => {
                    onLogin(data.nombre)
                }, 1500)
            }
        } catch (err) {
            setError(err.message)
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-background flex flex-col lg:flex-row">
            {/* PANEL IZQUIERDO */}
            <div className="hidden lg:flex flex-1 flex-col justify-between p-12 bg-surface-container-lowest border-r border-outline-variant/30 relative overflow-hidden">
                {/* Degradado subtil de fondo */}
                <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-white/5 to-transparent pointer-events-none" />
                
                <div className="relative z-10 max-w-xl self-center my-auto">
                    <span className="inline-block py-1 px-3 rounded-full border border-outline-variant text-[10px] font-bold text-on-surface-variant tracking-widest mb-8 uppercase bg-surface-container/50">
                        Malaquías Recruiting Suite
                    </span>
                    <h1 className="text-5xl 2xl:text-6xl font-black text-on-surface tracking-tight leading-[1.1] mb-6 text-balance">
                        Encuentra el talento ideal con <span className="text-on-surface-variant font-medium">precisión algorítmica.</span>
                    </h1>
                    <p className="text-lg text-on-surface-variant max-w-md leading-relaxed">
                        Optimiza tu proceso de selección utilizando nuestra inteligencia artificial avanzada diseñada para el reclutamiento moderno.
                    </p>
                </div>

                <div className="relative z-10 text-center">
                    <p className="text-xs text-on-surface-variant/50 tracking-widest uppercase mb-1">
                        © {new Date().getFullYear()} Malaquías Recruiting Suite <span className="mx-2">•</span> Diseñado para la Excelencia
                    </p>
                </div>
            </div>

            {/* PANEL DERECHO (LOGIN) */}
            <div className="flex-1 flex flex-col items-center justify-center p-6 relative overflow-hidden min-h-screen lg:min-h-0">
                {/* Gradiente radial de fondo sutil (glow effect) */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-white/5 blur-[120px] rounded-full pointer-events-none" />
                
                <div className="w-full max-w-md relative z-10">
                    <div className="text-center mb-10">
                        <h2 className="text-4xl font-black text-on-surface tracking-tight mb-2">Malaquías</h2>
                        <p className="text-on-surface-variant">Screening de CVs con IA</p>
                    </div>

                    <div className="crystal-glass">
                        <div className="switcher mb-8">
                            {['login', 'register'].map(m => (
                                <button
                                    key={m}
                                    className={`switcher-btn ${mode === m ? 'active' : ''}`}
                                    onClick={() => setMode(m)}
                                    type="button"
                                >
                                    {m === 'login' ? 'Iniciar sesión' : 'Crear cuenta'}
                                </button>
                            ))}
                            <div className="switcher-thumb w-1/2" style={{
                                transform: `translateX(${mode === 'login' ? '0%' : '100%'})`
                            }} />
                        </div>

                        <div className="space-y-4">
                            {mode === 'register' && (
                                <div>
                                    <label className="crystal-label uppercase text-[10px] font-bold tracking-widest">Nombre</label>
                                    <input
                                        type="text"
                                        className="crystal-input"
                                        value={nombre}
                                        onChange={e => setNombre(e.target.value)}
                                        placeholder="Tu nombre completo"
                                    />
                                </div>
                            )}

                            <div>
                                <label className="crystal-label uppercase text-[10px] font-bold tracking-widest">Correo Electrónico</label>
                                <input
                                    type="email"
                                    className="crystal-input"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    placeholder="nombre@empresa.com"
                                />
                            </div>

                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="crystal-label uppercase text-[10px] font-bold tracking-widest mb-0">Contraseña</label>
                                    {mode === 'login' && (
                                        <a href="#" className="text-xs text-on-surface-variant hover:text-on-surface transition-colors">¿Olvidaste tu contraseña?</a>
                                    )}
                                </div>
                                <input
                                    type="password"
                                    className="crystal-input"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl animate-[fade-in_0.3s_ease]">
                                <p className="text-sm text-red-400">{error}</p>
                            </div>
                        )}
                        {message && (
                            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-xl animate-[fade-in_0.3s_ease]">
                                <p className="text-sm text-green-400">{message}</p>
                            </div>
                        )}

                        <button
                            className="btn-primary mt-8 relative overflow-hidden transition-all duration-300"
                            onClick={handleSubmit}
                            disabled={!!loading || !email || !password || (mode === 'register' && !nombre)}
                        >
                            {loading === 'success' ? (
                                <span className="flex items-center justify-center gap-2 animate-[fade-in_0.3s_ease]">
                                    <span className="material-symbols-outlined text-[20px] text-green-700 font-bold scale-150 transition-transform">check_circle</span>
                                    ¡Acceso concedido!
                                </span>
                            ) : loading === true ? (
                                <span className="flex items-center justify-center gap-2">
                                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Procesando...
                                </span>
                            ) : (
                                mode === 'login' ? 'Entrar' : 'Registrarse'
                            )}
                        </button>
                    </div>

                    <div className="mt-8 text-center text-sm text-on-surface-variant">
                        {mode === 'login' ? '¿No tienes una cuenta? ' : '¿Ya tienes cuenta? '}
                        <button 
                            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
                            className="text-on-surface font-semibold hover:underline"
                        >
                            {mode === 'login' ? 'Solicita acceso' : 'Inicia sesión'}
                        </button>
                    </div>

                    {/* Footer features */}
                    <div className="mt-12 grid grid-cols-2 gap-4">
                        <div className="crystal-glass !p-4 !rounded-2xl flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center shrink-0">
                                <span className="material-symbols-outlined text-sm text-on-surface">shield</span>
                            </div>
                            <div className="text-left">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface">Seguridad</p>
                                <p className="text-[10px] text-on-surface-variant">Encriptación AES-256</p>
                            </div>
                        </div>
                        <div className="crystal-glass !p-4 !rounded-2xl flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center shrink-0">
                                <span className="material-symbols-outlined text-sm text-on-surface">support_agent</span>
                            </div>
                            <div className="text-left">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface">Soporte</p>
                                <p className="text-[10px] text-on-surface-variant">Asistencia 24/7</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}