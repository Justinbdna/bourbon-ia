/**
 * ConsentModal — Modale RGPD de consentement pour la sauvegarde locale chiffrée.
 * 100% natif React + Tailwind, aucune dépendance Radix UI.
 */
export default function ConsentModal({ isOpen, onAccept, onRefuse }) {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-md flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
    >
      <div className="bg-white dark:bg-[#1A1B22] rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 max-w-lg w-full p-6 md:p-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-3xl" aria-hidden="true">🔒</span>
          <h2 id="consent-title" className="text-lg font-bold text-slate-900 dark:text-white">
            Protection des données — Sauvegarde locale
          </h2>
        </div>

        <p className="text-sm text-slate-700 dark:text-slate-300 mb-4 leading-relaxed">
          Bourbon.IA peut sauvegarder votre session de travail dans le navigateur afin de reprendre en cas de coupure ou de crash.
        </p>

        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-xl p-4 mb-4">
          <p className="text-sm text-amber-800 dark:text-amber-200 leading-relaxed">
            <strong>Garanties de sécurité :</strong><br />
            • Les données sont <strong>chiffrées (AES-256-GCM)</strong> avant tout stockage.<br />
            • La clé de chiffrement est <strong>volatile</strong> : elle est détruite à la fermeture de l'onglet.<br />
            • Aucune donnée ne quitte votre navigateur.
          </p>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
          Si vous refusez, aucune donnée ne sera sauvegardée. Un rechargement de page ou un crash effacera votre travail en cours.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-end gap-3">
          <button
            type="button"
            onClick={onRefuse}
            className="w-full sm:w-auto rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            Refuser
          </button>
          <button
            type="button"
            onClick={onAccept}
            className="w-full sm:w-auto rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors shadow-[0_0_15px_rgba(16,185,129,0.3)]"
          >
            Accepter la sauvegarde chiffrée
          </button>
        </div>
      </div>
    </div>
  )
}
