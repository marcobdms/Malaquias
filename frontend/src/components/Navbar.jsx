import { useState, useRef, useEffect } from 'react'

export default function Navbar({ user, onLogout, onNavigate }) {
    const [menuOpen, setMenuOpen] = useState(false)
    const menuRef = useRef(null)

    // Cerrar menu al hacer click fuera
    useEffect(() => {
        function handleClickOutside(e) {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                setMenuOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const getInitials = (name) => {
        if (!name) return '?'
        return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    }

    return (
        <nav className="fixed top-0 left-0 right-0 h-14 bg-surface/80 backdrop-blur-xl border-b border-white/5 z-50 flex items-center justify-between px-4 md:px-6 md:pl-[260px] transition-all">
            {/* Nav Tabs - Desktop Only */}
            <div className="hidden md:flex items-center gap-6">
                <span className="text-on-surface font-semibold text-sm cursor-pointer border-b-2 border-primary py-4">Dashboard</span>
                <span className="text-on-surface-variant font-medium text-sm cursor-pointer hover:text-on-surface transition-colors">Talent Pool</span>
                <span className="text-on-surface-variant font-medium text-sm cursor-pointer hover:text-on-surface transition-colors">Reports</span>
            </div>

            {/* Logo/Name - Mobile Only */}
            <div className="md:hidden flex items-center">
                <h1 className="text-lg font-black text-white tracking-tight">Malaquías</h1>
            </div>

            <div className="flex items-center gap-2 md:gap-4">
                {/* Search - Desktop Only */}
                <div className="hidden md:block relative">
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
                <div className="hidden sm:flex">
                    <button className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors">
                        <span className="material-symbols-outlined text-[20px]">settings</span>
                    </button>
                </div>

                {/* Avatar + Dropdown Menu */}
                <div className="relative" ref={menuRef}>
                    <div 
                        className="flex items-center gap-3 pl-2 sm:border-l border-white/5 sm:ml-2 group cursor-pointer" 
                        onClick={() => setMenuOpen(!menuOpen)}
                    >
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#0bdacb] to-primary-container text-[#0a0a0a] font-bold text-xs flex items-center justify-center shadow-crystal group-hover:scale-105 transition-transform">
                            {getInitials(user)}
                        </div>
                    </div>

                    {/* Dropdown Popup */}
                    {menuOpen && (
                        <div className="absolute right-0 top-12 w-52 bg-surface-container border border-white/10 rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.5)] overflow-hidden animate-[fade-in_0.15s_ease-out] z-[60]">
                            {/* User Info Header */}
                            <div className="px-4 py-3 border-b border-white/5">
                                <p className="text-sm font-semibold text-on-surface truncate">{user}</p>
                                <p className="text-xs text-on-surface-variant mt-0.5">Cuenta personal</p>
                            </div>

                            {/* Menu Items */}
                            <div className="py-1">
                                <button 
                                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors text-left"
                                    onClick={() => { setMenuOpen(false); onNavigate('profile'); }}
                                >
                                    <span className="material-symbols-outlined text-[18px]">person</span>
                                    Configuración de Perfil
                                </button>
                                <button 
                                    className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors text-left"
                                    onClick={() => { setMenuOpen(false); onLogout(); }}
                                >
                                    <span className="material-symbols-outlined text-[18px]">logout</span>
                                    Cerrar sesión
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    )
}
