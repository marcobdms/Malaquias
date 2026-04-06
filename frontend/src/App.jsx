import { useState, useEffect } from 'react'
import DropZone from './components/DropZone'
import JobForm from './components/JobForm'
import Results from './components/Results'
import Progress from './components/Progress'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import Dashboard from './components/Dashboard'
import Positions from './components/Positions'
import TalentPool from './components/TalentPool'
import Profile from './components/Profile'
import Login from './pages/Login'
import './App.css'
import Confirm from './pages/Confirm'

function App() {
  const [user, setUser] = useState(null)
  const [currentView, setCurrentView] = useState('dashboard')
  const [jobDesc, setJobDesc] = useState('')
  const [categoria, setCategoria] = useState('')
  const [stack, setStack] = useState('')
  const [strictness, setStrictness] = useState('normal')
  const [files, setFiles] = useState([])
  const [results, setResults] = useState(null)
  const [currentOfertaId, setCurrentOfertaId] = useState(null)
  const [progress, setProgress] = useState({ status: 'idle', done: 0, total: 0 })
  const [error, setError] = useState(null)
  const [abortController, setAbortController] = useState(null)
  const [balanceValue, setBalanceValue] = useState(50)

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

  function handleNavigate(view) {
    setCurrentView(view)
  }

  const canAnalyze = jobDesc.trim().length > 20 && files.length > 0
  const loading = progress.status === 'analyzing' || progress.status === 'waking'

  function handleReset() {
    if (abortController) abortController.abort()
    setJobDesc('')
    setCategoria('')
    setStack('')
    setError(null)
    setResults(null)
    setFiles([])
    setCurrentOfertaId(null)
    setProgress({ status: 'idle', done: 0, total: 0 })
    setAbortController(null)
  }

  function handleCancel() {
    if (abortController) {
      abortController.abort()
      setError('Análisis cancelado por el usuario.')
      setProgress(p => ({ ...p, status: 'cancelled' }))
      setAbortController(null)
    }
  }

  async function handleAnalyze() {
    setError(null)
    setResults(null)
    setProgress({ status: 'waking', done: 0, total: files.length })

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      await fetch(`${API_URL}/health`)
    } catch { }

    setProgress({ status: 'analyzing', done: 0, total: files.length })

    const formData = new FormData()
    formData.append('balance', balanceValue / 100)
    formData.append('job_description', jobDesc)
    if (categoria) formData.append('categoria', categoria)
    if (stack) formData.append('stack', stack)
    formData.append('strictness', strictness)
    files.forEach(f => formData.append('cvs', f))

    const controller = new AbortController()
    setAbortController(controller)

    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
        signal: controller.signal
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
            setCurrentOfertaId(payload.oferta_id)
            setProgress({ status: 'done', done: payload.candidates.length, total: payload.candidates.length })
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        // Handled by handleCancel
      } else {
        setError(err.message)
        setProgress(p => ({ ...p, status: 'error' }))
      }
    } finally {
      setAbortController(null)
    }
  }

  if (window.location.pathname === '/confirm') return <Confirm />

  if (!user) return <Login onLogin={handleLogin} />

  return (
    <div className="min-h-screen bg-background text-on-surface font-sans selection:bg-primary/20 selection:text-primary relative flex">
      <Sidebar currentView={currentView} onNavigate={handleNavigate} />
      <Navbar user={user} onLogout={handleLogout} onNavigate={handleNavigate} />

      {/* ── Dashboard View ── */}
      {currentView === 'dashboard' && (
        <main className="flex-1 md:ml-[240px] pt-14 pb-[85px] md:pb-0 min-h-screen w-full">
          <Dashboard onNavigate={handleNavigate} />
        </main>
      )}

      {/* ── Profile View ── */}
      {currentView === 'profile' && (
        <main className="md:ml-[240px] pt-14 pb-[70px] md:pb-0 min-h-screen">
          <Profile user={user} onProfileUpdate={setUser} />
        </main>
      )}

      {/* ── Positions View ── */}
      {currentView === 'positions' && (
        <main className="flex-1 md:ml-[240px] pt-14 pb-[85px] md:pb-0 min-h-screen w-full">
          <Positions />
        </main>
      )}

      {/* ── CV Screener View (Original) ── */}
      {currentView === 'screener' && (
        <main className="md:ml-[240px] pt-14 pb-[70px] md:pb-0 min-h-screen xl:h-[100dvh] flex flex-col xl:flex-row xl:overflow-hidden relative w-full">
          {/* Glow effect sutil */}
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-white/5 blur-[120px] rounded-full pointer-events-none z-0" />

          {/* PANEL IZQUIERDO (Formulario y Subida) */}
          <div className="relative z-10 p-4 md:p-8 xl:flex-1 xl:max-w-3xl flex flex-col xl:overflow-y-auto w-full">
            <div className="mb-8">
              <h2 className="text-3xl font-black text-on-surface tracking-tight mb-2">Cribado de Candidatos</h2>
              <p className="text-on-surface-variant">Analiza y filtra perfiles automáticamente mediante inteligencia artificial.</p>
            </div>

            <div className="crystal-card flex flex-col gap-8 mb-8 relative shrink-0">
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

              <div className="flex flex-col-reverse sm:flex-row items-center justify-between pt-6 mt-2 border-t border-outline-variant/30 gap-4">
                <button
                  className="text-sm font-semibold text-on-surface-variant hover:text-on-surface transition-colors w-full sm:w-auto text-center"
                  onClick={handleReset}
                >
                  Nueva búsqueda
                </button>

                <button
                  className="bg-primary text-on-primary px-6 py-3 rounded-full font-bold shadow-crystal hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2 w-full sm:w-auto"
                  disabled={!canAnalyze || loading}
                  onClick={handleAnalyze}
                >
                  {loading ? (
                    <>
                      <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Procesando...</span>
                    </>
                  ) : progress.status === 'cancelled' ? (
                    <>
                      <span>Analizar de nuevo</span>
                      <span className="material-symbols-outlined text-[18px]">bolt</span>
                    </>
                  ) : (
                    <>
                      <span>Analizar candidatos</span>
                      <span className="material-symbols-outlined text-[18px]">bolt</span>
                    </>
                  )}
                </button>

                {loading && (
                  <button
                    onClick={handleCancel}
                    className="text-xs font-bold text-red-500 hover:text-red-400 uppercase tracking-widest mt-2 sm:mt-0 transition-colors"
                  >
                    Cancelar Proceso
                  </button>
                )}
              </div>

              {progress.status !== 'idle' && (
                <div className="mt-4">
                  <Progress total={progress.total} done={progress.done} status={progress.status} />
                </div>
              )}

              {error && (
                <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl">
                  <p className="text-sm text-red-400 font-medium">{error}</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className={`mt-auto pt-8 hidden ${results ? 'xl:flex' : 'sm:flex'} flex-col sm:flex-row items-start sm:items-center justify-between pointer-events-none shrink-0 border-t border-white/5 gap-4`}>
              <div className="flex gap-8 sm:gap-12">
              </div>
              <p className="text-xs text-on-surface-variant italic">
                Powered by Malaquías v2.5
              </p>
            </div>
          </div>

          {/* PANEL DERECHO (Resultados) */}
          {results ? (
            <div className="xl:flex-1 xl:border-l border-t xl:border-t-0 border-white/5 bg-surface-container-lowest/50 relative xl:overflow-y-auto w-full xl:h-full">
              <div className="p-4 md:p-8 animate-[fade-in_0.5s_ease-out] w-full">
                <Results candidates={results} onReset={handleReset} ofertaId={currentOfertaId} onNavigate={handleNavigate} />
              </div>
            </div>
          ) : (
            <div className="hidden xl:flex xl:flex-1 xl:border-l border-white/5 bg-surface-container-lowest/50 relative xl:overflow-y-auto w-full xl:h-full">
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8 text-on-surface-variant opacity-50">
                <span className="material-symbols-outlined text-6xl mb-4 opacity-50">data_exploration</span>
                <p className="text-lg font-medium">Los resultados del análisis aparecerán aquí</p>
                <p className="text-sm mt-2 max-w-sm">Completa el formulario y sube los currículums a evaluar para comenzar el proceso de matching.</p>
              </div>
            </div>
          )}
        </main>
      )}
    </div>
  )
}

export default App