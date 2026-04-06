const CATEGORIAS = [
    { value: '', label: 'Selecciona categoría' },
    { value: 'desarrollo', label: 'Desarrollo' },
    { value: 'diseño', label: 'Diseño' },
    { value: 'marketing', label: 'Marketing' },
    { value: 'ventas', label: 'Ventas' },
    { value: 'logistica', label: 'Logística' },
    { value: 'rrhh', label: 'RRHH' },
    { value: 'electromecanica', label: 'Electromecánica' },
    { value: 'administracion', label: 'Administración' },
    { value: 'data', label: 'Data / Analytics' },
    { value: 'devops', label: 'DevOps / Cloud' },
    { value: 'ciberseguridad', label: 'Ciberseguridad' },
    { value: 'finanzas', label: 'Finanzas' },
    { value: 'atencion_cliente', label: 'Atención al Cliente' },
]

const STACKS = {
    desarrollo: ['Python', 'JavaScript', 'React', 'Node.js', 'SQL', 'Java', 'TypeScript', 'FastAPI'],
    diseño: ['Figma', 'Adobe XD', 'Illustrator', 'Photoshop', 'UI/UX', 'Sketch'],
    marketing: ['SEO', 'SEM', 'Google Ads', 'Meta Ads', 'Email marketing', 'Analytics'],
    ventas: ['CRM', 'Salesforce', 'HubSpot', 'Negociación', 'B2B', 'B2C'],
    logistica: ['ERP', 'SAP', 'MRP', 'Gestión de almacén', 'Supply chain'],
    rrhh: ['ATS', 'Selección', 'Nóminas', 'Formación', 'HRBP'],
    electromecanica: ['PLC', 'Soldadura', 'Mantenimiento industrial', 'Neumática', 'Hidráulica'],
    administracion: ['Excel', 'Contabilidad', 'Facturación', 'Office', 'ERP'],
}

export default function JobForm({
    value,
    onChange,
    categoria,
    setCategoria,
    setStack,
    strictness,
<<<<<<< Updated upstream
    setStrictness
}) {
    const stackOptions = STACKS[categoria] || []
=======
    setStrictness,
    balance,
    setBalance,
}) => {
>>>>>>> Stashed changes

    function handleCategoria(e) {
        setCategoria(e.target.value)
        setStack('')
    }

    const balanceLabel =
        balance <= 30 ? 'Prioriza perfil adaptable y potencial transferible'
        : balance <= 70 ? 'Balance entre contexto y requisitos técnicos'
        : 'Prioriza keywords exactas y requisitos duros'

    const balanceLabelLeft = balance <= 30 ? 'font-bold text-on-surface' : 'text-on-surface-variant'
    const balanceLabelRight = balance >= 70 ? 'font-bold text-on-surface' : 'text-on-surface-variant'

    return (
        <div className="card">
            <div className="filtros-row">
                {/* Selector de Categoría */}
                <div className="filtro-group">
                    <label>Categoría</label>
                    <select value={categoria} onChange={handleCategoria}>
                        {CATEGORIAS.map(c => (
                            <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                    </select>
                </div>

                {/* Selector de Severidad (Solo si hay una categoría seleccionada) */}
                {categoria && (
                    <div className="filtro-group">
                        <label>Severidad</label>
                        <div className="switcher">
                            {['ligero', 'normal', 'estricto'].map(opt => (
                                <button
                                    key={opt}
                                    className={`switcher-btn ${strictness === opt ? 'active' : ''}`}
                                    onClick={() => setStrictness(opt)}
                                    type="button"
                                >
                                    {opt.charAt(0).toUpperCase() + opt.slice(1)}
                                </button>
                            ))}
                            <div
                                className="switcher-thumb"
                                style={{
                                    transform: `translateX(${['ligero', 'normal', 'estricto'].indexOf(strictness) * 100}%)`
                                }}
                            />
                        </div>
                    </div>
                )}
            </div>

<<<<<<< Updated upstream
            {/* Área de Texto para la descripción */}
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: '1rem' }}>
                <label>Descripción del puesto</label>
=======
            {/* Slider Balance — visible cuando hay categoría seleccionada */}
            {categoria && (
                <div>
                    <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                        Balance del Motor
                    </label>
                    <div className="bg-surface-container border border-white/5 rounded-2xl px-5 py-4 flex flex-col gap-3">
                        <div className="flex items-center gap-4">
                            <span className={`text-xs shrink-0 transition-colors ${balanceLabelLeft}`}>Semántico</span>
                            <input
                                type="range"
                                min={0}
                                max={100}
                                value={balance}
                                onChange={e => setBalance(Number(e.target.value))}
                                className="flex-1 h-1 appearance-none bg-white/10 rounded-full outline-none cursor-pointer accent-white"
                                id="balance-slider"
                            />
                            <span className={`text-xs shrink-0 transition-colors ${balanceLabelRight}`}>Técnico</span>
                        </div>
                        <p className="text-[11px] text-on-surface-variant text-center leading-tight transition-all">
                            {balanceLabel}
                        </p>
                    </div>
                </div>
            )}

            {/* Área de Texto */}
            <div>
                <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                    Descripción del puesto
                </label>
>>>>>>> Stashed changes
                <textarea
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    placeholder="Pega aquí la oferta de trabajo completa..."
                    rows={6}
                />
            </div>
        </div>
    )
}