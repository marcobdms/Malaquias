export default function Progress({ total, done, status }) {
    const pct = status === 'waking' ? 20
        : total > 0 ? Math.round((done / total) * 100)
            : 0

    return (
        <div className="progress-wrap">
            <div className="progress-header">
                <div className="progress-status">
                    {status === 'analyzing' && (
                        <>
                            <svg width="14" height="14" viewBox="0 0 16 16" className="spin" fill="none">
                                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"
                                    strokeDasharray="20 18" />
                            </svg>
                            {/* icono spinner — puedes cambiar por el tuyo */}
                            <span>Analizando {done} de {total}...</span>
                        </>
                    )}
                    {status === 'waking' && (
                        <>
                            <svg width="14" height="14" viewBox="0 0 16 16" className="spin" fill="none">
                                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"
                                    strokeDasharray="20 18" />
                            </svg>
                            {/* icono spinner — puedes cambiar por el tuyo */}
                            <span>Despertando a Malaquías...</span>
                        </>
                    )}
                    {status === 'done' && (
                        <>
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                                <path d="M3 8l3.5 3.5L13 4" stroke="#1D9E75" strokeWidth="1.5" strokeLinecap="round" />
                            </svg>
                            {/* icono check — puedes cambiar por el tuyo */}
                            <span style={{ color: '#1D9E75' }}>Análisis completado</span>
                        </>
                    )}
                    {status === 'error' && (
                        <>
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                                <path d="M4 4l8 8M12 4l-8 8" stroke="#E24B4A" strokeWidth="1.5" strokeLinecap="round" />
                            </svg>
                            {/* icono error — puedes cambiar por el tuyo */}
                            <span style={{ color: '#E24B4A' }}>Error en el análisis</span>
                        </>
                    )}
                </div>
                <span className="progress-pct">{pct}%</span>
            </div>

            <div className="progress-bar-wrap">
                <div
                    className={`progress-bar-fill ${status === 'done' ? 'done' : ''}`}
                    style={{ width: `${pct}%` }}
                />
            </div>
        </div>
    )
}