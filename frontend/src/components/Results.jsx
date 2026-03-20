import { useState } from 'react'

export default function Results({ candidates }) {
    const [contactoVisible, setContactoVisible] = useState({})

    function toggleContacto(i) {
        setContactoVisible(prev => ({ ...prev, [i]: !prev[i] }))
    }

    function recClass(rec) {
        if (!rec) return ''
        const r = rec.toLowerCase()
        if (r.includes('entrevistar')) return 'rec-green'
        if (r.includes('considerar')) return 'rec-amber'
        return 'rec-red'
    }

    function scoreColor(score) {
        if (score >= 70) return '#1D9E75'
        if (score >= 45) return '#BA7517'
        return '#E24B4A'
    }

    return (
        <div className="results">
            <p className="results-header">
                {candidates.length} candidato{candidates.length > 1 ? 's' : ''} · ordenados por puntuación
            </p>

            {candidates.map((c, i) => {
                const a = c.analysis || {}
                const tieneContacto = a.email_candidato || a.telefono_candidato

                return (
                    <div key={i} className={`candidate-card ${i === 0 ? 'top-card' : ''}`}>
                        <div className="candidate-top">
                            <div className="candidate-name">
                                {c.filename.replace('.pdf', '')}
                                <span className="rank-badge">{i === 0 ? 'Mejor candidato' : `#${i + 1}`}</span>
                            </div>
                            <span className="score">{c.match_score.toFixed(1)}%</span>
                        </div>

                        <div className="score-bar-wrap">
                            <div className="score-bar" style={{ width: `${c.match_score}%`, background: scoreColor(c.match_score) }} />
                        </div>

                        {a.error ? (
                            <p className="error-box">{a.error}</p>
                        ) : (
                            <>
                                <div className="analysis-grid">
                                    <div className="analysis-block">
                                        <h4>Fortalezas</h4>
                                        <ul>{(a.fortalezas || []).map((f, j) => <li key={j} className="dot-green">{f}</li>)}</ul>
                                    </div>
                                    <div className="analysis-block">
                                        <h4>Carencias</h4>
                                        <ul>{(a.carencias || []).map((car, j) => <li key={j} className="dot-red">{car}</li>)}</ul>
                                    </div>
                                </div>

                                {a.valoracion && <p className="valoracion">"{a.valoracion}"</p>}

                                <div className="card-footer">
                                    {a.recomendacion && (
                                        <span className={`recomendacion ${recClass(a.recomendacion)}`}>
                                            {a.recomendacion}
                                        </span>
                                    )}

                                    {tieneContacto && (
                                        <button className="btn-contactar" onClick={() => toggleContacto(i)}>
                                            {contactoVisible[i] ? 'Ocultar' : 'Contactar'}
                                        </button>
                                    )}
                                </div>

                                {contactoVisible[i] && (
                                    <div className="contacto-panel">
                                        {a.email_candidato && a.email_candidato !== 'null' && (
                                            <span>✉ {a.email_candidato}</span>
                                        )}
                                        {a.telefono_candidato && a.telefono_candidato !== 'null' && (
                                            <span>✆ {a.telefono_candidato}</span>
                                        )}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )
            })}
        </div>
    )
}