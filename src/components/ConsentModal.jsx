/**
 * ConsentModal — Modale RGPD de consentement pour la sauvegarde locale.
 * Affichée au premier lancement si aucun consentement n'a été donné.
 */
export default function ConsentModal({ isOpen, onAccept, onRefuse }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-white dark:bg-[#1A1B22] rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 max-w-lg mx-4 p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🔒</span>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">
            Protection des données — Sauvegarde locale
          </h2>
        </div>

        <p className="text-sm text-slate-700 dark:text-slate-300 mb-3 leading-relaxed">
          Bourbon.IA peut sauvegarder votre session de travail dans le navigateur afin de reprendre en cas de coupure ou de crash.
        </p>

        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 mb-4">
          <p className="text-sm text-amber-800 dark:text-amber-200 leading-relaxed">
            <strong>Garanties de sécurité :</strong><br />
            • Les données sont <strong>chiffrées (AES-256-GCM)</strong> avant tout stockage.<br />
            • La clé de chiffrement est <strong>volatile</strong> : elle est détruite à la fermeture de l'onglet.<br />
            • Aucune donnée ne quitte votre navigateur.
          </p>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400 mb-5">
          Si vous refusez, aucune donnée ne sera sauvegardée. Un rechargement de page ou un crash effacera votre travail en cours.
        </p>

        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onRefuse}
            className="rounded-md border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            Refuser
          </button>
          <button
            type="button"
            onClick={onAccept}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors shadow-[0_0_10px_rgba(16,185,129,0.4)]"
          >
            Accepter la sauvegarde chiffrée
          </button>
        </div>
      </div>
    </div>
  )
}
