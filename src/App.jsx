import { useState, useRef, useEffect } from 'react'
import ImportPanel from './components/ImportPanel'
import AmendmentTable from './components/AmendmentTable'
import AmendmentDetail from './components/AmendmentDetail'
import LawParticipants from './components/LawParticipants'
import ClassifyButton from './components/ClassifyButton'
import { classifyMechanically, explainConflictsWithAI, analyzeSingleAmendment, normalizeAmendments } from './api/classify'
import ThemeToggle from './components/ThemeToggle'
import AISettingsModal from './components/AISettingsModal'
import ConsentModal from './components/ConsentModal'
import { encrypt, decrypt } from './utils/crypto'
import { compareArticles } from './utils/sanitize'
import { startKeepAlive, stopKeepAlive } from './utils/keepAliveWorker'

const STORAGE_KEY = 'bourbon_session_amendments'

// Fournisseur d'IA au premier lancement (avant tout choix dans ⚙️ Réglages IA) :
//  • poste local (localhost) → IA locale, mode souverain ;
//  • démo publique en ligne → « Groq (Démo) » : le serveur Vercel n'a pas de LLM
//    local et l'anti-SSRF y bloque localhost, l'IA locale y échouerait toujours.
// VITE_AI_PROVIDER_DEFAUT force le choix (ex. « local » sur un intranet de l'AN).
const HOTES_LOCAUX = ['localhost', '127.0.0.1', '[::1]', '::1']

function fournisseurIAParDefaut() {
  const force = import.meta.env.VITE_AI_PROVIDER_DEFAUT
  if (['local', 'groq', 'groq_auto'].includes(force)) return force
  return HOTES_LOCAUX.includes(window.location.hostname) ? 'local' : 'groq_auto'
}

