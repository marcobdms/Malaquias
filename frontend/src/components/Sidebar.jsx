export default function Sidebar({ currentView, onNavigate }) {
    const navItems = [
        { id: 'dashboard', icon: 'dashboard', label: 'Dashboard' },
        { id: 'screener', icon: 'group', label: 'CV Screener' },
        { id: 'positions', icon: 'bookmarks', label: 'Análisis' },
    ]

    return (
        <>
            {/* DESKTOP SIDEBAR */}
            <aside className="hidden md:flex fixed top-0 left-0 bottom-0 w-[240px] bg-background border-r border-white/5 z-50 flex-col">
                {/* Logo area */}
                <div className="h-14 flex items-center px-6 border-b border-white/5 shrink-0">
                    <h1 className="text-xl font-black text-on-surface tracking-tight">Malaquías</h1>
                </div>

                {/* Suite info */}
                <div className="px-6 py-4 mt-2">
                    <p className="text-sm font-medium text-on-surface">Recruitment Suite</p>
                    <p className="text-[10px] text-on-surface-variant tracking-wider">Enterprise Edition</p>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-4 mt-4 space-y-1">
                    {navItems.map(item => (
                        <button
                            key={item.id}
                            onClick={() => onNavigate(item.id)}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                                currentView === item.id
                                    ? 'bg-surface-container text-on-surface border border-white/5 shadow-crystal'
                                    : 'text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface'
                            }`}
                        >
                            <span className={`material-symbols-outlined text-[20px] ${currentView === item.id ? 'text-primary' : ''}`}>
                                {item.icon}
                            </span>
                            {item.label}
                        </button>
                    ))}
                </nav>

                {/* Bottom Actions */}
                <div className="p-4 border-t border-white/5 mt-auto">
                    <button 
                        onClick={() => onNavigate('screener')}
                        className="btn-primary w-full shadow-crystal mb-4"
                    >
                        Nuevo Análisis
                    </button>
                    <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface text-sm font-medium transition-colors">
                        <span className="material-symbols-outlined text-[18px]">help</span>
                        Help Center
                    </button>
                </div>
            </aside>

            {/* MOBILE BOTTOM NAV */}
            <div className="md:hidden fixed bottom-0 left-0 right-0 h-[85px] bg-background border-t border-white/5 z-50 flex items-center justify-around px-2 pb-[15px] shadow-[0_-10px_40px_rgba(0,0,0,0.5)]">
                {navItems.map(item => (
                    <button
                        key={item.id}
                        onClick={() => onNavigate(item.id)}
                        className={`flex-1 flex flex-col items-center justify-center h-full gap-0.5 transition-all ${
                            currentView === item.id ? 'text-primary' : 'text-zinc-500'
                        }`}
                    >
                        <div className={`w-12 h-12 flex items-center justify-center transition-all ${currentView === item.id ? 'bg-primary/10 rounded-2xl' : ''}`}>
                            <span className="material-symbols-outlined text-[26px]">
                                {item.icon}
                            </span>
                        </div>
                        <span className="text-[10px] font-bold uppercase tracking-tight -mt-1">{item.label}</span>
                    </button>
                ))}
            </div>
        </>
    )
}
