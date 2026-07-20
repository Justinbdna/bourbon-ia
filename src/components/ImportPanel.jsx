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
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="font-display text-lg text-slate-900 dark:text-plume">Récupérer des amendements</h2>
          <p className="text-sm text-ink-500 dark:text-ink-300 mt-0.5">
            Importe un fichier JSON, ou colle directement les données.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-black transition-colors"
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
            className="rounded-md border border-ink-300 px-4 py-2 text-sm font-medium text-ink-700 dark:text-plume dark:border-ink-500 dark:hover:bg-ink-800 hover:bg-ink-100 transition-colors"
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
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-black"
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

      {error && (
        <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </p>
      )}
    </div>
  )
}
