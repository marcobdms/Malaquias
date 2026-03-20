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

export default function JobForm({ value, onChange, categoria, setCategoria, stack, setStack }) {
    const stackOptions = STACKS[categoria] || []

    function handleCategoria(e) {
        setCategoria(e.target.value)
        setStack('')
    }

    return (
        <div className="card">
            <div className="filtros-row">
                <div className="filtro-group">
                    <label>Categoría</label>
                    <select value={categoria} onChange={handleCategoria}>
                        {CATEGORIAS.map(c => (
                            <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                    </select>
                </div>

                {stackOptions.length > 0 && (
                    <div className="filtro-group">
                        <label>Requisito clave</label>
                        <select value={stack} onChange={e => setStack(e.target.value)}>
                            <option value="">Selecciona requisito</option>
                            {stackOptions.map(s => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                    </div>
                )}
            </div>

            <label style={{ marginTop: '1rem' }}>Descripción del puesto</label>
            <textarea
                value={value}
                onChange={e => onChange(e.target.value)}
                placeholder="Pega aquí la oferta de trabajo completa..."
                rows={6}
            />
        </div>
    )
}