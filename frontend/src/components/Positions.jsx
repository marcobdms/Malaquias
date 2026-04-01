import { useState, useEffect } from 'react'
import Results from './Results'

export default function Positions() {
    const [ofertas, setOfertas] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedOferta, setSelectedOferta] = useState(null)
    const [candidatos, setCandidatos] = useState(null)
    const [loadingCandidatos, setLoadingCandidatos] = useState(false)
    const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    useEffect(() => {
        fetchOfertas()
    }, [])

    async function fetchOfertas() {
        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API}/ofertas`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            if (res.ok) setOfertas(await res.json())
        } catch (e) {
            console.error('Error fetching ofertas:', e)
        } finally {
            setLoading(false)
        }
    }

    async function handleDelete(e, id) {
        e.stopPropagation()
        if (!confirm('¿Estás seguro de que deseas eliminar esta posición y todos sus candidatos analizados? Esta acción no se puede deshacer.')) return
        
        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API}/ofertas/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            })
            if (res.ok) {
                setOfertas(ofertas.filter(o => o.id !== id))
            } else {
                alert('No se pudo eliminar la posición')
            }
        } catch (e) {
            console.error('Error deleting:', e)
        }
    }

    async function viewCandidatos(oferta) {
        setSelectedOferta(oferta)
        setLoadingCandidatos(true)
        try {
            const token = localStorage.getItem('token')
            const res = await fetch(`${API}/ofertas/${oferta.id}/candidatos`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            if (res.ok) {
                const data = await res.json()
                setCandidatos(data.candidatos.map(c => ({
                    filename: c.filename,
                    match_score: c.match_score,
                    analysis: {
                        fortalezas: c.fortalezas,
                        carencias: c.carencias,
                        valoracion: c.valoracion,
                        recomendacion: c.recomendacion,
                        email_candidato: c.email_candidato,
                        telefono_candidato: c.telefono_candidato
                    }
                })))
            }
        } catch (e) {
            console.error('Error fetching candidatos:', e)
        } finally {
            setLoadingCandidatos(false)
        }
    }

    function formatDate(iso) {
        if (!iso) return ''
        const d = new Date(iso)
        return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
    }

    const getCategoryLabel = (cat) => {
        const map = {
            'desarrollo': 'Desarrollo',
            'diseño': 'Diseño UX/UI',
            'marketing': 'Marketing',
            'ventas': 'Ventas',
            'logistica': 'Logística',
            'rrhh': 'RRHH',
            'electromecanica': 'Electromecánica',
            'administracion': 'Administración'
        }
        return map[cat] || cat || 'General'
    }

    async function handleDownloadPDF() {
        if (!selectedOferta) return
        const token = localStorage.getItem('token')
        const url = `${API}/ofertas/${selectedOferta.id}/pdf`
        
        try {
            const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
            if (!res.ok) throw new Error('Error al generar PDF')
            const blob = await res.blob()
            const downloadUrl = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = downloadUrl
            a.download = `Reporte_${selectedOferta.categoria || 'Oferta'}.pdf`
            document.body.appendChild(a)
            a.click()
            a.remove()
        } catch (e) {
            console.error('Download error:', e)
            alert('Error descargando el PDF.')
        }
    }

    // Vista de candidatos de una oferta
    if (selectedOferta && candidatos) {
        return (
            <div className="p-4 md:p-8 max-w-5xl mx-auto w-full">
                <button 
                    onClick={() => { setSelectedOferta(null); setCandidatos(null) }}
                    className="flex items-center gap-2 text-on-surface-variant hover:text-on-surface transition-colors mb-6 text-sm font-medium"
                >
                    <span className="material-symbols-outlined text-[18px]">arrow_back</span>
                    Volver a posiciones
                </button>

                <div className="mb-6">
                    <div className="flex items-center gap-3 mb-2">
                        <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">
                            {getCategoryLabel(selectedOferta.categoria)}
                        </span>
                        <span className="text-xs text-on-surface-variant">{formatDate(selectedOferta.created_at)}</span>
                    </div>
                    <p className="text-sm text-on-surface-variant line-clamp-2">{selectedOferta.descripcion}</p>
                </div>

                {loadingCandidatos ? (
                    <div className="flex items-center justify-center h-32">
                        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    </div>
                )  : candidatos.length === 0 ? (
                    <div className="text-center py-12 text-on-surface-variant">
                        <span className="material-symbols-outlined text-5xl opacity-30 mb-3 block">person_off</span>
                        <p className="text-sm">No hay candidatos para esta posición</p>
                    </div>
                ) : (
                    <Results 
                        candidates={candidatos} 
                        onReset={() => { setSelectedOferta(null); setCandidatos(null) }}
                        ofertaId={selectedOferta.id}
                        onDownloadPDF={handleDownloadPDF}
                        isSavedView={true}
                    />
                )}
            </div>
        )
    }

    // Vista de lista de ofertas
    return (
        <div className="p-4 md:p-8 max-w-5xl mx-auto w-full">
            <div className="mb-8">
                <h2 className="text-3xl font-black text-on-surface tracking-tight mb-2">Análisis Guardados</h2>
                <p className="text-on-surface-variant">Historial de selecciones y sus candidatos analizados.</p>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-32">
                    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
            ) : ofertas.length === 0 ? (
                <div className="crystal-card text-center py-12">
                    <span className="material-symbols-outlined text-5xl text-on-surface-variant opacity-30 mb-3 block">work_off</span>
                    <p className="text-on-surface-variant mb-1">No tienes posiciones creadas</p>
                    <p className="text-sm text-on-surface-variant/70">Analiza CVs para crear tu primera posición</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {ofertas.map((o, i) => (
                        <div 
                            key={i} 
                            onClick={() => viewCandidatos(o)}
                            className="crystal-card !p-5 !rounded-2xl cursor-pointer hover:bg-surface-container transition-all hover:scale-[1.005] group"
                        >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex flex-wrap items-center gap-2 mb-2">
                                        <span className="bg-primary/10 text-primary px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest">
                                            {getCategoryLabel(o.categoria)}
                                        </span>
                                        {o.stack && (
                                            <span className="bg-surface-container-high text-on-surface-variant px-2.5 py-0.5 rounded-full text-[10px] font-medium">
                                                {o.stack}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-on-surface line-clamp-2 leading-relaxed">{o.descripcion}</p>
                                </div>

                                <div className="flex items-center gap-4 sm:gap-6 shrink-0">
                                    <div className="text-center">
                                        <p className="text-xl font-black text-on-surface">{o.total_candidatos}</p>
                                        <p className="text-[9px] font-bold uppercase tracking-widest text-on-surface-variant">Candidatos</p>
                                    </div>
                                    <div className="text-right hidden sm:block">
                                        <p className="text-xs text-on-surface-variant">{formatDate(o.created_at)}</p>
                                    </div>
                                    <button 
                                        className="w-8 h-8 flex items-center justify-center rounded-full text-zinc-500 hover:bg-red-500/10 hover:text-red-400 transition-colors"
                                        onClick={(e) => handleDelete(e, o.id)}
                                        title="Eliminar posición"
                                    >
                                        <span className="material-symbols-outlined text-[18px]">delete</span>
                                    </button>
                                    <span className="material-symbols-outlined text-on-surface-variant group-hover:text-on-surface transition-colors ml-2">
                                        chevron_right
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
