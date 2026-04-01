import { useState, useEffect } from 'react'

export default function Profile({ user, onProfileUpdate }) {
    const [nombre, setNombre] = useState(user || '')
    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState(null)
    const [error, setError] = useState(null)

    const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    async function handleSubmit(e) {
        e.preventDefault()
        setLoading(true)
        setMessage(null)
        setError(null)

        if (newPassword && !currentPassword) {
            setError('Ingresa tu contraseña actual para establecer una nueva')
            setLoading(false)
            return
        }

        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API}/profile`, {
                method: 'PUT',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    nombre,
                    current_password: currentPassword || null,
                    new_password: newPassword || null
                })
            })

            const data = await res.json()

            if (!res.ok) throw new Error(data.detail || 'Error al actualizar perfil')

            setMessage('Perfil actualizado exitosamente')
            localStorage.setItem('nombre', data.nombre)
            onProfileUpdate(data.nombre)
            setCurrentPassword('')
            setNewPassword('')

        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="p-4 md:p-8 max-w-2xl mx-auto w-full">
            <div className="mb-8">
                <h2 className="text-3xl font-black text-on-surface tracking-tight mb-2">Configuración</h2>
                <p className="text-on-surface-variant">Gestiona tu información personal y seguridad.</p>
            </div>

            <div className="crystal-card !p-6 md:!p-8 relative">
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">Nombre</label>
                        <input
                            type="text"
                            value={nombre}
                            onChange={(e) => setNombre(e.target.value)}
                            className="w-full bg-surface-container-high border border-white/5 rounded-2xl p-4 text-on-surface text-sm focus:outline-none focus:border-primary transition-colors hover:bg-surface-container-highest"
                        />
                    </div>

                    <div className="pt-6 mt-6 border-t border-white/5">
                        <p className="text-sm font-semibold text-on-surface mb-4">Cambiar Contraseña</p>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">Contraseña Actual</label>
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    className="w-full bg-surface-container-high border border-white/5 rounded-2xl p-4 text-on-surface text-sm focus:outline-none focus:border-primary transition-colors hover:bg-surface-container-highest"
                                />
                            </div>

                            <div>
                                <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">Nueva Contraseña</label>
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full bg-surface-container-high border border-white/5 rounded-2xl p-4 text-on-surface text-sm focus:outline-none focus:border-primary transition-colors hover:bg-surface-container-highest"
                                />
                            </div>
                        </div>
                    </div>

                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl animate-[fade-in_0.3s_ease]">
                            <p className="text-sm text-red-400 font-medium">{error}</p>
                        </div>
                    )}
                    
                    {message && (
                        <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-xl animate-[fade-in_0.3s_ease]">
                            <p className="text-sm text-green-400 font-medium">{message}</p>
                        </div>
                    )}

                    <div className="flex justify-end pt-4">
                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-primary flex items-center gap-2 disabled:opacity-50"
                        >
                            {loading ? (
                                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            ) : (
                                <span className="material-symbols-outlined text-[18px]">save</span>
                            )}
                            Guardar Cambios
                        </button>
                    </div>
                </form>

                {/* Zona de Peligro */}
                <div className="mt-12 pt-8 border-t border-red-500/10">
                    <h3 className="text-sm font-bold text-red-400 mb-2 flex items-center gap-2 uppercase tracking-widest">
                        <span className="material-symbols-outlined text-[18px]">warning</span>
                        Zona de Peligro
                    </h3>
                    <p className="text-xs text-on-surface-variant mb-6">Esta acción borrará permanentemente todos tus análisis, ofertas y candidatos. No se puede deshacer.</p>
                    
                    <button 
                        onClick={async () => {
                            if (!confirm('¿ESTÁS ABSOLUTAMENTE SEGURO? Se borrarán TODOS tus datos de análisis (ofertas y candidatos). Tu usuario permanecerá.')) return
                            setLoading(true)
                            try {
                                const token = localStorage.getItem('token')
                                const res = await fetch(`${API}/reset-data`, {
                                    method: 'DELETE',
                                    headers: { 'Authorization': `Bearer ${token}` }
                                })
                                if (res.ok) {
                                    alert('Todos tus datos han sido borrados. El dashboard ahora estará limpio.')
                                    window.location.reload()
                                }
                            } catch (e) {
                                console.error(e)
                            } finally {
                                setLoading(false)
                            }
                        }}
                        className="w-full sm:w-auto px-6 py-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl text-xs font-bold hover:bg-red-500/20 transition-all flex items-center justify-center gap-2"
                    >
                        <span className="material-symbols-outlined text-[18px]">delete_forever</span>
                        Reiniciar todos mis datos
                    </button>
                </div>
            </div>
        </div>
    )
}
