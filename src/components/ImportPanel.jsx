import { useRef, useState } from 'react'

/**
 * Permet au personnel de l'Assemblée de récupérer les amendements
 * à traiter : soit en important un fichier JSON, soit en collant
 * un tableau JSON directement. L'import PDF sera branché plus tard
 * (traitement prévu côté backend).
 */
export default function ImportPanel({ onImport }) {
  const fileInputRef = useRef(null)
  const [error, setError] = useState(null)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [pasteValue, setPasteValue] = useState('')

  function handleParsed(json, sourceLabel) {
    const list = Array.isArray(json) ? json : json.amendments
    if (!Array.isArray(list)) {
      setError('Le JSON doit être un tableau d\u2019amendements (ou un objet { "amendments": [...] }).')
      return
    }
    setError(null)
    onImport(list, sourceLabel)
  }

  async function handleFileChange(e) {
    const files = Array.from(e.target.files || [])
    if (!files.length) return

    let allAmendments = []
    let hasError = false

    for (const file of files) {
      try {
        const text = await file.text()
        const json = JSON.parse(text)
        
        // Détection robuste du format de l'Assemblée nationale ou générique
        let list = null
        if (Array.isArray(json)) {
          list = json
        } else if (json.amendments) {
          list = Array.isArray(json.amendments) ? json.amendments : [json.amendments]
        } else if (json.amendements) {
          if (Array.isArray(json.amendements)) {
            list = json.amendements
          } else if (json.amendements.amendement) {
            list = Array.isArray(json.amendements.amendement) ? json.amendements.amendement : [json.amendements.amendement]
          } else {
            list = [json.amendements]
          }
        } else if (json.amendement) {
          list = Array.isArray(json.amendement) ? json.amendement : [json.amendement]
        } else if (json.uid) {
          // Cas où le fichier EST directement l'amendement
          list = [json]
        }

        if (!list) {
          hasError = true
        } else {
          allAmendments = [...allAmendments, ...list]
        }
      } catch {
        hasError = true
      }
    }

    if (allAmendments.length > 0) {
      setError(hasError ? 'Certains fichiers étaient invalides, mais les autres ont été chargés avec succès.' : null)
      onImport(allAmendments, files.length > 1 ? `${files.length} fichiers JSON` : files[0].name)
    } else {
      setError('Impossible de lire les fichiers : Format JSON invalide ou aucun amendement trouvé.')
    }

    e.target.value = ''
  }

  function handlePasteSubmit() {
    try {
      const json = JSON.parse(pasteValue)
      handleParsed(json, 'Collage manuel')
      setPasteValue('')
      setPasteOpen(false)
    } catch {
      setError('JSON invalide, vérifie la syntaxe.')
    }
  }

  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-4 sm:p-5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-base sm:text-lg text-slate-900 dark:text-plume">Récupérer des amendements</h2>
          <p className="text-xs sm:text-sm text-ink-500 dark:text-ink-300 mt-0.5">
            Importe un fichier JSON, ou colle directement les données.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="w-full sm:w-auto rounded-md bg-slate-900 text-white hover:bg-black dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white px-4 py-2 text-xs sm:text-sm font-medium transition-colors text-center"
          >
            Importer un fichier JSON
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => setPasteOpen((v) => !v)}
            className="w-full sm:w-auto rounded-md border border-neutral-300 px-4 py-2 text-xs sm:text-sm font-medium text-slate-700 dark:text-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 dark:hover:border-neutral-600 transition-colors text-center"
          >
            Coller du JSON
          </button>
        </div>
      </div>

      {pasteOpen && (
        <div className="mt-4">
          <textarea
            value={pasteValue}
            onChange={(e) => setPasteValue(e.target.value)}
            rows={6}
            placeholder='[{ "id": "amdt-1", "article": "22", "numero": "1", ... }]'
            className="w-full rounded-md border border-ink-300 p-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={handlePasteSubmit}
              className="rounded-md bg-slate-900 text-white hover:bg-black dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white px-3 py-1.5 text-sm font-medium transition-colors"
            >
              Charger
            </button>
            <button
              type="button"
              onClick={() => { setPasteOpen(false); setPasteValue(''); setError(null) }}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-ink-500 dark:text-ink-300 hover:bg-ink-100 dark:hover:bg-ink-800"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* ── MODALE D'ERREUR 100% NATIVE (zéro Radix) ── */}
      {error && (
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="import-error-title"
        >
          <div className="bg-white dark:bg-[#1A1B22] rounded-xl shadow-2xl border border-red-300 dark:border-red-800 max-w-sm w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <h2 id="import-error-title" className="text-lg font-bold text-red-700 dark:text-red-400">
                Erreur d'importation
              </h2>
            </div>
            <p className="text-sm text-slate-700 dark:text-slate-300 mb-6 leading-relaxed">
              {error}
            </p>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setError(null)}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
