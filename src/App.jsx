import { useState, useRef, useEffect, useCallback } from 'react'
import ImportPanel from './components/ImportPanel'
import AmendmentTable from './components/AmendmentTable'
import AmendmentDetail from './components/AmendmentDetail'
import ClassifyButton from './components/ClassifyButton'
import sampleAmendments from './data/sampleAmendments.json'
import { classifyAmendments, normalizeAmendments } from './api/classify'
import ThemeToggle from './components/ThemeToggle'
import AISettingsModal from './components/AISettingsModal'
import ConsentModal from './components/ConsentModal'
import { encrypt, decrypt } from './utils/crypto'

const STORAGE_KEY = 'bourbon_session_amendments'

export default function App() {
  const [hasEntered, setHasEntered] = useState(false)
  const [amendments, setAmendments] = useState([])
  const [sourceLabel, setSourceLabel] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [isClassifying, setIsClassifying] = useState(false)
  const [classifyError, setClassifyError] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isReasoningMode, setIsReasoningMode] = useState(false)
  const [progressInfo, setProgressInfo] = useState(null)
  const [showCloudWarning, setShowCloudWarning] = useState(false)

  // Consentement RGPD (sessionStorage = volatile)
  const [consentAsked, setConsentAsked] = useState(() => sessionStorage.getItem('bourbon_consent') !== null)
  const [consentGiven, setConsentGiven] = useState(() => sessionStorage.getItem('bourbon_consent') === 'true')
  const [showConsentModal, setShowConsentModal] = useState(false)

  const abortRef = useRef(false)
  const abortControllerRef = useRef(null)
  const timerRef = useRef(null)

  // Provider LOCAL par défaut (souveraineté)
  const [aiSettings, setAiSettings] = useState(() => {
    const saved = localStorage.getItem('bourbon_ai_settings')
    if (saved) return JSON.parse(saved)
    return { provider: 'local', apiKey: '', localUrl: 'http://localhost:1234/v1' }
  })

  // ─── Restauration de session chiffrée ───
  useEffect(() => {
    if (!consentGiven) return
    async function restore() {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (!stored) return
      try {
        const json = await decrypt(stored)
        const parsed = JSON.parse(json)
        if (Array.isArray(parsed) && parsed.length > 0) {
          setAmendments(parsed)
        }
      } catch (e) {
        console.warn('Impossible de restaurer la session chiffrée (clé expirée ou données corrompues).', e)
        localStorage.removeItem(STORAGE_KEY)
      }
    }
    restore()
  }, [consentGiven])

  // ─── Auto-save chiffré ───
  useEffect(() => {
    if (!consentGiven || amendments.length === 0) return
    let cancelled = false
    async function save() {
      try {
        const cipher = await encrypt(JSON.stringify(amendments))
        if (!cancelled) {
          localStorage.setItem(STORAGE_KEY, cipher)
        }
      } catch (e) {
        console.warn('Échec de l\'auto-save chiffré.', e)
      }
    }
    save()
    return () => { cancelled = true }
  }, [amendments, consentGiven])

  // ─── Nettoyage au démontage (anti memory leak) ───
  useEffect(() => {
    return () => {
      abortRef.current = true
      if (abortControllerRef.current) abortControllerRef.current.abort()
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  // ─── Séquence d'apparition RGPD (cooldown de 3s après l'entrée dans l'application) ───
  useEffect(() => {
    let timer = null
    if (hasEntered && !consentAsked) {
      timer = setTimeout(() => {
        setShowConsentModal(true)
      }, 3000)
    }
    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [hasEntered, consentAsked])

  function handleConsentAccept() {
    sessionStorage.setItem('bourbon_consent', 'true')
    setConsentGiven(true)
    setConsentAsked(true)
    setShowConsentModal(false)
  }

  function handleConsentRefuse() {
    sessionStorage.setItem('bourbon_consent', 'false')
    setConsentGiven(false)
    setConsentAsked(true)
    setShowConsentModal(false)
    localStorage.removeItem(STORAGE_KEY)
  }

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
    if (abortControllerRef.current) abortControllerRef.current.abort()
  }

  async function handleClassify() {
    // ── MODALE CLOUD BLOQUANTE ──
    if (aiSettings.provider !== 'local') {
      setShowCloudWarning(true)
      return
    }
    executeClassify()
  }

  function handleCloudConfirm() {
    setShowCloudWarning(false)
    executeClassify()
  }

  async function executeClassify() {
    setIsClassifying(true)
    setClassifyError(null)
    setWarnings([])
    abortRef.current = false

    // Nettoyer les anciens résultats avant de démarrer
    setAmendments(prev => prev.map(a => {
      const copy = { ...a }
      delete copy.resultat_ia
      return copy
    }))

    const controller = new AbortController()
    abortControllerRef.current = controller

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
        signal: controller.signal,
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
      if (err.name === 'AbortError') {
        setWarnings(prev => [...prev, "Classement annulé par l'utilisateur."])
      } else {
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
      }
    } finally {
      if (timerRef.current) clearInterval(timerRef.current)
      abortControllerRef.current = null
      setIsClassifying(false)
      setProgressInfo(null)
    }
  }

  function handleReorder(fromIndex, toIndex) {
    setAmendments((prev) => {
      const updated = [...prev]
      const [moved] = updated.splice(fromIndex, 1)
      updated.splice(toIndex, 0, moved)
      return updated
    })
  }

  function handleDelete(id) {
    const confirmed = window.confirm(
      "Retirer définitivement cet amendement de la liste de travail ?"
    )
    if (!confirmed) return
    setAmendments((prev) => prev.filter((a) => a.id !== id))
    if (selectedId === id) setSelectedId(null)
  }

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

  function handleResetSession() {
    if (window.confirm("Voulez-vous vraiment réinitialiser la session ? Toutes les données non exportées seront perdues.")) {
      setAmendments([])
      setSelectedId(null)
      localStorage.removeItem(STORAGE_KEY)
      setSourceLabel(null)
    }
  }

  // ─── Badge de souveraineté (SANS EMOJI, texte brut) ───
  let sovereigntyBadge = null
  if (aiSettings.provider === 'local') {
    sovereigntyBadge = <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-900/40 border border-emerald-600/50 px-3 py-1 text-xs font-bold text-emerald-300">IA Locale (Souveraine)</span>
  } else if (aiSettings.provider === 'groq') {
    sovereigntyBadge = <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-900/40 border border-amber-600/50 px-3 py-1 text-xs font-bold text-amber-300">Clé API (Personnalisée)</span>
  } else {
    sovereigntyBadge = <span className="inline-flex items-center gap-1.5 rounded-full bg-red-900/40 border border-red-600/50 px-3 py-1 text-xs font-bold text-red-300">Groq (Démo non-souveraine)</span>
  }

  if (hasEntered) {
    return (
      <div className="min-h-screen bg-white dark:bg-[#0B0C10]">
      <header className="bg-[#0B0C10] text-white border-b border-gray-800">
        <div className="max-w-[95%] mx-auto px-6 py-6 flex items-center justify-between gap-4 flex-wrap">
          {/* Logo seul à gauche */}
          <img src="/Bourbon.IA-Final.png" alt="Bourbon.IA Logo" className="h-20 w-auto object-contain shrink-0" />

          {/* Tout le bloc d'actions et le badge à droite avec ml-auto */}
          <div className="ml-auto flex items-center gap-3 flex-wrap">
            {sovereigntyBadge}
            
            {amendments.length > 0 && (
              <button
                type="button"
                onClick={handleResetSession}
                className="rounded-md bg-red-600 text-white px-3 py-1.5 text-sm font-medium hover:bg-red-700 transition-colors"
                title="Réinitialiser la session"
              >
                🗑️ Reset
              </button>
            )}

            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsSettingsOpen(true)}
                className="rounded-md border border-white/30 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10 transition-colors flex items-center gap-2 shrink-0"
              >
                ⚙️ Réglages IA
              </button>
              <ThemeToggle />
            </div>
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
              isClassifying={isClassifying}
              onExportJson={handleExport}
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

      {/* ── MODALE D'ALERTE CLOUD BLOQUANTE (100% natif, zéro Radix) ── */}
      {showCloudWarning && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cloud-warning-title"
        >
          <div className="bg-white dark:bg-[#1A1B22] rounded-xl shadow-2xl border border-red-300 dark:border-red-800 max-w-lg w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <h2 id="cloud-warning-title" className="text-lg font-bold text-red-700 dark:text-red-400">
                Alerte Souveraineté — Envoi Cloud
              </h2>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-5">
              <p className="text-sm text-red-800 dark:text-red-200 leading-relaxed">
                <strong>Attention :</strong> Vos données d'amendements vont quitter votre poste pour être envoyées à un serveur extérieur (<strong>Groq / États-Unis</strong>), hors de l'Union européenne.
              </p>
              <p className="text-sm text-red-800 dark:text-red-200 mt-2">
                Cette action est <strong>incompatible avec le mode souverain</strong> et la confidentialité des textes non publiés.
              </p>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-5">
              Pour un usage confidentiel, ouvrez les ⚙️ Réglages IA et sélectionnez "IA Locale".
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowCloudWarning(false)}
                className="rounded-md border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={handleCloudConfirm}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors"
              >
                Je confirme l'envoi vers le Cloud
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODALE CONSENTEMENT RGPD ── */}
      <ConsentModal
        isOpen={showConsentModal}
        onAccept={handleConsentAccept}
        onRefuse={handleConsentRefuse}
      />
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
