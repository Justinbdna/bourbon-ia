export default function ClassifyButton({
  disabled,
  loading,
  error,
  warnings = [],
  onMechanicalClick,
  onLlmClick,
  onStop,
  progressInfo,
  mechanicalSummary,
}) {
  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg text-slate-900 dark:text-plume">Classement automatique</h2>
          <p className="text-sm text-ink-500 dark:text-ink-300 mt-0.5">
            Applique les règles de classement de l'Assemblée aux amendements chargés, avec ou sans IA.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
          {loading ? (
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full sm:w-auto">
              <div className="flex flex-col items-start sm:items-end">
                {progressInfo?.total > 0 && (
                  <span className="text-xs sm:text-sm font-bold text-bourbon">
                    🧠 Analyse en cours ({progressInfo.current || 0} / {progressInfo.total})...
                  </span>
                )}
                <span className="text-[10px] sm:text-xs text-slate-500 flex items-center gap-1 animate-pulse">
                  Temps écoulé : {progressInfo?.elapsed || 0} s
                </span>
              </div>
              <button
                type="button"
                onClick={onStop}
                className="w-full sm:w-auto rounded-md bg-red-600 px-4 py-2 text-xs sm:text-sm font-semibold text-white hover:bg-red-700 transition-all shadow-[0_0_15px_rgba(220,38,38,0.5)] flex items-center justify-center gap-2"
              >
                Annuler
              </button>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full sm:w-auto">
              <button
                type="button"
                disabled={disabled}
                onClick={onMechanicalClick}
                className="w-full sm:w-auto rounded-md bg-[#D91227] px-4 py-2.5 text-xs sm:text-sm font-semibold text-white hover:bg-[#D91227]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_15px_rgba(217,18,39,0.4)] hover:shadow-[0_0_20px_rgba(217,18,39,0.6)] flex items-center justify-center gap-2 text-center shrink-0"
                title="Tri déterministe immédiat (Identiques, Doublons, Priorités, Chapeaux, Art. 40)"
              >
                ⚡ Lancer le classement mécanique
              </button>

              <button
                type="button"
                disabled={disabled}
                onClick={onLlmClick}
                className="w-full sm:w-auto rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 px-4 py-2.5 text-xs sm:text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2 text-center shrink-0"
                title="Interroge l'IA pour expliciter les discussions communes et similitudes de fond"
              >
                🤖 Expliquer les conflits par IA
              </button>
            </div>
          )}
        </div>
      </div>

      {mechanicalSummary && !loading && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-emerald-700 dark:text-emerald-300 bg-emerald-50/80 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 rounded-md px-3 py-1.5">
          <span className="font-semibold">
            ⚡ Classement déterministe exécuté en {mechanicalSummary.elapsedSec} s
          </span>
          {mechanicalSummary.statistiques && (
            <span className="text-slate-600 dark:text-slate-300">
              — {mechanicalSummary.statistiques.identiques ?? 0} Identiques ·{' '}
              {mechanicalSummary.statistiques.discussions_communes ?? 0} Discussions communes ·{' '}
              {mechanicalSummary.statistiques.isoles ?? 0} Isolés
            </span>
          )}
        </div>
      )}

      {error && (
        <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      {warnings.length > 0 && (
        <ul className="mt-4 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 space-y-1">
          {warnings.map((w, i) => (
            <li key={i}>⚠️ {w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
