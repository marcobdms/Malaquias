import { useRef, useState, memo } from 'react'
const DropZone = memo(({ files, setFiles }) => {
    const inputRef = useRef()
    const [isDragging, setIsDragging] = useState(false)

    function addFiles(newFiles) {
        const xliffFiles = Array.from(newFiles).filter(f => f.name.endsWith('.pdf'))
        setFiles(prev => [...prev, ...xliffFiles].slice(0, 20)) // permitiremos 20 para hacer match con ref
    }

    function removeFile(index) {
        setFiles(prev => prev.filter((_, i) => i !== index))
    }

    function onDrop(e) {
        e.preventDefault()
        setIsDragging(false)
        addFiles(e.dataTransfer.files)
    }

    function onDragOver(e) {
        e.preventDefault()
        setIsDragging(true)
    }

    return (
        <div className="mt-8">
            <label className="block text-[11px] font-bold text-on-surface-variant uppercase tracking-widest mb-3">
                Subida de currículums
            </label>

            <div
                className={`relative overflow-hidden rounded-[2rem] border-2 border-dashed transition-colors duration-300 cursor-pointer p-12 flex flex-col items-center justify-center text-center
                    ${isDragging ? 'border-primary bg-primary/5' : 'border-outline-variant/30 hover:border-outline-variant hover:bg-surface-container-low'}
                `}
                onClick={() => inputRef.current.click()}
                onDragOver={onDragOver}
                onDragLeave={() => setIsDragging(false)}
                onDrop={onDrop}
            >
                {/* Glow effect central */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[200px] h-[200px] bg-white/5 blur-[80px] rounded-full pointer-events-none" />
                
                <div className="relative z-10">
                    <div className="w-14 h-14 bg-surface-container-high rounded-full flex items-center justify-center mb-6 mx-auto shadow-crystal border border-white/5">
                        <span className="material-symbols-outlined text-[28px] text-on-surface">cloud_upload</span>
                    </div>
                    
                    <h3 className="text-xl font-bold text-on-surface mb-2 tracking-tight">Arrastra los PDFs aquí</h3>
                    <p className="text-sm text-on-surface-variant mb-6">o haz clic para seleccionar archivos desde tu equipo</p>
                    
                    <span className="inline-block bg-surface-container rounded-full px-4 py-1.5 text-xs text-on-surface-variant border border-white/5">
                        Máximo 20 archivos (PDF)
                    </span>
                </div>

                <input
                    ref={inputRef}
                    type="file"
                    multiple
                    accept=".pdf"
                    className="hidden"
                    onChange={e => addFiles(e.target.files)}
                />
            </div>

            {files.length > 0 && (
                <div className="mt-6 flex flex-wrap gap-3">
                    {files.map((f, i) => (
                        <div key={i} className="flex items-center gap-2 bg-surface-container rounded-full py-1.5 pl-4 pr-1.5 text-sm border border-white/5 shadow-sm group">
                            <span className="material-symbols-outlined text-[16px] text-on-surface-variant">description</span>
                            <span className="text-on-surface max-w-[200px] truncate">{f.name}</span>
                            <button 
                                onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                                className="w-6 h-6 rounded-full flex items-center justify-center hover:bg-surface-container-high hover:text-red-400 text-on-surface-variant transition-colors ml-1"
                            >
                                <span className="material-symbols-outlined text-[14px]">close</span>
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
})
export default DropZone