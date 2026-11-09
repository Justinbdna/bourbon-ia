import { useEffect, useState } from 'react'
import { SERVEUR_LOCAL, choisirServeur, modeServeur, testerServeur } from '../api/serveur'

/**
 * ServeurBourbon — Où s'exécute le traitement des amendements (⚙️ Réglages IA).
 *
 *   • En ligne : le serveur de la démo (Vercel). Rien à installer.
 *   • Sur cet ordinateur : un serveur Bourbon.IA lancé sur le poste
 *     (http://localhost:8000). Les amendements ne passent plus par le serveur
 *     en ligne et les grosses liasses ne sont plus limitées par Vercel.
 *
 * Le choix s'applique immédiatement et est mémorisé dans le navigateur.
 */
export default function ServeurBourbon() {
  const [mode, setMode] = useState(modeServeur)
  const [etat, setEtat] = useState(null) // null | 'test' | 'ok' | 'ko'

  useEffect(() => {
    if (mode !== 'local') return
    let actif = true
    setEtat('test')
    testerServeur(SERVEUR_LOCAL).then((ok) => { if (actif) setEtat(ok ? 'ok' : 'ko') })
    return () => { actif = false }
  }, [mode])

  function choisir(nouveau) {
    choisirServeur(nouveau)
    setMode(nouveau)
    setEtat(null)
  }

  function retester() {
    setEtat('test')
    testerServeur(SERVEUR_LOCAL).then((ok) => setEtat(ok ? 'ok' : 'ko'))
  }

  const bouton = (actif) =>
    `w-full py-2 px-2 rounded-md border font-medium text-xs sm:text-sm text-center transition-colors ${
      actif
        ? 'bg-slate-100 border-slate-500 text-slate-900 dark:bg-slate-900/50 dark:border-slate-400 dark:text-plume shadow-sm'
        : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
    }`

  return (
    <section aria-labelledby="serveur-titre" className="space-y-3">
      <div>
        <h3 id="serveur-titre" className="text-sm font-semibold text-slate-900 dark:text-plume">Serveur Bourbon.IA</h3>
        <p className="text-xs text-ink-500 dark:text-ink-300 mt-0.5">
          Où sont traités les amendements (import, tri, envoi à l'IA).
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button type="button" aria-pressed={mode === 'en_ligne'} onClick={() => choisir('en_ligne')} className={bouton(mode === 'en_ligne')}>
          🌐 En ligne
        </button>
        <button type="button" aria-pressed={mode === 'local'} onClick={() => choisir('local')} className={bouton(mode === 'local')}>
          💻 Sur cet ordinateur
        </button>
      </div>

      {mode === 'en_ligne' && (
        <p className="text-xs text-ink-500 dark:text-ink-300">
          Serveur de la démo, rien à installer. Les amendements transitent par ce serveur (hébergé par Vercel).
        </p>
      )}

      {mode === 'local' && (
        <div className="rounded-md border border-ink-200 dark:border-ink-700 bg-slate-50 dark:bg-obsidienne p-3 space-y-2 text-xs text-slate-700 dark:text-slate-300">
          <p className="flex items-center justify-between gap-2">
            <span>
              Adresse : <code className="font-mono">{SERVEUR_LOCAL}</code>
            </span>
            <span aria-live="polite" className="font-medium">
              {etat === 'test' && 'Test en cours…'}
              {etat === 'ok' && <span className="text-emerald-700 dark:text-emerald-400">✓ Serveur local connecté</span>}
              {etat === 'ko' && <span className="text-red-700 dark:text-red-400">✗ Aucun serveur détecté</span>}
            </span>
          </p>
          {etat === 'ko' && (
            <>
              <p>Pour lancer le serveur sur ce poste (Python 3.9+), dans un terminal :</p>
              <pre className="overflow-x-auto rounded bg-slate-900 text-slate-100 p-2 font-mono text-[11px] leading-relaxed">{`git clone https://github.com/Justinbdna/bourbon-ia.git
cd bourbon-ia
pip install -r requirements.txt uvicorn
uvicorn api.index:app --port 8000`}</pre>
              <button type="button" onClick={retester} className="font-medium text-[#D91227] hover:underline">
                Tester à nouveau
              </button>
            </>
          )}
          <p className="text-ink-500 dark:text-ink-300">
            Les amendements ne passent plus par le serveur en ligne. Pour un traitement 100 % local, choisissez aussi
            « 💻 IA Locale » ci-dessous (la clé de la démo Groq n'existe que sur le serveur en ligne). Fonctionne avec
            Chrome, Edge et Firefox.
          </p>
        </div>
      )}
    </section>
  )
}
