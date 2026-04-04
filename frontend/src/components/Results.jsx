import { useState } from 'react'

export default function Results({ candidates, onReset, ofertaId, onDownloadPDF, isSavedView, onNavigate }) {
    const [expanded, setExpanded] = useState({ 0: true })
    const [contactoVisible, setContactoVisible] = useState({})
    const [showAll, setShowAll] = useState(false)
    const [saved, setSaved] = useState(false)
    const [discardPopup, setDiscardPopup] = useState(false)

    const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

    function toggleExpand(i) {
        setExpanded(prev => ({ ...prev, [i]: !prev[i] }))
    }

    function toggleContacto(e, i) {
        e.stopPropagation() // Para no disparar el toggleExpand
        setContactoVisible(prev => ({ ...prev, [i]: !prev[i] }))
    }

    function getInitials(name) {
        if (!name) return '??'
        const cleanName = name.replace('.pdf', '')
        return cleanName.substring(0, 2).toUpperCase()
    }

    const truncate = (text) => {
        if (!text) return '';
        return text.length > 80 ? text.substring(0, 60) + '...' : text;
    }

    async function handleDiscard() {
        if (ofertaId && !saved && !isSavedView) {
            try {
                const token = localStorage.getItem('token')
                await fetch(`${API}/ofertas/${ofertaId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${token}` }
                })
            } catch(e) {
                console.error(e)
            }
        }
        setDiscardPopup(false)
        onReset()
    }

    function handleNewSearchClick() {
        if (!isSavedView && !saved) {
            setDiscardPopup(true)
        } else {
            onReset()
        }
    }

    function handleSave() {
        setSaved(true)
        alert('Análisis guardado. Búscalo en "Análisis Guardados" del menú principal.')
    }

    const getRecommendationBadge = (rec) => {
        const r = rec?.toLowerCase() || '';
        if (r.includes('entrevistar')) {
            return <span className="bg-white/10 border border-white/10 text-white px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">Entrevistar</span>;
        }
        if (r.includes('considerar')) {
            return <span className="bg-surface-container-highest border border-white/5 text-zinc-400 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">Considerar</span>;
        }
        if (r.includes('descartar')) {
            return <span className="bg-red-500/10 border border-red-500/20 text-red-400 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">Descartar</span>;
        }
        return null;
    }

    const visibleCandidates = showAll ? candidates : candidates.slice(0, 4)

    return (
        <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-4">
                <div>
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1 flex items-center gap-2">
                        Análisis Activo
                        <span className="text-on-surface font-bold">{candidates.length} Analizados</span>
                    </h3>
                    <p className="text-3xl font-black text-on-surface tracking-tight leading-tight">
                        Candidato<br className="hidden sm:block" /> Intelligence
                    </p>
                </div>
                <div className="flex flex-col sm:flex-row items-center gap-3">
                    {!isSavedView && (
                        <button 
                            onClick={handleNewSearchClick}
                            className="btn-outline h-10 px-4 w-full sm:w-auto flex items-center justify-center gap-2 text-sm text-on-surface-variant hover:text-on-surface whitespace-nowrap"
                        >
                            <span className="material-symbols-outlined text-[18px]">refresh</span>
                            Nueva búsqueda
                        </button>
                    )}
                    
                    {isSavedView ? (
                        <button 
                            onClick={onDownloadPDF}
                            className="bg-white text-black h-10 px-6 rounded-full font-bold text-sm shadow-crystal hover:scale-[1.02] active:scale-95 transition-transform flex items-center justify-center gap-2 whitespace-nowrap"
                        >
                            <span className="material-symbols-outlined text-[18px]">picture_as_pdf</span>
                            Descargar informe
                        </button>
                    ) : (
                        <button 
                            onClick={handleSave}
                            disabled={saved}
                            className={`${saved ? 'bg-zinc-800 text-zinc-400' : 'bg-white text-black hover:scale-[1.02] active:scale-95 shadow-crystal'} h-10 px-4 w-full sm:w-auto rounded-full font-bold text-sm transition-transform flex items-center justify-center gap-2 whitespace-nowrap`}
                        >
                            <span className="material-symbols-outlined text-[18px]">{saved ? 'check' : 'bookmark'}</span>
                            {saved ? 'Guardado' : 'Guardar análisis'}
                        </button>
                    )}
                </div>
            </div>
            
            <p className="text-sm text-on-surface-variant mb-4 lg:hidden">
                Hemos procesado los perfiles disponibles para encontrar el ajuste perfecto con tu cultura y requisitos técnicos.
            </p>

            {visibleCandidates.map((c, i) => {
                const a = c.analysis || {}
                const isExpanded = !!expanded[i]
                const isTop = i === 0
                const tieneContacto = a.email_candidato || a.telefono_candidato
                const score = c.match_score.toFixed(1)

                return (
                    <div 
                        key={i} 
                        className={`crystal-card overflow-hidden transition-all duration-300 ${isTop ? 'bg-surface-container border-t border-white/10 shadow-[0_10px_40px_rgba(0,0,0,0.5)]' : 'bg-surface border-transparent hover:bg-surface-container-lowest cursor-pointer'} border relative`}
                        onClick={() => !isTop && toggleExpand(i)}
                    >
                        {/* Cabecera de la Tarjeta (Siempre visible) */}
                        <div className="flex items-start justify-between gap-4 relative z-10">
                            <div className="flex items-start gap-4 min-w-0 flex-1">
                                {/* Avatar & Badge Placed Together */}
                                <div className="flex flex-col items-center gap-2 relative mt-1 shrink-0">
                                    <div className={`w-14 h-14 rounded-full flex items-center justify-center text-lg font-black shadow-crystal border ${isTop ? 'bg-surface-container-high text-white border-white/20' : 'bg-surface-container text-on-surface border-white/5'}`}>
                                        {getInitials(a.nombre_candidato || c.filename)}
                                    </div>
                                    {isTop && (
                                        <div className="absolute -bottom-3 top-[44px] left-1/2 -translate-x-1/2 bg-background rounded-full p-1 z-20">
                                            <div className="w-5 h-5 bg-white rounded-full flex items-center justify-center">
                                                <span className="material-symbols-outlined text-[12px] text-black font-black">star</span>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="min-w-0 flex-1">
                                    {isTop && (
                                        <span className="text-white bg-white/10 border border-white/10 px-2 py-0.5 rounded-full text-[9px] font-black tracking-widest uppercase mb-2 inline-block">
                                            Mejor Candidato
                                        </span>
                                    )}
                                    <h4 className="text-xl md:text-2xl font-bold text-white tracking-tight leading-tight mb-1 truncate pr-2">
                                        {a.nombre_candidato || c.filename.replace('.pdf', '')}
                                    </h4>
                                    <p className="text-sm text-zinc-400 font-medium truncate">
                                        {a.titulo_candidato || 'Perfil Analizado'}
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center gap-3 shrink-0">
                                <div className={`flex items-center justify-center w-[54px] h-[54px] rounded-full border-2 ${isTop ? 'border-white/60 bg-white/5' : 'border-white/10 bg-surface-container-high'} shrink-0 shadow-crystal`}>
                                    <p className="text-[13px] font-black tracking-tighter text-white">{score}%</p>
                                </div>

                                {!isTop && (
                                    <button 
                                        className="sm:hidden w-10 h-10 flex items-center justify-center rounded-xl bg-surface-container border border-white/5"
                                        onClick={(e) => { e.stopPropagation(); toggleExpand(i); }}
                                    >
                                        <span className={`material-symbols-outlined text-[20px] transition-transform ${isExpanded ? 'rotate-180' : ''}`}>expand_more</span>
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Error Handling si existe en el análisis */}
                        {a.error && isExpanded && (
                            <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl relative z-10">
                                <p className="text-sm text-red-400">Error en análisis: {a.error}</p>
                            </div>
                        )}

                        {/* Contenido Expandido */}
                        {!a.error && isExpanded && (
                            <div className={`mt-6 pt-6 border-t border-outline-variant/30 transition-all duration-500 origin-top relative z-10`}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
                                    {/* Fortalezas y Carencias stacked */}
                                    <div className="space-y-6">
                                        <div>
                                            <h5 className="text-[10px] font-bold uppercase tracking-widest text-[#c6c6c6] mb-3 flex items-center gap-2">
                                                Fortalezas
                                            </h5>
                                            <div className="flex flex-wrap gap-2">
                                                {(a.fortalezas || []).map((f, j) => (
                                                    <span key={j} className="flex items-center gap-2 text-xs text-on-surface bg-surface-container border border-white/5 rounded-full px-3 py-1.5 shadow-sm hover:border-white/20 transition-colors">
                                                        <span className="material-symbols-outlined text-[14px] text-green-500">check_circle</span>
                                                        {truncate(f)}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>

                                        <div>
                                            <h5 className="text-[10px] font-bold uppercase tracking-widest text-[#c6c6c6] mb-3 flex items-center gap-2">
                                                Carencias
                                            </h5>
                                            <div className="flex flex-wrap gap-2">
                                                {(a.carencias || []).map((car, j) => (
                                                    <span key={j} className="flex items-center gap-2 text-xs text-on-surface-variant bg-surface-container border border-white/5 rounded-full px-3 py-1.5 shadow-sm hover:border-white/20 transition-colors">
                                                        <span className="material-symbols-outlined text-[14px] text-red-500">info</span>
                                                        {truncate(car)}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {/* Panel Derecho de Expanded: Valoración AI  & Contact */}
                                    <div className="flex flex-col justify-between">
                                        {a.valoracion && (
                                            <div className="bg-[#1a1a1a] rounded-2xl p-5 border border-white/5 relative overflow-hidden group h-full flex flex-col">
                                                <h5 className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">
                                                    <span className="material-symbols-outlined text-[16px] text-on-surface-variant">auto_awesome</span>
                                                    Resumen de Malaquías AI
                                                </h5>
                                                <p className="text-sm leading-relaxed text-[#c6c6c6] italic relative z-10 flex-1">
                                                    "{a.valoracion}"
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Botones Acciones al final */}
                                <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
                                    {tieneContacto ? (
                                        <>
                                            <button 
                                                className="btn-primary h-12 rounded-full font-bold text-sm hover:scale-[1.02] active:scale-[0.98] transition-all flex-[2] w-full"
                                                onClick={(e) => toggleContacto(e, i)}
                                            >
                                                {contactoVisible[i] ? 'Ocultar Contacto' : 'Contactar'}
                                            </button>
                                            <div className="flex-1 flex justify-center sm:justify-end">
                                                {getRecommendationBadge(a.recomendacion || (score > 70 ? 'Entrevistar' : score > 40 ? 'Considerar' : 'Descartar'))}
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <button className="btn-primary h-12 rounded-full font-bold text-sm hover:scale-[1.02] active:scale-[0.98] transition-all flex-[2] w-full">
                                                Guardar
                                            </button>
                                            <div className="flex-1 flex justify-center sm:justify-end">
                                                {getRecommendationBadge(a.recomendacion || (score > 70 ? 'Entrevistar' : score > 40 ? 'Considerar' : 'Descartar'))}
                                            </div>
                                        </>
                                    )}
                                </div>

                                {/* Datos de Contacto (Dropdown suave) */}
                                {contactoVisible[i] && tieneContacto && (
                                    <div className="mt-3 p-4 rounded-xl bg-surface-container-low border border-white/10 flex flex-wrap gap-6 items-center flex-col sm:flex-row animate-[fade-in_0.2s_ease-out]">
                                        {a.email_candidato && a.email_candidato !== 'null' && (
                                            <div className="flex items-center justify-center gap-2 text-sm text-on-surface w-full sm:w-auto">
                                                <span className="material-symbols-outlined text-[18px] text-on-surface-variant">mail</span>
                                                <a href={`mailto:${a.email_candidato}`} className="hover:underline font-medium">{a.email_candidato}</a>
                                            </div>
                                        )}
                                        {a.telefono_candidato && a.telefono_candidato !== 'null' && (
                                            <div className="flex items-center justify-center gap-2 text-sm text-on-surface w-full sm:w-auto">
                                                <span className="material-symbols-outlined text-[18px] text-on-surface-variant">call</span>
                                                <a href={`tel:${a.telefono_candidato}`} className="hover:underline font-medium">{a.telefono_candidato}</a>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                        
                        {/* Soft Glow Background para Top Candidato */}
                        {isTop && (
                            <div className="absolute top-[-50px] left-[-50px] w-[200px] h-[200px] bg-white/5 blur-[60px] pointer-events-none z-0 rounded-full" />
                        )}
                    </div>
                )
            })}

            {!showAll && candidates.length > 4 && (
                <div className="flex justify-center mt-4 border-t border-white/5 pt-4">
                    <button 
                        onClick={() => setShowAll(true)}
                        className="flex flex-col items-center justify-center gap-1 text-on-surface-variant hover:text-white transition-colors pb-4"
                    >
                        <span className="text-sm font-semibold">Mostrar más ({candidates.length - 4})</span>
                        <span className="material-symbols-outlined">expand_more</span>
                    </button>
                </div>
            )}

            {/* Pop up de descartar */}
            {discardPopup && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
                    <div className="bg-surface-container border border-white/10 rounded-3xl p-6 max-w-sm w-full shadow-2xl animate-[fade-in_0.2s_ease-out]">
                        <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
                            <span className="material-symbols-outlined text-red-500 text-2xl">warning</span>
                        </div>
                        <h3 className="text-xl font-bold text-on-surface mb-2">¿Descartar análisis?</h3>
                        <p className="text-sm text-on-surface-variant mb-6">Si realizas una nueva búsqueda, los resultados actuales se borrarán y no aparecerán en el historial a menos que los guardes.</p>
                        
                        <div className="flex flex-col gap-3">
                            <button 
                                onClick={handleDiscard}
                                className="w-full btn-outline border-red-500/20 text-red-400 hover:bg-red-500/10"
                            >
                                Sí, descartar y buscar
                            </button>
                            <button 
                                onClick={() => { setDiscardPopup(false); handleSave(); }}
                                className="w-full bg-white text-black rounded-full h-11 font-bold text-sm"
                            >
                                Cancelar y guardar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}