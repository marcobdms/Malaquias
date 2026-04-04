import { useState, useEffect } from 'react'

export default function Dashboard({ onNavigate }) {
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(true)
    const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    useEffect(() => {
        async function fetchDashboard() {
            try {
                const token = localStorage.getItem('token')
                const res = await fetch(`${API}/dashboard`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                })
                if (res.ok) {
                    setData(await res.json())
                }
            } catch (e) {
                console.error('Error fetching dashboard:', e)
            } finally {
                setLoading(false)
            }
        }
        fetchDashboard()
    }, [])

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-[70dvh] w-full">
                <div className="w-12 h-12 border-2 border-white/10 border-t-white rounded-full animate-spin" />
                <p className="mt-4 text-zinc-500 text-[10px] font-bold uppercase tracking-widest leading-none">Cargando Dashboard</p>
            </div>
        )
    }

    if (!data) return null

    const total = data.distribucion.entrevistar + data.distribucion.considerar + data.distribucion.descartar
    const pctEntrevistar = total > 0 ? Math.round((data.distribucion.entrevistar / total) * 100) : 0
    const pctConsiderar = total > 0 ? Math.round((data.distribucion.considerar / total) * 100) : 0
    const pctDescartar = total > 0 ? Math.round((data.distribucion.descartar / total) * 100) : 0

    const getRecBadge = (rec) => {
        const r = (rec || '').toLowerCase()
        if (r.includes('entrevistar')) return <span className="text-green-400 text-xs font-bold">Entrevistar</span>
        if (r.includes('considerar')) return <span className="text-yellow-400 text-xs font-bold">Considerar</span>
        if (r.includes('descartar')) return <span className="text-red-400 text-xs font-bold">Descartar</span>
        return <span className="text-zinc-500 text-xs">—</span>
    }

    return (
        <div className="p-4 md:p-8 max-w-5xl mx-auto w-full">
            <div className="mb-8">
                <h2 className="text-3xl font-black text-on-surface tracking-tight mb-2">Dashboard</h2>
                <p className="text-on-surface-variant">Vista general de tu actividad de reclutamiento.</p>
            </div>

            {/* Metric Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <div className="crystal-card !p-5 !rounded-2xl group hover:scale-[1.02] transition-transform">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                            <span className="material-symbols-outlined text-primary text-[20px]">work</span>
                        </div>
                    </div>
                    <p className="text-2xl font-black text-on-surface">{data.total_ofertas}</p>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mt-1">Posiciones</p>
                </div>

                <div className="crystal-card !p-5 !rounded-2xl group hover:scale-[1.02] transition-transform">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-zinc-500/10 flex items-center justify-center">
                            <span className="material-symbols-outlined text-zinc-400 text-[20px]">group</span>
                        </div>
                    </div>
                    <p className="text-2xl font-black text-on-surface">{data.total_candidatos}</p>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mt-1">CVs Analizados</p>
                </div>

                <div className="crystal-card !p-5 !rounded-2xl group hover:scale-[1.02] transition-transform">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-yellow-500/10 flex items-center justify-center">
                            <span className="material-symbols-outlined text-yellow-500 text-[20px]">speed</span>
                        </div>
                    </div>
                    <p className="text-2xl font-black text-on-surface">{data.score_promedio}%</p>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mt-1">Score Promedio</p>
                </div>

                <div className="crystal-card !p-5 !rounded-2xl group hover:scale-[1.02] transition-transform cursor-pointer" onClick={() => onNavigate('screener')}>
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center">
                            <span className="material-symbols-outlined text-on-surface text-[20px]">add_circle</span>
                        </div>
                    </div>
                    <p className="text-sm font-bold text-on-surface">Nuevo Análisis</p>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mt-1">Iniciar screening</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Distribution Chart */}
                <div className="crystal-card !rounded-2xl">
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-6">Distribución de Recomendaciones</h3>
                    
                    {total === 0 ? (
                        <div className="text-center py-8 text-on-surface-variant">
                            <span className="material-symbols-outlined text-4xl opacity-30 mb-2 block">bar_chart</span>
                            <p className="text-sm">Aún no hay datos de análisis</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {/* Bar: Entrevistar */}
                            <div>
                                <div className="flex justify-between items-center mb-1.5">
                                    <span className="text-sm font-medium text-on-surface">Entrevistar</span>
                                    <span className="text-sm font-bold text-green-400">{data.distribucion.entrevistar} ({pctEntrevistar}%)</span>
                                </div>
                                <div className="h-2.5 bg-surface-container-high rounded-full overflow-hidden">
                                    <div className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full transition-all duration-700" style={{ width: `${pctEntrevistar}%` }} />
                                </div>
                            </div>

                            {/* Bar: Considerar */}
                            <div>
                                <div className="flex justify-between items-center mb-1.5">
                                    <span className="text-sm font-medium text-on-surface">Considerar</span>
                                    <span className="text-sm font-bold text-yellow-400">{data.distribucion.considerar} ({pctConsiderar}%)</span>
                                </div>
                                <div className="h-2.5 bg-surface-container-high rounded-full overflow-hidden">
                                    <div className="h-full bg-gradient-to-r from-yellow-500 to-yellow-400 rounded-full transition-all duration-700" style={{ width: `${pctConsiderar}%` }} />
                                </div>
                            </div>

                            {/* Bar: Descartar */}
                            <div>
                                <div className="flex justify-between items-center mb-1.5">
                                    <span className="text-sm font-medium text-on-surface">Descartar</span>
                                    <span className="text-sm font-bold text-red-400">{data.distribucion.descartar} ({pctDescartar}%)</span>
                                </div>
                                <div className="h-2.5 bg-surface-container-high rounded-full overflow-hidden">
                                    <div className="h-full bg-gradient-to-r from-red-500 to-red-400 rounded-full transition-all duration-700" style={{ width: `${pctDescartar}%` }} />
                                </div>
                            </div>
                        </div>
                    )}
                    {error && (
                        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl">
                            <p className="text-sm text-red-400 font-medium">{error}</p>
                        </div>
                    )}
                </div>

                {/* Recent Candidates */}
                <div className="crystal-card !rounded-2xl">
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-6">Últimos Candidatos</h3>
                    
                    {data.ultimos_candidatos.length === 0 ? (
                        <div className="text-center py-8 text-on-surface-variant">
                            <span className="material-symbols-outlined text-4xl opacity-30 mb-2 block">person_search</span>
                            <p className="text-sm">No hay candidatos analizados</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {data.ultimos_candidatos.map((c, i) => (
                                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-surface-container-lowest/50 border border-white/5 hover:bg-surface-container transition-colors">
                                    <div className="w-9 h-9 rounded-full bg-surface-container-high flex items-center justify-center text-xs font-bold text-on-surface shrink-0">
                                        {(c.filename || '??').replace('.pdf', '').substring(0, 2).toUpperCase()}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-on-surface truncate">{c.filename?.replace('.pdf', '')}</p>
                                        <div className="flex items-center gap-2 mt-0.5">
                                            {getRecBadge(c.recomendacion)}
                                        </div>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="text-sm font-bold text-on-surface">{c.match_score?.toFixed(1)}%</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
