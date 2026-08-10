const PRIORITIES = [
    { value: 'required', label: 'Obligatorio' },
    { value: 'important', label: 'Importante' },
    { value: 'preferred', label: 'Deseable' },
    { value: 'not_evaluable', label: 'No evaluable en CV' },
]

function createCriterion() {
    return {
        id: `criterion-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        label: '',
        priority: 'important',
        equivalences: [],
    }
}

export default function CriteriaEditor({ criteria, onChange }) {
    const addCriterion = () => onChange([...criteria, createCriterion()])
    const updateCriterion = (id, patch) => onChange(criteria.map(criterion => (
        criterion.id === id ? { ...criterion, ...patch } : criterion
    )))
    const removeCriterion = id => onChange(criteria.filter(criterion => criterion.id !== id))

    const evaluableCount = criteria.filter(c => c.priority !== 'not_evaluable' && c.label.trim()).length
    const interviewCount = criteria.filter(c => c.priority === 'not_evaluable' && c.label.trim()).length

    return (
        <section aria-labelledby="criteria-title" className="border-t border-outline-variant/30 pt-6">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-5">
                <div>
                    <h3 id="criteria-title" className="text-sm font-bold text-on-surface">Criterios confirmados</h3>
                    <p className="text-sm text-on-surface-variant mt-1 max-w-2xl">
                        Aclara qué debe buscar Malaquías. Si el CV no menciona algo, se tratará como información desconocida.
                    </p>
                </div>
                <button type="button" onClick={addCriterion} className="btn-outline min-h-11 shrink-0">
                    Añadir criterio
                </button>
            </div>

            <p className="sr-only" aria-live="polite">
                {evaluableCount} criterios evaluables y {interviewCount} reservados para entrevista.
            </p>

            {criteria.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-outline-variant bg-surface-container-low/40 p-5">
                    <p className="text-sm text-on-surface-variant">
                        Puedes analizar la descripción original o añadir los requisitos que realmente importan.
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {criteria.map((criterion, index) => {
                        const labelId = `${criterion.id}-label`
                        const priorityId = `${criterion.id}-priority`
                        const equivalencesId = `${criterion.id}-equivalences`
                        return (
                            <article key={criterion.id} className="rounded-2xl bg-surface-container border border-white/5 p-4">
                                <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_180px_auto] gap-3 items-end">
                                    <div>
                                        <label htmlFor={labelId} className="crystal-label">Criterio {index + 1}</label>
                                        <input
                                            id={labelId}
                                            value={criterion.label}
                                            onChange={event => updateCriterion(criterion.id, { label: event.target.value })}
                                            placeholder="Ej. Experiencia con radiofrecuencia"
                                            className="crystal-input bg-surface-container-low"
                                        />
                                    </div>
                                    <div>
                                        <label htmlFor={priorityId} className="crystal-label">Prioridad</label>
                                        <select
                                            id={priorityId}
                                            value={criterion.priority}
                                            onChange={event => updateCriterion(criterion.id, { priority: event.target.value })}
                                            className="crystal-input bg-surface-container-low"
                                        >
                                            {PRIORITIES.map(priority => (
                                                <option key={priority.value} value={priority.value}>{priority.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => removeCriterion(criterion.id)}
                                        className="min-h-11 min-w-11 rounded-full text-on-surface-variant hover:text-red-400 hover:bg-red-500/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white transition-colors"
                                        aria-label={`Eliminar criterio ${index + 1}`}
                                    >
                                        <span className="material-symbols-outlined" aria-hidden="true">delete</span>
                                    </button>
                                </div>
                                <div className="mt-3">
                                    <label htmlFor={equivalencesId} className="crystal-label">
                                        Equivalencias aceptadas <span className="normal-case font-normal">(opcionales, separadas por comas)</span>
                                    </label>
                                    <input
                                        id={equivalencesId}
                                        value={(criterion.equivalences || []).join(', ')}
                                        onChange={event => updateCriterion(criterion.id, {
                                            equivalences: event.target.value.split(',').map(value => value.trim()).filter(Boolean),
                                        })}
                                        placeholder="Ej. carretilla elevadora, montacargas"
                                        className="crystal-input bg-surface-container-low"
                                    />
                                </div>
                            </article>
                        )
                    })}
                </div>
            )}
        </section>
    )
}
