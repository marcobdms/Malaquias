import { useState } from 'react'

export default function Results({ candidates }) {
    // Por defecto, el top candidato (índice 0) está expandido
    const [expanded, setExpanded] = useState({ 0: true })
    const [contactoVisible, setContactoVisible] = useState({})

    function toggleExpand(i) {
        setExpanded(prev => ({ ...prev, [i]: !prev[i] }))
    }

    function toggleContacto(e, i) {
        e.stopPropagation() // Para no disparar el toggleExpand
        setContactoVisible(prev => ({ ...prev, [i]: !prev[i] }))
    }

    function getInitials(filename) {
        const name = filename.replace('.pdf', '')
        return name.substring(0, 2).toUpperCase()
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between mb-2">
                <div>
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">
                        Candidatos Analizados
                    </h3>
                    <p className="text-2xl font-black text-on-surface tracking-tight">
                        Inteligencia de Selección
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="text-right">
                        <p className="text-xs text-on-surface-variant">Nuestro motor de matching evaluó</p>
                        <p className="text-sm font-semibold text-on-surface">{candidates.length} perfiles técnicos</p>
                    </div>
                </div>
            </div>

            {candidates.map((c, i) => {
                const a = c.analysis || {}
                const isExpanded = !!expanded[i]
                const isTop = i === 0
                const tieneContacto = a.email_candidato || a.telefono_candidato
                const score = c.match_score.toFixed(1)

                return (
                    <div 
                        key={i} 
                        className={`crystal-card overflow-hidden transition-all duration-300 ${isTop ? 'bg-surface-container-low border-white/10' : 'bg-surface border-transparent hover:bg-surface-container-lowest cursor-pointer'} border`}
                        onClick={() => !isTop && toggleExpand(i)}
                    >
                        {/* Cabecera de la Tarjeta (Siempre visible) */}
                        <div className="flex items-center justify-between gap-6">
                            <div className="flex items-center gap-6">
                                {/* Avatar & Badge Placed Together */}
                                <div className="flex flex-col items-center gap-2">
                                    <div className={`w-14 h-14 rounded-full flex items-center justify-center text-lg font-black shadow-crystal border ${isTop ? 'bg-gradient-to-br from-primary to-primary-container text-on-primary border-transparent' : 'bg-surface-container text-on-surface border-white/5'}`}>
                                        {getInitials(c.filename)}
                                    </div>
                                    {isTop && (
                                        <span className="bg-primary text-on-primary text-[9px] font-black tracking-widest uppercase px-2 py-0.5 rounded-full whitespace-nowrap">
                                            Mejor Candidato
                                        </span>
                                    )}
                                </div>

                                <div>
                                    <h4 className="text-xl font-bold text-on-surface tracking-tight">
                                        {c.filename.replace('.pdf', '')}
                                    </h4>
                                    <div className="flex items-center gap-2 mt-1">
                                        <span className="text-xs text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-md border border-white/5">
                                            Perfil Analizado
                                        </span>
                                        {a.recomendacion && (
                                            <span className="text-xs text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-md border border-white/5">
                                                Recomendación: {a.recomendacion}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-6">
                                <div className="text-right">
                                    <p className="text-3xl font-black tracking-tighter text-on-surface">{score}%</p>
                                    <p className="text-[9px] font-bold text-on-surface-variant uppercase tracking-widest mt-0.5">Match Score</p>
                                </div>

                                <div className="flex items-center gap-3">
                                    {!isTop && (
                                        <button 
                                            className="btn-outline h-10 px-6 flex items-center justify-center"
                                            onClick={(e) => { e.stopPropagation(); toggleExpand(i); }}
                                        >
                                            {isExpanded ? 'Colapsar' : 'Ver Análisis'}
                                        </button>
                                    )}
                                    {isTop && tieneContacto && (
                                        <button 
                                            className="bg-primary text-on-primary h-10 px-6 rounded-full font-semibold text-sm hover:scale-[1.02] active:scale-95 transition-transform"
                                            onClick={(e) => toggleContacto(e, i)}
                                        >
                                            {contactoVisible[i] ? 'Ocultar info' : 'Contactar'}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Error Handling si existe en el análisis */}
                        {a.error && isExpanded && (
                            <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl">
                                <p className="text-sm text-red-400">Error en análisis: {a.error}</p>
                            </div>
                        )}

                        {/* Contenido Expandido */}
                        {!a.error && isExpanded && (
                            <div className={`mt-8 pt-8 border-t border-outline-variant/30 transition-all duration-500 origin-top`}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                                    {/* Fortalezas */}
                                    <div>
                                        <h5 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
                                            Fortalezas Destacadas
                                        </h5>
                                        <ul className="space-y-4">
                                            {(a.fortalezas || []).map((f, j) => (
                                                <li key={j} className="flex gap-3 text-sm text-on-surface">
                                                    <span className="material-symbols-outlined text-[18px] text-primary shrink-0 mt-0.5">check_circle</span>
                                                    <span className="leading-relaxed">{f}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    {/* Carencias */}
                                    <div>
                                        <h5 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
                                            Áreas de Mejora
                                        </h5>
                                        <ul className="space-y-4">
                                            {(a.carencias || []).map((car, j) => (
                                                <li key={j} className="flex gap-3 text-sm text-on-surface-variant">
                                                    <span className="material-symbols-outlined text-[18px] text-on-surface-variant shrink-0 mt-0.5">info</span>
                                                    <span className="leading-relaxed">{car}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>

                                {/* Valoración AI */}
                                {a.valoracion && (
                                    <div className="mt-8 bg-surface-container rounded-2xl p-6 border border-white/5 relative overflow-hidden group">
                                        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
                                        <h5 className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-on-surface mb-3">
                                            <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
                                            Resumen de Malaquías AI
                                        </h5>
                                        <p className="text-[15px] leading-relaxed text-on-surface-variant italic relative z-10">
                                            "{a.valoracion}"
                                        </p>
                                    </div>
                                )}

                                {/* Panel de Contacto Expandido para todos (No solo top, si tienen y hacen click en "Ver perfil / Contactar" pero no caben los botones) */}
                                {(!isTop && tieneContacto) && (
                                    <div className="mt-6 flex justify-end">
                                         <button 
                                            className="bg-primary text-on-primary h-10 px-6 rounded-full font-semibold text-sm hover:scale-[1.02] active:scale-95 transition-transform"
                                            onClick={(e) => toggleContacto(e, i)}
                                        >
                                            {contactoVisible[i] ? 'Ocultar contacto' : 'Revelar contacto'}
                                        </button>
                                    </div>
                                )}

                                {/* Datos de Contacto */}
                                {contactoVisible[i] && tieneContacto && (
                                    <div className="mt-4 p-4 rounded-2xl bg-surface-container-high border border-white/10 flex flex-wrap gap-6 items-center animate-[fade-in_0.3s_ease-out]">
                                        {a.email_candidato && a.email_candidato !== 'null' && (
                                            <div className="flex items-center gap-2 text-sm text-on-surface">
                                                <span className="material-symbols-outlined text-[18px] text-on-surface-variant">mail</span>
                                                <a href={`mailto:${a.email_candidato}`} className="hover:underline">{a.email_candidato}</a>
                                            </div>
                                        )}
                                        {a.telefono_candidato && a.telefono_candidato !== 'null' && (
                                            <div className="flex items-center gap-2 text-sm text-on-surface">
                                                <span className="material-symbols-outlined text-[18px] text-on-surface-variant">call</span>
                                                <a href={`tel:${a.telefono_candidato}`} className="hover:underline">{a.telefono_candidato}</a>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}