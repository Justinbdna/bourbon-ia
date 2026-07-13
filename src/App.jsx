import { useState } from 'react'
import ImportPanel from './components/ImportPanel'
import AmendmentTable from './components/AmendmentTable'
import AmendmentDetail from './components/AmendmentDetail'
import ClassifyButton from './components/ClassifyButton'
import sampleAmendments from './data/sampleAmendments.json'
import { classifyAmendments } from './api/classify'

export default function App() {
  const [amendments, setAmendments] = useState([])
  const [sourceLabel, setSourceLabel] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [isClassifying, setIsClassifying] = useState(false)
  const [classifyError, setClassifyError] = useState(null)
  const [warnings, setWarnings] = useState([])

  const selected = amendments.find((a) => a.id === selectedId) || null

  function handleImport(list, label) {
    setAmendments(list)
    setSourceLabel(label)
    setSelectedId(list[0]?.id ?? null)
    setClassifyError(null)
    setWarnings([])
  }

  function handleLoadSample() {
    handleImport(sampleAmendments, "Jeu de données d'exemple")
  }

  async function handleClassify() {
    setIsClassifying(true)
    setClassifyError(null)
    setWarnings([])

    try {
      const result = await classifyAmendments(amendments)
      const parId = new Map(result.classement.map((c) => [c.id, c]))

      const misAJour = amendments.map((a) => ({
        ...a,
        resultat_ia: parId.get(a.id) || null,
      }))

      // Trie par rang d'examen renvoyé par l'IA ; les amendements non
      // classés (absents de la réponse) restent en fin de liste.
      misAJour.sort((a, b) => {
        const rangA = a.resultat_ia?.rang ?? Infinity
        const rangB = b.resultat_ia?.rang ?? Infinity
        return rangA - rangB
      })

      setAmendments(misAJour)
      setWarnings(result.avertissements || [])
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

  return (
    <div className="min-h-screen">
      <header className="bg-marine-950 text-white">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between flex-wrap gap-3">
          <div>
            <img src="/bourdon_logo.svg" alt="Logo" className="h-10 w-auto" /> test
          </div>
          {amendments.length > 0 && (
            <div className="flex items-center gap-4">
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
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <ImportPanel onImport={handleImport} />

        {amendments.length === 0 && (
          <div className="text-center">
            <button
              type="button"
              onClick={handleLoadSample}
              className="text-sm text-marine-700 underline underline-offset-2 hover:text-marine-900"
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

        <div className="grid grid-cols-1 lg:grid-cols-6 gap-6 items-start">
          <div className="lg:col-span-4">
            <AmendmentTable
              amendments={amendments}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onReorder={handleReorder}
              onDelete={handleDelete}
            />
          </div>
          <div className="lg:col-span-2 lg:sticky lg:top-6">
            <AmendmentDetail amendment={selected} onClose={() => setSelectedId(null)} />
          </div>
        </div>
      </main>
    </div>
  )
}
