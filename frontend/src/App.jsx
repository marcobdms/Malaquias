import { useState, useEffect } from 'react'
import DropZone from './components/DropZone'
import JobForm from './components/JobForm'
import Results from './components/Results'
import Progress from './components/Progress'
import Login from './pages/Login'
import './App.css'

function App() {
  const [user, setUser] = useState(null)
  const [jobDesc, setJobDesc] = useState('')
  const [categoria, setCategoria] = useState('')
  const [stack, setStack] = useState('')
  const [strictness, setStrictness] = useState('normal')
  const [files, setFiles] = useState([])
  const [results, setResults] = useState(null)
  const [progress, setProgress] = useState({ status: 'idle', done: 0, total: 0 })
  const [error, setError] = useState(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    const nombre = localStorage.getItem('nombre')
    if (token && nombre) setUser(nombre)
  }, [])

  function handleLogin(nombre) {
    setUser(nombre)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('nombre')
    setUser(null)
    handleReset()
  }

  const canAnalyze = jobDesc.trim().length > 20 && files.length > 0
  const loading = progress.status === 'analyzing'

  function handleReset() {
    setJobDesc('')
    setCategoria('')
    setStack('')
    setFiles([])
    setResults(null)
    setError(null)
    setProgress({ status: 'idle', done: 0, total: 0 })
  }

  async function handleAnalyze() {
    setError(null)
    setResults(null)
    setProgress({ status: 'waking', done: 0, total: files.length })

    try {
      await fetch('https://malaquias.onrender.com/health')
    } catch { }

    setProgress({ status: 'analyzing', done: 0, total: files.length })

    const formData = new FormData()
    formData.append('job_description', jobDesc)
    if (categoria) formData.append('categoria', categoria)
    if (stack) formData.append('stack', stack)
    formData.append('strictness', strictness)
    files.forEach(f => formData.append('cvs', f))

    try {
      const token = localStorage.getItem('token')
      const res = await fetch('https://malaquias.onrender.com/analyze', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      })

      if (res.status === 401) {
        handleLogout()
        return
      }

      if (!res.ok) throw new Error(`Error del servidor: ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = JSON.parse(line.slice(6))

          if (payload.event === 'cv_done') {
            setProgress(p => ({ ...p, done: payload.index }))
          }
          if (payload.event === 'complete') {
            setResults(payload.candidates)
            setProgress({ status: 'done', done: payload.candidates.length, total: payload.candidates.length })
          }
        }
      }
    } catch (err) {
      setError(err.message)
      setProgress(p => ({ ...p, status: 'error' }))
    }
  }

  if (!user) return <Login onLogin={handleLogin} />

  return (
    <div className="app">
      <div className="header">
        <div>
          <h1>Malaquías</h1>
          <p>Screening de CVs con IA · hasta 10 candidatos</p>
        </div>
        <div className="header-right">
          <span className="header-user">{user}</span>
          <button className="btn-logout" onClick={handleLogout}>Salir</button>
        </div>
      </div>

      <JobForm
        value={jobDesc}
        onChange={setJobDesc}
        categoria={categoria}
        setCategoria={setCategoria}
        stack={stack}
        setStack={setStack}
        strictness={strictness}
        setStrictness={setStrictness}
      />
      <DropZone files={files} setFiles={setFiles} />

      <button className="btn-analyze" disabled={!canAnalyze || loading} onClick={handleAnalyze}>
        {loading ? 'Analizando...' : 'Analizar candidatos'}
      </button>

      <button className="btn-reset" onClick={handleReset}>
        Nueva búsqueda
      </button>

      {progress.status !== 'idle' && (
        <Progress total={progress.total} done={progress.done} status={progress.status} />
      )}

      {error && <div className="error-box">{error}</div>}
      {results && <Results candidates={results} />}
    </div>
  )
}

export default App