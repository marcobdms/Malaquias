import { useEffect } from 'react'

export default function CVModal({ isOpen, onClose, cvText, filename, candidateName, pdfUrl }) {
    // Evitar scroll en el body cuando el modal está abierto
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden'
        } else {
            document.body.style.overflow = 'unset'
        }
        return () => { document.body.style.overflow = 'unset' }
    }, [isOpen])

    // Función para renderizar el texto plano añadiendo negritas a las frases en Mayúsculas (posibles subtitulos)
    const renderFormattedText = (text) => {
        if (!text) return null
        return text.split('\n').map((line, idx) => {
            const isAllCaps = line.trim().length > 3 && line === line.toUpperCase() && !line.match(/^[0-9\W]+$/)
            return (
                <span key={idx} className={isAllCaps ? 'font-black block mt-4 mb-2 text-sm text-zinc-800' : 'block mb-1 text-sm'}>
                    {line}
                </span>
            )
        })
    }

    if (!isOpen) return null

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 sm:p-6 bg-black/95 animate-[fade-in_0.2s_ease-out]">
            {/* Contenedor principal responsive */}
            <div className="w-full max-w-4xl h-[95vh] flex flex-col bg-surface-container rounded-[1.5rem] shadow-2xl border border-white/10 overflow-hidden transform transition-all">
                
                {/* Cabecera del Documento */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-surface-container-high/50 backdrop-blur-sm z-10 shrink-0">
                    <div className="flex items-center gap-3 overflow-hidden">
                        <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                            <span className="material-symbols-outlined text-white text-[20px]">description</span>
                        </div>
                        <div className="min-w-0">
                            <h3 className="text-white font-bold text-lg truncate">
                                Perfil: {candidateName}
                            </h3>
                            <p className="text-on-surface-variant font-medium text-xs truncate">
                                {filename}
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose}
                        className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/10 text-on-surface-variant hover:text-white transition-colors shrink-0"
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                {/* Área del Documento (A4 Simulation en desktop o iFrame PDF) */}
                <div className={`flex-1 w-full flex justify-center bg-[#151515] ${pdfUrl ? 'p-0' : 'p-0 sm:p-8 overflow-y-auto'}`}>
                    {pdfUrl ? (
                        <iframe src={pdfUrl} className="w-full h-full border-0" title="CV Original PDF" />
                    ) : !cvText ? (
                        <div className="flex flex-col items-center justify-center h-full gap-4">
                            <span className="material-symbols-outlined text-4xl text-on-surface-variant animate-spin">refresh</span>
                            <p className="text-on-surface-variant font-medium">Renderizando texto plano...</p>
                        </div>
                    ) : (
                        <div className="bg-white text-zinc-700 w-full max-w-[210mm] min-h-[297mm] h-fit sm:rounded sm:shadow-2xl p-8 sm:p-14 lg:p-20 font-sans leading-relaxed whitespace-pre-wrap format-a4">
                            {renderFormattedText(cvText)}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
