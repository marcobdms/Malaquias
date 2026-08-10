import { memo } from 'react'
import CriteriaEditor from './CriteriaEditor'

const CATEGORIAS = [
    { value: '', label: 'Selecciona categoría' },
    { value: 'desarrollo', label: 'Desarrollo de Software' },
    { value: 'it_sistemas', label: 'IT / Sistemas' },
    { value: 'diseño', label: 'Diseño UX/UI' },
    { value: 'marketing', label: 'Marketing Digital' },
    { value: 'ventas', label: 'Ventas y Business' },
    { value: 'logistica', label: 'Logística y Operaciones' },
    { value: 'rrhh', label: 'Recursos Humanos' },
    { value: 'electromecanica', label: 'Electromecánica' },
    { value: 'administracion', label: 'Administración' },
]

const JobForm = memo(({ value, onChange, categoria, setCategoria, setStack, criteria, setCriteria }) => {
    function handleCategoria(event) {
        setCategoria(event.target.value)
        setStack('')
    }

    return (
        <div className="flex flex-col gap-6">
            <div>
                <label htmlFor="job-category" className="crystal-label uppercase tracking-widest">Categoría de la oferta</label>
                <div className="relative">
                    <select
                        id="job-category"
                        value={categoria}
                        onChange={handleCategoria}
                        className="w-full appearance-none bg-surface-container border border-white/5 rounded-2xl px-5 py-3.5 text-on-surface text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white cursor-pointer hover:bg-surface-container-high transition-colors"
                    >
                        {CATEGORIAS.map(category => (
                            <option key={category.value} value={category.value}>{category.label}</option>
                        ))}
                    </select>
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant pointer-events-none" aria-hidden="true">keyboard_arrow_down</span>
                </div>
            </div>

            <div>
                <label htmlFor="job-description" className="crystal-label uppercase tracking-widest">Descripción del puesto</label>
                <textarea
                    id="job-description"
                    value={value}
                    onChange={event => onChange(event.target.value)}
                    placeholder="Pega aquí la oferta completa: responsabilidades, requisitos y condiciones."
                    rows={8}
                    aria-describedby="job-description-hint"
                    className="w-full bg-surface-container border border-white/5 rounded-[2rem] p-6 text-on-surface text-[15px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white transition-colors resize-y shadow-inner placeholder:text-on-surface-variant/50 leading-relaxed"
                />
                <p id="job-description-hint" className="text-xs text-on-surface-variant mt-2">
                    La descripción original se conserva como contexto. Los criterios confirmados guían la puntuación.
                </p>
            </div>

            <CriteriaEditor criteria={criteria} onChange={setCriteria} />
        </div>
    )
})

export default JobForm
