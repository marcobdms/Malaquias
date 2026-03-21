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
    setStrictness
}) {
    const stackOptions = STACKS[categoria] || []

    function handleCategoria(e) {
        setCategoria(e.target.value)
        setStack('') // Reseteamos el stack al cambiar de categoría
    }

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

            {/* Área de Texto para la descripción */}
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: '1rem' }}>
                <label>Descripción del puesto</label>
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