import { useState, useEffect } from 'react'
import Results from './Results' // Re-usamos para mostrar detalle si quieres o solo una tabla

export default function TalentPool({ onNavigate }) {
    const [candidatos, setCandidatos] = useState([])
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [filterRec, setFilterRec] = useState('')
    const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    useEffect(() => {
        async function fetchPool() {
            try {
                const token = localStorage.getItem('token')
                const res = await fetch(`${API}/talent-pool`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                })
                if (res.ok) setCandidatos(await res.json())
            } catch (e) {
                console.error('Error fetching talent pool:', e)
            } finally {
                setLoading(false)
            }
        }
        fetchPool()
    }, [API])

    // Filtrado
    const filtered = candidatos.filter(c => {
        const matchesSearch = c.filename.toLowerCase().includes(searchTerm.toLowerCase()) || 
                              (c.fortalezas || []).some(f => f.toLowerCase().includes(searchTerm.toLowerCase())) ||
                              (c.oferta_descripcion || '').toLowerCase().includes(searchTerm.toLowerCase())
        const matchesRec = filterRec ? (c.recomendacion || '').toLowerCase().includes(filterRec) : true
        return matchesSearch && matchesRec
    })

    const getRecBadge = (rec) => {
        const r = (rec || '').toLowerCase()
        if (r.includes('entrevistar')) return <span className="bg-green-500/10 text-green-400 text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-md">Entrevistar</span>
        if (r.includes('considerar')) return <span className="bg-yellow-500/10 text-yellow-500 text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-md">Considerar</span>
        if (r.includes('descartar')) return <span className="bg-red-500/10 text-red-400 text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-md">Descartar</span>
        return <span className="text-zinc-500 text-xs">—</span>
    }

    return (
        <div className="p-4 md:p-8 max-w-5xl mx-auto w-full">
            <div className="mb-8">
                <h2 className="text-3xl font-black text-on-surface tracking-tight mb-2">Talent Pool Global</h2>
                <p className="text-on-surface-variant">Busca entre todos los perfiles analizados en tus posiciones pasadas.</p>
            </div>

            <div className="crystal-card !p-4 mb-6 flex flex-col sm:flex-row gap-4">
                <div className="flex-1 relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant text-[20px]">search</span>
                    <input 
                        type="text" 
                        placeholder="Buscar por nombre, skill clave, oferta..." 
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-surface-container-high border border-white/5 rounded-2xl py-3 pl-11 pr-4 text-sm text-on-surface focus:outline-none focus:border-primary transition-colors hover:bg-surface-container-highest"
                    />
                </div>
                <div className="sm:w-64">
                    <select 
                        value={filterRec}
                        onChange={(e) => setFilterRec(e.target.value)}
                        className="w-full appearance-none bg-surface-container-high border border-white/5 rounded-2xl px-5 py-3 text-on-surface text-sm focus:outline-none focus:border-primary cursor-pointer hover:bg-surface-container-highest transition-colors"
                    >
                        <option value="">Todas las recomendaciones</option>
                        <option value="entrevistar">Solo Entrevistar</option>
                        <option value="considerar">Solo Considerar</option>
                        <option value="descartar">Solo Descartar</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-32">
                    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
            ) : filtered.length === 0 ? (
                <div className="crystal-card text-center py-16">
                    <span className="material-symbols-outlined text-5xl text-on-surface-variant opacity-30 mb-3 block">group_off</span>
                    <p className="text-on-surface text-lg font-medium mb-1">Ningún candidato coincide</p>
                    <p className="text-sm text-on-surface-variant/70">Intenta buscar con otros términos o cambia el filtro de recomendación.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filtered.map(c => (
                        <div key={c.id} className="crystal-card hover:bg-surface-container transition-colors relative group">
                            <div className="flex items-start justify-between gap-4 mb-4">
                                <div>
                                    <h3 className="font-bold text-on-surface truncate pr-4 text-lg">{c.filename?.replace('.pdf', '')}</h3>
                                    <p className="text-xs text-on-surface-variant mt-0.5">
                                        Posición: <span className="font-medium text-primary/80">{c.oferta_categoria || 'General'}</span>
                                    </p>
                                </div>
                                <div className="text-right">
                                    <span className="text-xl font-black text-on-surface">{c.match_score?.toFixed(1)}/100</span>
                                    <div className="mt-1">{getRecBadge(c.recomendacion)}</div>
                                </div>
                            </div>
                            
                            {/* Tags de fortalezas principales */}
                            {c.fortalezas && c.fortalezas.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 mt-3 mb-4">
                                    {c.fortalezas.slice(0, 3).map((f, i) => (
                                        <span key={i} className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full whitespace-nowrap overflow-hidden text-ellipsis max-w-[120px]">
                                            {f}
                                        </span>
                                    ))}
                                    {c.fortalezas.length > 3 && (
                                        <span className="text-[10px] bg-white/5 text-on-surface-variant px-2 py-0.5 rounded-full">
                                            +{c.fortalezas.length - 3}
                                        </span>
                                    )}
                                </div>
                            )}

                            <div className="flex items-center justify-between mt-auto pt-4 border-t border-white/5">
                                <div className="flex gap-4">
                                    {c.email_candidato && c.email_candidato !== 'null' && (
                                        <a href={`mailto:${c.email_candidato}`} className="text-on-surface-variant hover:text-primary transition-colors" title="Enviar Email">
                                            <span className="material-symbols-outlined text-[18px]">mail</span>
                                        </a>
                                    )}
                                    {c.telefono_candidato && c.telefono_candidato !== 'null' && (
                                        <a href={`tel:${c.telefono_candidato}`} className="text-on-surface-variant hover:text-primary transition-colors" title="Llamar">
                                            <span className="material-symbols-outlined text-[18px]">call</span>
                                        </a>
                                    )}
                                </div>
                                <span className="text-[10px] text-on-surface-variant/50">
                                    {new Date(c.created_at).toLocaleDateString()}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
