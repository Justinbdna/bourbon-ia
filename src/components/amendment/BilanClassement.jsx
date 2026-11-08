/**
 * BilanClassement — Bandeau chiffré en tête du tableau, après classement.
 *
 * Une tuile par catégorie (discussions communes, identiques, doublons,
 * écartés, isolés ; « en attente d'IA » et « erreurs IA » seulement s'il y en
 * a). Cliquer une tuile filtre le tableau sur cette catégorie ; la recliquer
 * retire le filtre. Une ligne indique la part triée sans IA.
 */

const TUILES = [
  {
    cle: 'commune',
    libelle: 'Discussions communes',
    aide: 'Amendements concurrents sur le même passage, à discuter ensemble.',
    style: 'border-purple-200 bg-purple-50 text-purple-900 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-200',
    actif: 'ring-purple-500',
  },
  {
    cle: 'identique',
    libelle: 'Identiques',
    aide: "Même texte déposé par des auteurs différents (ou marqués identiques par l'AN).",
    style: 'border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200',
    actif: 'ring-blue-500',
  },
  {
    cle: 'doublon',
    libelle: 'Doublons',
    aide: 'Même texte redéposé par le même auteur devant la même commission : copie à retirer.',
    style: 'border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-200',
    actif: 'ring-rose-500',
  },
  {
    cle: 'ecarte',
    libelle: 'Écartés',
    aide: 'Irrecevables (Art. 40 / 45), retirés ou sans dispositif.',
    style: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200',
    actif: 'ring-amber-500',
  },
  {
    cle: 'isole',
    libelle: 'Isolés',
    aide: 'Seuls sur leur passage du texte : appelés un par un.',
    style: 'border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-200',
    actif: 'ring-slate-500',
  },
  {
    cle: 'attente',
    libelle: "En attente d'IA",
    aide: "Cas ambigus pas encore analysés par l'IA : lancez le classement.",
    style: 'border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-200',
    actif: 'ring-sky-500',
    siPresent: true,
  },
  {
    cle: 'erreur',
    libelle: 'Erreurs IA',
    aide: "L'IA n'a pas pu analyser ces amendements : relancez le classement.",
    style: 'border-red-200 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200',
    actif: 'ring-red-500',
    siPresent: true,
  },
]

export default function BilanClassement({ bilan, categorieActive, onFiltrer }) {
  if (!bilan || bilan.classes === 0) return null

  const tuiles = TUILES.filter((t) => !t.siPresent || bilan.parCategorie[t.cle] > 0)
  const partSansIA = Math.round((bilan.sansIA / bilan.classes) * 100)

  return (
    <section
      aria-label="Bilan du classement"
      className="border-b border-ink-200 dark:border-ink-700 bg-white dark:bg-surface px-4 py-3"
    >
      <div className="flex flex-wrap gap-2">
        {tuiles.map((t) => {
          const nb = bilan.parCategorie[t.cle]
          const actif = categorieActive === t.cle
          return (
            <button
              key={t.cle}
              type="button"
              aria-pressed={actif}
              onClick={() => onFiltrer(actif ? '' : t.cle)}
              title={`${t.aide} Cliquer pour ${actif ? 'retirer le filtre' : 'filtrer le tableau'}.`}
              className={`flex-1 min-w-[130px] rounded-lg border px-3 py-2 text-left transition-shadow hover:shadow-md ${t.style} ${actif ? `ring-2 ring-offset-1 dark:ring-offset-[#0B0C10] ${t.actif}` : ''}`}
            >
              <span className="block text-2xl font-bold leading-tight tabular-nums">{nb}</span>
              <span className="block text-xs font-medium">{t.libelle}</span>
            </button>
          )
        })}
      </div>

      <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
        <span>
          ⚙️ <strong className="text-slate-800 dark:text-slate-200">{bilan.sansIA}</strong> sur {bilan.classes} triés sans IA ({partSansIA} %), par règles déterministes
        </span>
        {bilan.parIA > 0 && (
          <span>
            · 🧠 <strong className="text-slate-800 dark:text-slate-200">{bilan.parIA}</strong> cas ambigus analysés par l'IA
          </span>
        )}
        {categorieActive && (
          <button
            type="button"
            onClick={() => onFiltrer('')}
            className="font-medium text-[#D91227] hover:underline"
          >
            ✕ Tout afficher
          </button>
        )}
      </p>
    </section>
  )
}
