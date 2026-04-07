export default function Progress({ total, done, status }) {
    const pct = total > 0 ? Math.round((done / total) * 100) : 0

    return (
        <div className="bg-surface-container rounded-[1.5rem] p-5 shadow-crystal border border-white/5">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    {status === 'analyzing' && (
                        <>
                            <svg className="animate-spin h-5 w-5 text-primary" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span className="text-sm font-semibold text-on-surface tracking-wide">Analizando {done} de {total}...</span>
                        </>
                    )}
                    {status === 'waking' && (
                        <>
                            <svg className="animate-spin h-5 w-5 text-on-surface-variant" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <span className="text-sm text-on-surface-variant tracking-wide">Despertando motor neuronal...</span>
                        </>
                    )}
                    {status === 'done' && (
                        <>
                            <div className="bg-green-500/20 text-green-400 p-1 rounded-full border border-green-500/30">
                                <span className="material-symbols-outlined text-[16px] block">check</span>
                            </div>
                            <span className="text-sm font-bold text-green-400">Análisis completado</span>
                        </>
                    )}
                    {status === 'error' && (
                        <>
                            <div className="bg-red-500/20 text-red-400 p-1 rounded-full border border-red-500/30">
                                <span className="material-symbols-outlined text-[16px] block">close</span>
                            </div>
                            <span className="text-sm font-bold text-red-400">Error en el análisis</span>
                        </>
                    )}
                </div>
                <span className="text-sm font-black text-on-surface">{pct}%</span>
            </div>

            <div className="h-2 w-full bg-background rounded-full overflow-hidden border border-outline-variant/20 shadow-inner">
                <div
                    className={`h-full rounded-full transition-all duration-700 ease-out relative ${
                        status === 'done' ? 'bg-gradient-to-r from-green-500 to-green-400' :
                        status === 'error' ? 'bg-gradient-to-r from-red-500 to-red-400' :
                        'bg-gradient-to-r from-primary-container to-primary'
                    }`}
                    style={{ width: `${pct}%` }}
                >
                    {/* Animated shine effect if not done/error */}
                    {(status === 'analyzing' || status === 'waking') && (
                        <div className="absolute top-0 left-0 bottom-0 right-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
                    )}
                </div>
            </div>
        </div>
    )
}