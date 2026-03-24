export default function Navbar({ user, onLogout }) {
    // Generar iniciales ("Juan Perez" -> "JP")
    const getInitials = (name) => {
        if (!name) return '?'
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    }

    return (
        <nav className="fixed top-0 left-0 right-0 h-14 bg-surface/80 backdrop-blur-xl border-b border-white/5 z-50 flex items-center justify-between px-6 pl-[260px] transition-all">
            <div className="flex items-center gap-6">
                <span className="text-on-surface font-semibold text-sm cursor-pointer border-b-2 border-primary py-4">Dashboard</span>
                <span className="text-on-surface-variant font-medium text-sm cursor-pointer hover:text-on-surface transition-colors">Talent Pool</span>
                <span className="text-on-surface-variant font-medium text-sm cursor-pointer hover:text-on-surface transition-colors">Reports</span>
            </div>

            <div className="flex items-center gap-4">
                <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-[18px] text-on-surface-variant">search</span>
                    <input 
                        type="text" 
                        placeholder="Search candidates..." 
                        className="bg-surface-container-low border border-white/5 rounded-full py-1.5 pl-9 pr-4 text-sm text-on-surface focus:outline-none focus:border-outline-variant transition-colors w-64"
                    />
                </div>
                
                <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors">
                    <span className="material-symbols-outlined text-[20px]">notifications</span>
                </button>
                <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors">
                    <span className="material-symbols-outlined text-[20px]">settings</span>
                </button>

                <div className="flex items-center gap-3 pl-2 border-l border-white/5 ml-2 group cursor-pointer" onClick={onLogout} title="Cerrar sesión">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary-container text-on-primary font-bold text-xs flex items-center justify-center shadow-crystal group-hover:scale-105 transition-transform">
                        {getInitials(user)}
                    </div>
                </div>
            </div>
        </nav>
    )
}
