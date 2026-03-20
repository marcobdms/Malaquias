import { useRef } from 'react'

export default function DropZone({ files, setFiles }) {
    const inputRef = useRef()

    function addFiles(newFiles) {
        const pdfs = Array.from(newFiles).filter(f => f.name.endsWith('.pdf'))
        setFiles(prev => [...prev, ...pdfs].slice(0, 10))
    }

    function removeFile(index) {
        setFiles(prev => prev.filter((_, i) => i !== index))
    }

    function onDrop(e) {
        e.preventDefault()
        addFiles(e.dataTransfer.files)
    }

    return (
        <div className="card">
            <label>CVs en PDF · máximo 10</label>

            <div
                className="drop-zone"
                onClick={() => inputRef.current.click()}
                onDragOver={e => e.preventDefault()}
                onDrop={onDrop}
            >
                <p className="drop-title">Arrastra los PDFs aquí</p>
                <p className="drop-sub">o haz clic para seleccionar</p>
                <input
                    ref={inputRef}
                    type="file"
                    multiple
                    accept=".pdf"
                    style={{ display: 'none' }}
                    onChange={e => addFiles(e.target.files)}
                />
            </div>

            {files.length > 0 && (
                <ul className="file-list">
                    {files.map((f, i) => (
                        <li key={i} className="file-item">
                            <span>{f.name}</span>
                            <button onClick={() => removeFile(i)}>×</button>
                        </li>
                    ))}
                </ul>
            )}

            {files.length > 0 && (
                <p className="file-count">{files.length} archivo{files.length > 1 ? 's' : ''} {files.length === 10 && '· límite alcanzado'}</p>
            )}
        </div>
    )
}