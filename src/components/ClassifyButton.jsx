export default function ClassifyButton({ disabled, loading, error, warnings = [], onClick, onStop, isReasoningMode, onToggleReasoning, progressInfo }) {
  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg text-slate-900 dark:text-plume">Classement automatique</h2>
          <p className="text-sm text-ink-500 dark:text-ink-300 mt-0.5">
            Applique les règles de classement de l'Assemblée aux amendements chargés, via l'IA.
          </p>
        </div>

        <div className="flex items-center gap-4 w-full sm:w-auto">
          <label className="flex items-center cursor-pointer gap-2 mr-2">
            <div className="relative">
              <input type="checkbox" className="sr-only" checked={isReasoningMode} onChange={(e) => onToggleReasoning(e.target.checked)} disabled={loading} />
              <div className={`block w-10 h-6 rounded-full transition-colors ${isReasoningMode ? 'bg-red-600' : 'bg-slate-300 dark:bg-slate-700'}`}></div>
              <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${isReasoningMode ? 'transform translate-x-4' : ''}`}></div>
            </div>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Analyse Profonde
            </span>
          </label>

          {loading ? (
            <div className="flex items-center gap-4">
              <div className="flex flex-col items-end">
                <span className="text-sm font-bold text-bourbon">
                  🧠 Amendement {progressInfo?.current || 0} / {progressInfo?.total || 0}
                </span>
                <span className="text-xs text-slate-500 flex items-center gap-1 animate-pulse">
                  Traitement en cours... ({progressInfo?.elapsed || 0}s)
                </span>
              </div>
              <button
                type="button"
                onClick={onStop}
                className="rounded-md bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-all shadow-[0_0_15px_rgba(220,38,38,0.5)] flex items-center gap-2"
              >
                Annuler
              </button>
            </div>
          ) : (
            <button
              type="button"
              disabled={disabled}
              onClick={onClick}
              className="rounded-md bg-bourbon px-5 py-2.5 text-sm font-semibold text-white hover:bg-bourbon/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_15px_rgba(217,18,39,0.5)] hover:shadow-[0_0_20px_rgba(217,18,39,0.7)] flex items-center justify-center gap-2"
            >
              Lancer le classement IA
            </button>
          )}
        </div>
      </div>

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
