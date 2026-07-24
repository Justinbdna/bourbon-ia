import { useState, useRef, useEffect } from 'react'
import ImportPanel from './components/ImportPanel'
import AmendmentTable from './components/AmendmentTable'
import AmendmentDetail from './components/AmendmentDetail'
import ClassifyButton from './components/ClassifyButton'
import sampleAmendments from './data/sampleAmendments.json'
import { classifyAmendments, normalizeAmendments } from './api/classify'
import ThemeToggle from './components/ThemeToggle'
import AISettingsModal from './components/AISettingsModal'

export default function App() {
  const [hasEntered, setHasEntered] = useState(false)
  const [amendments, setAmendments] = useState(() => {
    const saved = localStorage.getItem('bourbon_session_amendments')
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch (e) {
        console.error("Failed to parse saved session", e)
      }
    }
    return []
  })

  useEffect(() => {
    localStorage.setItem('bourbon_session_amendments', JSON.stringify(amendments))
  }, [amendments])
  const [sourceLabel, setSourceLabel] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [isClassifying, setIsClassifying] = useState(false)
  const [classifyError, setClassifyError] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isReasoningMode, setIsReasoningMode] = useState(false)
  const [progressInfo, setProgressInfo] = useState(null)
  
  const abortRef = useRef(false)
  const timerRef = useRef(null)
  
  const [aiSettings, setAiSettings] = useState(() => {
    const saved = localStorage.getItem('bourbon_ai_settings')
    if (saved) return JSON.parse(saved)
    return { provider: 'groq', apiKey: '', localUrl: 'http://localhost:1234/v1' }
  })

  function handleSaveSettings(newSettings) {
    setAiSettings(newSettings)
    localStorage.setItem('bourbon_ai_settings', JSON.stringify(newSettings))
  }

  const selected = amendments.find((a) => a.id === selectedId) || null

  async function handleImport(list, label) {
    try {
      const cleanList = await normalizeAmendments(list)
      setAmendments(cleanList)
      setSourceLabel(label)
      setSelectedId(cleanList[0]?.id ?? null)
      setClassifyError(null)
      setWarnings([])
    } catch (err) {
      setClassifyError(err.message)
    }
  }

  function handleLoadSample() {
    handleImport(sampleAmendments, "Jeu de données d'exemple")
  }

  function handleStopClassify() {
    abortRef.current = true
  }

  async function handleClassify() {
    setIsClassifying(true)
    setClassifyError(null)
    setWarnings([])
    abortRef.current = false
    setProgressInfo({ current: 0, total: amendments.length, elapsed: 0 })

    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setProgressInfo(prev => prev ? { ...prev, elapsed: prev.elapsed + 1 } : null)
    }, 1000)

    try {
      await classifyAmendments(amendments, {
        aiSettings,
        isReasoningMode,
        abortRef,
        onProgress: (partialResult, idx, total, warningsList) => {
          setAmendments(prev => {
            const newAmdts = [...prev]
            const targetIndex = newAmdts.findIndex(a => (a.id || a.numero) === partialResult.id)
            if (targetIndex !== -1) {
              newAmdts[targetIndex] = { ...newAmdts[targetIndex], resultat_ia: partialResult }
            }
            return newAmdts
          })
          setProgressInfo(prev => prev ? { ...prev, current: idx, total } : null)
          if (warningsList && warningsList.length > 0) {
            setWarnings([...warningsList])
          }
        }
      })

      // Tri final une fois terminé
      setAmendments(prev => {
        const sorted = [...prev]
        sorted.sort((a, b) => {
          const rangA = a.resultat_ia?.rang ?? Infinity
          const rangB = b.resultat_ia?.rang ?? Infinity
          return rangA - rangB
        })
        return sorted
      })

    } catch (err) {
      console.error('Erreur classement:', err)
      const fallbackAmendments = amendments.map((a, i) => ({
        ...a,
        resultat_ia: a.resultat_ia || {
          id: a.id,
          statut: 'Erreur',
          justification: err.message || 'Erreur inconnue lors du classement.',
          alerte_couleur: 'rouge',
          rang: i + 1
        }
      }))
      setAmendments(fallbackAmendments)
      setClassifyError(err.message || 'Erreur inconnue lors du classement.')
    } finally {
      if (timerRef.current) clearInterval(timerRef.current)
      setIsClassifying(false)
      setProgressInfo(null)
    }
  }

  // Le personnel peut glisser-déposer une ligne s'il juge le classement de
  // l'IA perfectible. Le rang affiché (position dans la liste) s'adapte
  // automatiquement au nouvel ordre.
  function handleReorder(fromIndex, toIndex) {
    setAmendments((prev) => {
      const updated = [...prev]
      const [moved] = updated.splice(fromIndex, 1)
      updated.splice(toIndex, 0, moved)
      return updated
    })
  }

  // Retrait manuel d'un amendement (typiquement : un doublon jugé
  // irrecevable par le personnel après relecture).
  function handleDelete(id) {
    const confirmed = window.confirm(
      "Retirer définitivement cet amendement de la liste de travail ?"
    )
    if (!confirmed) return
    setAmendments((prev) => prev.filter((a) => a.id !== id))
    if (selectedId === id) setSelectedId(null)
  }

  // Export du travail en cours (classement + réordonnancements manuels)
  // pour que le personnel puisse le reprendre plus tard.
  function handleExport() {
    const payload = { amendements: amendments }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `amendements-classes-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  if (hasEntered) {
    return (
      <div className="min-h-screen bg-white dark:bg-[#0B0C10]">
      <header className="bg-[#0B0C10] text-white border-b border-gray-800">
        <div className="max-w-[95%] mx-auto px-6 py-6 flex items-center justify-between flex-wrap gap-3">
          <div>
            <img src="/Bourbon.IA-Final.png" alt="Bourbon.IA Logo" className="h-20 w-auto object-contain" />
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="rounded-md border border-white/30 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10 transition-colors flex items-center gap-2"
            >
              ⚙️ Réglages IA
            </button>
            <ThemeToggle />
            {amendments.length > 0 && (
              <>
                <span className="text-sm text-gray-300/80">
                  {amendments.length} amendement{amendments.length > 1 ? 's' : ''} chargé
                  {amendments.length > 1 ? 's' : ''}
                  {sourceLabel ? ` · ${sourceLabel}` : ''}
                </span>
                <button
                  type="button"
                  onClick={handleExport}
                  className="rounded-md bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 px-3 py-1.5 text-sm font-medium hover:bg-slate-700 dark:hover:bg-slate-300 transition-colors"
                >
                  Exporter en JSON
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-[95%] mx-auto px-6 py-8 space-y-6">
        <ImportPanel onImport={handleImport} />

        {amendments.length === 0 && (
          <div className="text-center">
            <button
              type="button"
              onClick={handleLoadSample}
              className="text-sm text-slate-700 dark:text-slate-300 underline underline-offset-2 hover:text-slate-900 dark:hover:text-slate-100"
            >
              Pas de fichier sous la main ? Charger le jeu de données d'exemple
            </button>
          </div>
        )}

        <ClassifyButton
          disabled={amendments.length === 0}
          loading={isClassifying}
          error={classifyError}
          warnings={warnings}
          onClick={handleClassify}
          onStop={handleStopClassify}
          isReasoningMode={isReasoningMode}
          onToggleReasoning={setIsReasoningMode}
          progressInfo={progressInfo}
        />

        <div className="flex flex-col gap-6 items-start">
          <div className="w-full">
            <AmendmentTable
              amendments={amendments}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onReorder={handleReorder}
              onDelete={handleDelete}
            />
          </div>
          <div className="w-full">
            <AmendmentDetail amendment={selected} onClose={() => setSelectedId(null)} />
          </div>
        </div>

        <AISettingsModal
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          onSave={handleSaveSettings}
          currentSettings={aiSettings}
        />
      </main>

      <footer className="max-w-[95%] mx-auto px-6 pb-8 text-center">
        <p className="text-sm text-neutre dark:text-ink-400 max-w-5xl mx-auto leading-relaxed">
          ⚠️ Note technique - Version Démo : Pour des raisons de logistique et de puissance de serveurs, l'IA de cette démonstration est temporairement déportée sur un Cloud externe sécurisé (Groq/Llama 3.3). L'architecture logicielle de Bourbon.IA reste conçue pour une exécution 100 % souveraine, locale et hors-ligne, garantissant la stricte confidentialité des données.
        </p>
      </footer>
    </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0B0C10] text-plume flex flex-col items-center justify-center p-4 relative">
      <button
        onClick={() => setIsSettingsOpen(true)}
        className="absolute top-4 left-4 z-50 rounded-md border border-ink-600 px-4 py-2 text-sm font-medium text-ink-300 hover:bg-ink-800 transition-colors flex items-center gap-2"
      >
        ⚙️ Réglages IA
      </button>

      <img src="/Bourbon.IA-Final.png" alt="Bourbon.IA Logo" className="h-48 w-auto object-contain animate-pulse mb-10" />
      
      <button
        onClick={() => setHasEntered(true)}
        className="px-10 py-4 bg-bourbon text-white text-lg font-bold rounded-lg shadow-[0_0_25px_rgba(217,18,39,0.5)] hover:bg-red-600 hover:scale-105 transition-all duration-300"
      >
        Entrer dans Bourbon.IA
      </button>

      <div className="absolute bottom-4 left-0 right-0 text-center text-xs text-slate-500 px-6 max-w-2xl mx-auto">
        <p>
          Bourbon.IA est nativement conçu pour être une IA souveraine et 100% locale, garantissant la stricte confidentialité des données législatives. Pour la fluidité de cette démonstration publique, les calculs sont temporairement déportés sur un Cloud sécurisé.
        </p>
      </div>

      <AISettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSave={handleSaveSettings}
        currentSettings={aiSettings}
      />
    </div>
  )
}
