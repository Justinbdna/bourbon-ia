export default function ClassifyButton({ disabled, loading, error, warnings = [], onClick }) {
  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-display text-lg text-marine-900 dark:text-plume">Classement automatique</h2>
          <p className="text-sm text-ink-500 dark:text-ink-300 mt-0.5">
            Applique les règles de classement de l'Assemblée aux amendements chargés, via l'IA.
          </p>
        </div>

        <button
          type="button"
          disabled={disabled || loading}
          onClick={onClick}
          className="rounded-md bg-bourbon px-5 py-2.5 text-sm font-semibold text-white hover:bg-bourbon/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_15px_rgba(217,18,39,0.5)] hover:shadow-[0_0_20px_rgba(217,18,39,0.7)]"
        >
          {loading ? 'Classement en cours…' : 'Lancer le classement IA'}
        </button>
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      {warnings.length > 0 && (
        <ul className="mt-3 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 space-y-1">
          {warnings.map((w, i) => (
            <li key={i}>⚠️ {w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