export default function App() {
  const [hasEntered, setHasEntered] = useState(false)
  const [amendments, setAmendments] = useState([])
  const [sourceLabel, setSourceLabel] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [isClassifying, setIsClassifying] = useState(false)
  const [currentAnalyzing, setCurrentAnalyzing] = useState(null)
  const [classifyError, setClassifyError] = useState(null)
  const [warnings, setWarnings] = useState([])
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [progressInfo, setProgressInfo] = useState(null)
  const [lastMechanicalSummary, setLastMechanicalSummary] = useState(null)
  const [analyzingUids, setAnalyzingUids] = useState(() => new Set())
  const [showCloudWarning, setShowCloudWarning] = useState(false)

  // Consentement RGPD (sessionStorage = volatile)
  const [consentAsked, setConsentAsked] = useState(() => sessionStorage.getItem('bourbon_consent') !== null)
  const [consentGiven, setConsentGiven] = useState(() => sessionStorage.getItem('bourbon_consent') === 'true')
  const [showConsentModal, setShowConsentModal] = useState(false)

  const abortRef = useRef(false)
  const abortControllerRef = useRef(null)
  const timerRef = useRef(null)
  const startTimeRef = useRef(null)

  const [aiSettings, setAiSettings] = useState({ provider: fournisseurIAParDefaut(), apiKey: '', localUrl: 'http://localhost:1234/v1' })

  // ─── Restauration des paramètres IA chiffrés ───
  useEffect(() => {
    async function restoreSettings() {
      // 1. Nettoyage de sécurité : supprimer toute ancienne version en clair si elle existe
      const plainSaved = localStorage.getItem('bourbon_ai_settings')
      if (plainSaved) {
        try {
          const parsed = JSON.parse(plainSaved)
          if (parsed && typeof parsed === 'object') {
            setAiSettings(parsed)
          }
        } catch {
          // ignore parsing error
        }
        localStorage.removeItem('bourbon_ai_settings')
      }

      // 2. Déchiffrement sécurisé des paramètres stockés
      const cipher = localStorage.getItem('bourbon_ai_settings_encrypted')
      if (cipher) {
        try {
          const json = await decrypt(cipher)
          const parsed = JSON.parse(json)
          if (parsed && typeof parsed === 'object') {
            const isRemoteHttps = !HOTES_LOCAUX.includes(window.location.hostname) && window.location.protocol === 'https:'
            if (isRemoteHttps && parsed.provider === 'local' && /^http:\/\/(localhost|127\.0\.0\.1)/i.test(parsed.localUrl || 'http://localhost:1234/v1')) {
              parsed.provider = parsed.apiKey ? 'groq' : 'groq_auto'
            } else if (parsed.apiKey && parsed.provider === 'groq_auto') {
              parsed.provider = 'groq'
            }
            setAiSettings(parsed)
          }
        } catch (e) {
          console.warn('Impossible de déchiffrer les paramètres IA stockés.', e)
        }
      }
    }
    restoreSettings()
  }, [])

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
          setAmendments([...parsed].sort(compareArticles))
        }
      } catch (e) {
        console.warn('Impossible de restaurer la session chiffrée (clé expirée ou données corrompues).', e)
        localStorage.removeItem(STORAGE_KEY)
      }
    }
    restore()
  }, [consentGiven])

  // Helper d'écriture sécurisée dans localStorage (tolérant à QuotaExceededError)
  async function persistEncryptedSession(dataToSave) {
    if (!consentGiven || !Array.isArray(dataToSave) || dataToSave.length === 0) return
    try {
      const cipher = await encrypt(JSON.stringify(dataToSave))
      try {
        localStorage.setItem(STORAGE_KEY, cipher)
      } catch (storageErr) {
        console.warn('Quota localStorage dépassé ou écriture refusée (auto-save ignoré) :', storageErr)
      }
    } catch (e) {
      console.warn('Échec de l\'auto-save chiffré.', e)
    }
  }

  // ─── Auto-save chiffré (debounced 3s, neutralisé pendant la boucle unitaire) ───
  useEffect(() => {
    if (!consentGiven || amendments.length === 0 || isClassifying) return
    let cancelled = false
    const debounceTimer = setTimeout(async () => {
      if (!cancelled) {
        await persistEncryptedSession(amendments)
      }
    }, 3000)
    return () => { cancelled = true; clearTimeout(debounceTimer) }
  }, [amendments, consentGiven, isClassifying])

  // ─── Nettoyage au démontage (anti memory leak) ───
  useEffect(() => {
    return () => {
      abortRef.current = true
      if (abortControllerRef.current) abortControllerRef.current.abort()
      if (timerRef.current) clearInterval(timerRef.current)
      stopKeepAlive()
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

  async function handleSaveSettings(newSettings) {
    setAiSettings(newSettings)
    localStorage.removeItem('bourbon_ai_settings') // Sécurité : pas de stockage en clair
    try {
      const cipher = await encrypt(JSON.stringify(newSettings))
      localStorage.setItem('bourbon_ai_settings_encrypted', cipher)
    } catch (e) {
      console.warn('Échec du chiffrement des paramètres IA.', e)
    }
  }

  const selected = amendments.find((a) => a.id === selectedId) || null

  // Dossier législatif du lot courant : on prend la première référence trouvée.
  // Un lot d'amendements porte en pratique sur un seul texte ; l'amendement
  // sélectionné prime s'il en porte une.
  const dossierRefCourant =
    selected?.dossier_ref || amendments.find((a) => a.dossier_ref)?.dossier_ref || null

  // Repli : sans référence de dossier, le backend la reconstruit depuis l'uid
  // d'un amendement réel (un seul appel pour tout le lot).
  const premierUidAmendement =
    amendments.find((a) => String(a.uid || a.id || '').startsWith('AM'))?.uid ||
    amendments.find((a) => String(a.uid || a.id || '').startsWith('AM'))?.id ||
    null

  async function handleImport(list, label) {
    try {
      const normalized = await normalizeAmendments(list)
      const cleanList = Array.isArray(normalized) ? [...normalized].sort(compareArticles) : []
      // Données de test des badges de conformité UE — DÉVELOPPEMENT UNIQUEMENT.
      // `import.meta.env.DEV` vaut false au build : rien n'est servi en production.
      if (import.meta.env.DEV && new URLSearchParams(window.location.search).has('demoUE')) {
        const { appliquerFixturesUE } = await import('./data/euComplianceFixtures.js')
        appliquerFixturesUE(cleanList)
      }
      setAmendments(cleanList)
      setSourceLabel(label)
      setSelectedId(cleanList[0]?.id ?? null)
      setClassifyError(null)
      setWarnings([])
    } catch (err) {
      setClassifyError(err.message)
    }
  }

  async function handleLoadSample() {
    // Chargement à la demande depuis public/sample-amendments.json :
    // n'alourdit jamais le bundle JS compilé par Vite.
    try {
      const response = await fetch('/sample-amendments.json')
      if (!response.ok) {
        throw new Error(`Impossible de charger le jeu d'exemple (HTTP ${response.status})`)
      }
      const sampleAmendments = await response.json()
      await handleImport(sampleAmendments, "Jeu de données d'exemple")
    } catch (err) {
      setClassifyError(err.message)
    }
  }

  function handleStopClassify() {
    abortRef.current = true
    if (abortControllerRef.current) abortControllerRef.current.abort()
  }

  async function handleMechanicalClassify() {
    setIsClassifying(true)
    setClassifyError(null)
    setWarnings([])
    abortRef.current = false

    const controller = new AbortController()
    abortControllerRef.current = controller

    const t0 = Date.now()
    startTimeRef.current = t0
    setProgressInfo({ current: 0, total: amendments.length, elapsed: 0 })

    try {
      const mecResults = await classifyMechanically(amendments, {
        signal: controller.signal,
      })
      const elapsedMs = Date.now() - t0
      const rawSec = (elapsedMs / 1000).toFixed(1)
      const displaySec = rawSec === '0.0' ? '0.1' : rawSec

      setAmendments(mecResults)
      setLastMechanicalSummary({
        elapsedSec: displaySec,
        dureeMs: mecResults._meta?.duree_ms ?? elapsedMs,
        statistiques: mecResults._meta?.statistiques || null,
      })
      await persistEncryptedSession(mecResults)
    } catch (err) {
      if (err.name === 'AbortError') {
        setWarnings(prev => [...prev, "Classement mécanique annulé."])
      } else {
        console.error('Erreur classement mécanique:', err)
        setClassifyError(err.message || 'Erreur inconnue lors du classement mécanique.')
      }
    } finally {
      startTimeRef.current = null
      abortControllerRef.current = null
      setIsClassifying(false)
      setProgressInfo(null)
    }
  }

  async function handleAnalyzeSingle(targetUid) {
    if (!targetUid) return
    const target = amendments.find((a) => a.id === targetUid || a.uid === targetUid)
    const uid = target?.uid || target?.id || targetUid
    setClassifyError(null)
    setAnalyzingUids((prev) => new Set(prev).add(uid).add(targetUid))
    try {
      const resIa = await analyzeSingleAmendment(uid, amendments, aiSettings)
      setAmendments((prev) => {
        const next = prev.map((a) => {
          if (a.id !== targetUid && a.uid !== targetUid && a.id !== uid && a.uid !== uid) return a
          const newJustif = resIa?.justification || resIa?.analyse_intention || a.justification
          const preservedStatut = a.resultat_ia?.statut || a.statut || resIa?.statut
          const preservedGid = a.groupe_conflit_id ?? a.resultat_ia?.groupe_conflit_id ?? resIa?.groupe_conflit_id
          const preservedCible = a.cible_numero ?? a.resultat_ia?.cible_numero ?? resIa?.cible_numero
          const preservedGroupe = a.resultat_ia?.groupe || resIa?.groupe
          return {
            ...a,
            statut: preservedStatut,
            groupe_conflit_id: preservedGid,
            cible_numero: preservedCible,
            justification: newJustif,
            explication_ia: true,
            resultat_ia: {
              ...a.resultat_ia,
              ...resIa,
              statut: preservedStatut,
              groupe_conflit_id: preservedGid,
              cible_numero: preservedCible,
              groupe: preservedGroupe,
              justification: newJustif,
              explication_ia: true,
            },
          }
        })
        persistEncryptedSession(next)
        return next
      })
    } catch (err) {
      console.error(`Erreur analyse unitaire sur ${targetUid}:`, err)
      setClassifyError(err.message || `Impossible d'analyser l'amendement ${targetUid}.`)
    } finally {
      setAnalyzingUids((prev) => {
        const next = new Set(prev)
        next.delete(uid)
        next.delete(targetUid)
        return next
      })
    }
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

    const controller = new AbortController()
    abortControllerRef.current = controller

    const nbConflictsInitial = amendments.filter(
      (a) => (a.resultat_ia?.statut || a.statut) === 'Discussion commune'
    ).length
    const totalToExplain = nbConflictsInitial > 0 ? nbConflictsInitial : amendments.length

    startTimeRef.current = Date.now()
    setProgressInfo({ current: 0, total: totalToExplain, elapsed: 0 })

    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      if (startTimeRef.current) {
        const tempsEcoule = Math.floor((Date.now() - startTimeRef.current) / 1000)
        setProgressInfo(prev => prev ? { ...prev, elapsed: tempsEcoule } : null)
      }
    }, 500)

    // Neutralisation de l'App Nap et de la mise en veille d'arrière-plan de Safari (uniquement pendant l'IA)
    startKeepAlive(() => {
      if (startTimeRef.current) {
        const tempsEcoule = Math.floor((Date.now() - startTimeRef.current) / 1000)
        setProgressInfo(prev => prev ? { ...prev, elapsed: tempsEcoule } : null)
      }
    })

    try {
      setCurrentAnalyzing({ uid: '', numero: '...', index: 0, total: totalToExplain })
      const enrichedResults = await explainConflictsWithAI(amendments, {
        aiSettings,
        signal: controller.signal,
        onMechanical: (mecResults) => {
          setAmendments(mecResults)
        },
        onProgress: (partialResult, idx, total, snapshot) => {
          if (partialResult) {
            setCurrentAnalyzing({
              uid: partialResult.id,
              numero: partialResult.id?.split('-').pop() || '?',
              index: idx,
              total,
            })
          }
          const tempsEcoule = startTimeRef.current ? Math.floor((Date.now() - startTimeRef.current) / 1000) : 0
          setProgressInfo(prev => prev ? { ...prev, current: idx, total, elapsed: tempsEcoule } : null)
          if (Array.isArray(snapshot) && snapshot.length > 0) {
            setAmendments(snapshot)
            if (idx > 0 && (idx % 25 === 0 || idx === total)) {
              persistEncryptedSession(snapshot)
            }
          }
        },
      })

      setAmendments(enrichedResults)
      await persistEncryptedSession(enrichedResults)
      setCurrentAnalyzing(null)

    } catch (err) {
      if (err.name === 'AbortError') {
        setWarnings(prev => [...prev, "Explication IA annulée par l'utilisateur."])
      } else {
        console.error('Erreur explication IA:', err)
        setClassifyError(err.message || "Erreur inconnue lors de l'explication des conflits.")
      }
    } finally {
      stopKeepAlive()
      if (timerRef.current) clearInterval(timerRef.current)
      startTimeRef.current = null
      abortControllerRef.current = null
      setIsClassifying(false)
      setProgressInfo(null)
      setCurrentAnalyzing(null)
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

  function handleDeleteDoublons(ids) {
    const nb = ids.length
    const confirmed = window.confirm(
      `Retirer ${nb} doublon${nb > 1 ? 's' : ''} (même texte, même auteur, même commission) de la liste de travail ?\n` +
      "L'amendement d'origine de chaque auteur est conservé."
    )
    if (!confirmed) return
    const aRetirer = new Set(ids)
    setAmendments((prev) => prev.filter((a) => !aRetirer.has(a.id)))
    if (aRetirer.has(selectedId)) setSelectedId(null)
  }

  function handleExport() {
    const fileName = window.prompt("Comment souhaitez-vous nommer ce fichier d'export ?", "amendements_export")
    if (fileName === null) return
    const finalName = fileName.trim() || "amendements_export"

    const payload = { amendements: amendments }
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${finalName}.json`
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
    sovereigntyBadge = (
      <span className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-400 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
        IA Locale (Souveraine)
      </span>
    )
  } else if (aiSettings.provider === 'groq') {
    sovereigntyBadge = (
      <span className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-400 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></span>
        Clé API (Personnalisée)
      </span>
    )
  } else {
    sovereigntyBadge = (
      <span className="bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-400 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors">
        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
        Groq (Démo non-souveraine)
      </span>
    )
  }

  if (hasEntered) {
    return (
      <div className="min-h-screen bg-white dark:bg-[#0B0C10]">
      <header className="bg-[#F8F9FA] dark:bg-[#1A1B22] text-slate-800 dark:text-white border-b border-neutral-200/80 dark:border-gray-800 transition-colors">
        <div className="max-w-[95%] mx-auto px-4 sm:px-6 py-4 sm:py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Logo seul à gauche (double source light/dark) */}
          <img src="/bourbon-logo-black.svg" alt="Bourbon.IA Logo" className="h-16 sm:h-24 w-auto object-contain shrink-0 dark:hidden block" />
          <img src="/bourbon-logo-white.svg" alt="Bourbon.IA Logo" className="h-16 sm:h-24 w-auto object-contain shrink-0 hidden dark:block" />

          {/* Tout le bloc d'actions et le badge à droite avec ml-auto */}
          <div className="w-full sm:w-auto flex flex-col sm:flex-row items-center justify-center sm:justify-end gap-2 sm:gap-4 flex-wrap">
            {sovereigntyBadge}
            
            <div className="flex items-center gap-2 flex-wrap justify-center">
              {amendments.length > 0 && (
                <button
                  type="button"
                  onClick={handleResetSession}
                  className="bg-white dark:bg-neutral-800/50 hover:bg-rose-50 dark:hover:bg-rose-950/50 border border-neutral-200 dark:border-neutral-700/50 hover:border-rose-200 dark:hover:border-rose-500/50 text-slate-700 dark:text-neutral-300 hover:text-rose-600 dark:hover:text-rose-400 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center gap-1.5"
                  title="Efface l'ensemble des amendements et réinitialise le classement."
                >
                  🗑️ Réinitialiser
                </button>
              )}

              <button
                onClick={() => setIsSettingsOpen(true)}
                className="bg-white dark:bg-neutral-800/50 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 border border-neutral-200 dark:border-neutral-700/50 text-slate-700 dark:text-neutral-300 hover:text-slate-900 dark:hover:text-white px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center gap-1.5 shrink-0"
                title="Configure l'endpoint local (LM Studio) ou la clé API Cloud."
              >
                ⚙️ Réglages IA
              </button>
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[95%] mx-auto px-3 sm:px-6 py-4 sm:py-8 space-y-6">
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
          onMechanicalClick={handleMechanicalClassify}
          onLlmClick={handleClassify}
          onStop={handleStopClassify}
          progressInfo={progressInfo}
          mechanicalSummary={lastMechanicalSummary}
        />

        {/* ── État d'analyse en cours (V2) ── */}
        {isClassifying && (
          <div className="flex items-center gap-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3 animate-pulse">
            <span className="text-lg">🧠</span>
            <p className="text-sm text-blue-800 dark:text-blue-300 font-medium">
              Analyse IA en cours{sourceLabel ? ` (${sourceLabel})` : ''}
              {currentAnalyzing && currentAnalyzing.total > 0
                ? ` — ${currentAnalyzing.index}/${currentAnalyzing.total} (${currentAnalyzing.numero})`
                : '...'}
            </p>
          </div>
        )}

        <div className="flex flex-col gap-6 items-start">
          <div className="w-full">
            <AmendmentTable
              amendments={amendments}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onReorder={handleReorder}
              onDelete={handleDelete}
              onDeleteDoublons={handleDeleteDoublons}
              isClassifying={isClassifying}
              analyzingUids={analyzingUids}
              onExportJson={handleExport}
              onAnalyzeSingle={handleAnalyzeSingle}
            />
          </div>
          <div className="w-full">
            <AmendmentDetail
              amendment={selected}
              onClose={() => setSelectedId(null)}
              isLoading={isClassifying && selected && !selected.resultat_ia}
              aiSettings={aiSettings}
            />
          </div>

          {/* Participants du texte de loi : nom, prénom, groupe politique.
              Granularité au dossier (200+ personnes) → panneau dédié et non
              une colonne du tableau d'amendements. */}
          {(dossierRefCourant || premierUidAmendement) && (
            <div className="w-full">
              <LawParticipants
                dossierRef={dossierRefCourant}
                amendementUid={premierUidAmendement}
                titre={amendments.find((a) => a.title)?.title}
              />
            </div>
          )}
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
          💡 Note technique : Par défaut, cette démonstration publique utilise le mode Groq (GPT-OSS 20B) pour la fluidité web. L'application reste 100 % conçue pour une exécution souveraine, locale et hors-ligne (sélectionnable dans les ⚙️ Réglages IA).
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

      <img src="/bourbon-logo-white.svg" alt="Bourbon.IA Logo" className="h-48 w-auto object-contain animate-pulse mb-10" />
      
      <button
        onClick={() => setHasEntered(true)}
        className="px-10 py-4 bg-bourbon text-white text-lg font-bold rounded-lg shadow-[0_0_25px_rgba(217,18,39,0.5)] hover:bg-red-600 hover:scale-105 transition-all duration-300"
      >
        Entrer dans Bourbon.IA
      </button>

      <div className="absolute bottom-4 left-0 right-0 text-center text-xs text-slate-500 px-6 max-w-2xl mx-auto">
        <p>
          💡 Note technique : Par défaut, cette démonstration publique utilise le mode Groq (GPT-OSS 20B) pour la fluidité web. L'application reste 100 % conçue pour une exécution souveraine, locale et hors-ligne (sélectionnable dans les ⚙️ Réglages IA).
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
