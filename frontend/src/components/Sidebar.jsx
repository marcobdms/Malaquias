export default function Sidebar() {
    return (
        <aside className="fixed top-0 left-0 bottom-0 w-[240px] bg-background border-r border-white/5 z-50 flex flex-col">
            {/* Logo area */}
            <div className="h-14 flex items-center px-6 border-b border-white/5">
                <h1 className="text-xl font-black text-on-surface tracking-tight">Malaquías</h1>
            </div>

            {/* Suite info */}
            <div className="px-6 py-4 mt-2">
                <p className="text-sm font-medium text-on-surface">Recruitment Suite</p>
                <p className="text-[10px] text-on-surface-variant tracking-wider">Enterprise Edition</p>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 mt-4 space-y-1">
                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl bg-surface-container text-on-surface text-sm font-medium transition-colors">
                    <span className="material-symbols-outlined text-[20px]">dashboard</span>
                    Dashboard
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface text-sm font-medium transition-colors">
                    <span className="material-symbols-outlined text-[20px]">group</span>
                    Talent Pool
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface text-sm font-medium transition-colors">
                    <span className="material-symbols-outlined text-[20px]">bar_chart</span>
                    Reports
                </button>
            </nav>

            {/* Bottom Actions */}
            <div className="p-4 border-t border-white/5 mt-auto">
                <button className="btn-primary w-full shadow-crystal mb-4">
                    Post New Job
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface text-sm font-medium transition-colors">
                    <span className="material-symbols-outlined text-[18px]">help</span>
                    Help Center
                </button>
            </div>
        </aside>
    )
}
