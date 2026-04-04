const CATEGORIAS = [
    { value: '', label: 'Selecciona categoría' },
    { value: 'desarrollo', label: 'Desarrollo de Software' },
    { value: 'diseño', label: 'Diseño UX/UI' },
    { value: 'marketing', label: 'Marketing Digital' },
    { value: 'ventas', label: 'Ventas y Business' },
    { value: 'logistica', label: 'Logística y Operaciones' },
    { value: 'rrhh', label: 'Recursos Humanos' },
    { value: 'electromecanica', label: 'Electromecánica' },
    { value: 'administracion', label: 'Administración' },
]

import { memo } from 'react'
const JobForm = memo(({
    value,
    onChange,
    categoria,
    setCategoria,
    setStack, // guardado en caso de usarlo luego
    strictness,
    setStrictness
}) => {

    function handleCategoria(e) {
        setCategoria(e.target.value)
        setStack('') // Reseteamos el stack al cambiar de categoría
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-col sm:flex-row gap-6">
                {/* Selector de Categoría */}
                <div className="flex-1">
                    <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                        Categoría de la Oferta
                    </label>
                    <div className="relative">
                        <select 
                            value={categoria} 
                            onChange={handleCategoria}
                            className="w-full appearance-none bg-surface-container border border-white/5 rounded-2xl px-5 py-3.5 text-on-surface text-sm focus:outline-none focus:border-outline-variant cursor-pointer hover:bg-surface-container-high transition-colors"
                        >
                            {CATEGORIAS.map(c => (
                                <option key={c.value} value={c.value}>{c.label}</option>
                            ))}
                        </select>
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant pointer-events-none">
                            keyboard_arrow_down
                        </span>
                    </div>
                </div>

                {/* Selector de Severidad */}
                {categoria && (
                    <div className="w-[300px]">
                        <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                            Severidad de Evaluación
                        </label>
                        <div className="switcher h-[52px]">
                            {['ligero', 'normal', 'estricto'].map(opt => (
                                <button
                                    key={opt}
                                    className={`switcher-btn h-full flex items-center justify-center !text-[13px] ${strictness === opt ? 'active font-bold' : ''}`}
                                    onClick={() => setStrictness(opt)}
                                    type="button"
                                >
                                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                                </button>
                            ))}
                            <div
                                className="switcher-thumb"
                                style={{
                                    transform: `translateX(${['ligero', 'normal', 'estricto'].indexOf(strictness) * 100}%)`,
                                    width: '33.333%'
                                }}
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Área de Texto */}
            <div>
                <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                    Descripción del puesto
                </label>
                <textarea
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    placeholder="Pega aquí la oferta de trabajo completa (responsabilidades, requisitos, beneficios)..."
                    rows={8}
                    className="w-full bg-surface-container border border-white/5 rounded-[2rem] p-6 text-on-surface text-[15px] focus:outline-none focus:border-outline-variant transition-colors resize-y shadow-inner placeholder:text-on-surface-variant/50 leading-relaxed"
                />
            </div>
        </div>
    )
})
export default JobForm