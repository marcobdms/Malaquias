import { useState } from 'react'
import DropZone from './components/DropZone'
import JobForm from './components/JobForm'
import Results from './components/Results'
import './App.css'

function App() {
  const [jobDesc, setJobDesc] = useState('')
  const [categoria, setCategoria] = useState('')
  const [stack, setStack] = useState('')
  const [files, setFiles] = useState([])
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const canAnalyze = jobDesc.trim().length > 20 && files.length > 0

  function handleReset() {
    setJobDesc('')
    setCategoria('')
    setStack('')
    setFiles([])
    setResults(null)
    setError(null)
  }

  async function handleAnalyze() {
    setLoading(true)
    setError(null)
    setResults(null)

    const formData = new FormData()
    formData.append('job_description', jobDesc)
    if (categoria) formData.append('categoria', categoria)
    if (stack) formData.append('stack', stack)
    files.forEach(f => formData.append('cvs', f))

    try {
      const res = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        body: formData
      })
      if (!res.ok) throw new Error(`Error del servidor: ${res.status}`)
      const data = await res.json()
      setResults(data.candidates)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <div className="header">
        <h1>Malaquías</h1>
        <p>Screening de CVs con IA · hasta 10 candidatos</p>
      </div>

      <JobForm
        value={jobDesc}
        onChange={setJobDesc}
        categoria={categoria}
        setCategoria={setCategoria}
        stack={stack}
        setStack={setStack}
      />
      <DropZone files={files} setFiles={setFiles} />

      <button
        className="btn-analyze"
        disabled={!canAnalyze || loading}
        onClick={handleAnalyze}
      >
        {loading ? 'Analizando...' : 'Analizar candidatos'}
      </button>

      <button
        className="btn-reset"
        onClick={handleReset}
      >
        Nueva búsqueda
      </button>

      {error && <div className="error-box">{error}</div>}
      {results && <Results candidates={results} />}
    </div>
  )
}

export default App