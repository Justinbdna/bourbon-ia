import { useState } from 'react'
import ImportPanel from './components/ImportPanel'
import AmendmentTable from './components/AmendmentTable'
import AmendmentDetail from './components/AmendmentDetail'
import ClassifyButton from './components/ClassifyButton'
import sampleAmendments from './data/sampleAmendments.json'
import { classifyAmendments, normalizeAmendments } from './api/classify'
import ThemeToggle from './components/ThemeToggle'


export default function App() {
  const [hasEntered, setHasEntered] = useState(false)
  const [amendments, setAmendments] = useState([])
  const [sourceLabel, setSourceLabel] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [isClassifying, setIsClassifying] = useState(false)
  const [classifyError, setClassifyError] = useState(null)
  const [warnings, setWarnings] = useState([])

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

  async function handleClassify() {
    setIsClassifying(true)
    setClassifyError(null)
    setWarnings([])

    const CHUNK_SIZE = 5
    const allResults = []
    const allWarnings = []

    try {
      for (let i = 0; i < amendments.length; i += CHUNK_SIZE) {
        const chunk = amendments.slice(i, i + CHUNK_SIZE)

        try {
          const result = await classifyAmendments(chunk)
          allResults.push(...result.classement)
          allWarnings.push(...(result.avertissements || []))
        } catch (chunkErr) {
          allWarnings.push(
            `Erreur sur le lot ${Math.floor(i / CHUNK_SIZE) + 1}: ${chunkErr.message}`
          )
        }

        // Mise à jour progressive : les badges apparaissent au fur et à mesure
        const parId = new Map(allResults.map((c) => [c.id, c]))
        setAmendments((prev) =>
          prev.map((a) => ({
            ...a,
            resultat_ia: parId.get(a.id) || a.resultat_ia || null,
          }))
        )
      }

      setWarnings(allWarnings)
    } catch (err) {
      setClassifyError(err.message || 'Erreur inconnue lors du classement.')
    } finally {
      setIsClassifying(false)
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
      <div className="min-h-screen">
      <header className="bg-marine-950 text-white">
        <div className="max-w-[95%] mx-auto px-6 py-6 flex items-center justify-between flex-wrap gap-3">
          <div>
            <img src="/bourdon_logo.svg" alt="Logo" className="h-24 w-auto" />
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            {amendments.length > 0 && (
              <>
                <span className="text-sm text-marine-100/80">
                  {amendments.length} amendement{amendments.length > 1 ? 's' : ''} chargé
                  {amendments.length > 1 ? 's' : ''}
                  {sourceLabel ? ` · ${sourceLabel}` : ''}
                </span>
                <button
                  type="button"
                  onClick={handleExport}
                  className="rounded-md border border-white/30 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10 transition-colors"
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
              className="text-sm text-marine-700 dark:text-marine-300 underline underline-offset-2 hover:text-marine-900 dark:hover:text-marine-100"
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
    <div className="min-h-screen bg-obsidienne text-plume flex flex-col items-center justify-center p-4">
      <img src="/bourdon_logo.svg" alt="Bourbon.IA Logo" className="h-40 w-auto animate-pulse mb-10" />
      
      <div className="bg-surface rounded-xl p-8 max-w-3xl text-center shadow-2xl mb-10 border border-ink-800">
        <p className="text-neutre text-base md:text-lg leading-relaxed mb-4 font-medium">
          ⚠️ Note sur l'infrastructure de cette démonstration :
        </p>
        <p className="text-neutre text-base md:text-lg leading-relaxed mb-4">
          L'intelligence artificielle utilisée ici est temporairement déportée sur un Cloud sécurisé. Faire tourner un modèle d'IA exige des ressources matérielles intenses. Pour des raisons d'accessibilité publique, nous utilisons une API externe.
        </p>
        <p className="text-neutre text-base md:text-lg leading-relaxed">
          Cependant, l'architecture de Bourbon.IA est nativement conçue pour être souveraine. Il est totalement viable de l'installer et de la relier à une IA 100 % locale hébergée sur vos propres serveurs, garantissant ainsi une confidentialité absolue des données législatives.
        </p>
      </div>

      <button
        onClick={() => setHasEntered(true)}
        className="px-10 py-4 bg-bourbon text-white text-lg font-bold rounded-lg shadow-[0_0_25px_rgba(217,18,39,0.5)] hover:bg-red-600 hover:scale-105 transition-all duration-300"
      >
        Entrer dans Bourbon.IA
      </button>
    </div>
  )
}
