import { useEffect, useRef, useState } from 'react'
import { rechercherDossiers, listerLiasses, chargerLiasse } from '../api/classify'

/**
 * ImportDossierAN — Import direct depuis les données ouvertes de l'Assemblée.
 *
 * Trois étapes, sans fichier à télécharger :
 *   1. chercher un dossier législatif (XVIIe législature) par mots du titre ;
 *      à l'ouverture, les dossiers les plus récemment actifs sont proposés ;
 *   2. choisir la liasse (étape de lecture : commission, séance publique…) ;
 *   3. les amendements sont chargés comme un import JSON (onImport).
 *
 * Source : data.assemblee-nationale.fr, via l'API Tricoteuses (backend).
 */
export default function ImportDossierAN({ onImport, onClose }) {
  const [recherche, setRecherche] = useState('')
  const [dossiers, setDossiers] = useState(null)
  const [dossier, setDossier] = useState(null)
  const [liasses, setLiasses] = useState(null)
  const [chargement, setChargement] = useState('')
  const [erreur, setErreur] = useState(null)
  const abortRef = useRef(null)

  // Une seule requête à la fois : la précédente est annulée.
  async function executer(libelle, action) {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setChargement(libelle)
    setErreur(null)
    try {
      await action(controller.signal)
    } catch (err) {
      if (err.name !== 'AbortError') setErreur(err.message || 'Erreur inconnue.')
    } finally {
      if (abortRef.current === controller) setChargement('')
    }
  }

  function chercher(texte) {
    setDossier(null)
    setLiasses(null)
    executer('Recherche des dossiers…', async (signal) => {
      setDossiers(await rechercherDossiers(texte, { signal }))
    })
  }

  useEffect(() => {
    chercher('')
    return () => abortRef.current?.abort()
  }, [])

  function choisirDossier(d) {
    setDossier(d)
    setLiasses(null)
    executer('Recherche des liasses d’amendements…', async (signal) => {
      setLiasses(await listerLiasses(d.uid, { signal }))
    })
  }

  function importer(liasse) {
    executer(`Chargement de ${liasse.nb} amendements…`, async (signal) => {
      const { amendements, total, tronque } = await chargerLiasse(dossier.uid, liasse.etape, { signal })
      if (tronque) {
        window.alert(`Cette liasse compte ${total} amendements : seuls les ${amendements.length} premiers sont chargés.`)
      }
      onImport(amendements, `${dossier.titre} — ${liasse.libelle}`)
      onClose()
    })
  }

  const champ = 'rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2.5 py-1.5 text-sm text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40'

  return (
    <div className="mt-4 rounded-md border border-ink-200 dark:border-ink-700 bg-slate-50/60 dark:bg-[#12131A]/60 p-3 sm:p-4">
      <form
        role="search"
        aria-label="Rechercher un dossier législatif"
        onSubmit={(e) => { e.preventDefault(); chercher(recherche) }}
        className="flex flex-col sm:flex-row gap-2"
      >
        <input
          type="search"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          placeholder="Titre du texte (ex. : jeux Olympiques, logement…)"
          className={`${champ} flex-1`}
        />
        <button
          type="submit"
          className="rounded-md bg-[#D91227] px-4 py-1.5 text-sm font-medium text-white hover:bg-[#b80f21] transition-colors"
        >
          Rechercher
        </button>
      </form>
      <p className="mt-1.5 text-xs text-ink-500 dark:text-ink-300">
        Dossiers législatifs de la XVIIe législature — données ouvertes de l'Assemblée nationale (via l'API Tricoteuses).
      </p>

      {chargement && (
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300 animate-pulse" aria-live="polite">{chargement}</p>
      )}
      {erreur && (
        <p className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300" role="alert">
          {erreur}
        </p>
      )}

      {/* ── Étape 2 : liasses du dossier choisi ── */}
      {dossier && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => { setDossier(null); setLiasses(null) }}
            className="text-xs font-medium text-[#D91227] hover:underline"
          >
            ← Autres dossiers
          </button>
          <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-plume">{dossier.titre}</p>
          {liasses && liasses.length === 0 && (
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Aucun amendement déposé à l'Assemblée sur ce dossier pour l'instant.</p>
          )}
          {liasses && liasses.length > 0 && (
            <ul className="mt-2 flex flex-col gap-2">
              {liasses.map((l) => (
                <li key={l.etape}>
                  <button
                    type="button"
                    disabled={Boolean(chargement)}
                    onClick={() => importer(l)}
                    className="w-full flex items-center justify-between gap-3 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#0B0C10] px-3 py-2 text-left text-sm hover:border-[#D91227] disabled:opacity-50 transition-colors"
                  >
                    <span className="text-slate-800 dark:text-slate-200">{l.libelle}</span>
                    <span className="shrink-0 text-xs font-semibold text-[#D91227]">Importer {l.nb} amendement{l.nb > 1 ? 's' : ''} →</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── Étape 1 : résultats de recherche ── */}
      {!dossier && dossiers && (
        dossiers.length === 0 ? (
          <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">Aucun dossier ne correspond à cette recherche.</p>
        ) : (
          <ul className="mt-3 max-h-80 overflow-y-auto scroll-thin divide-y divide-ink-200 dark:divide-ink-700 rounded-md border border-ink-200 dark:border-ink-700 bg-white dark:bg-[#0B0C10]">
            {dossiers.map((d) => (
              <li key={d.uid}>
                <button
                  type="button"
                  onClick={() => choisirDossier(d)}
                  className="w-full px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-900/60 transition-colors"
                >
                  <span className="block text-sm text-slate-900 dark:text-plume">{d.titre}</span>
                  <span className="block text-xs text-ink-500 dark:text-ink-300">
                    {[d.type, d.statut, d.date_dernier_acte && `dernier acte le ${d.date_dernier_acte.split('-').reverse().join('/')}`].filter(Boolean).join(' · ')}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  )
}
