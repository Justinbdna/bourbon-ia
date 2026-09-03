import ScrollableText from './ScrollableText'
import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'
import AuthorBadge from './amendment/AuthorBadge'
import PoliticalGroupTag from './amendment/PoliticalGroupTag'
import LegislativeContext from './amendment/LegislativeContext'
import IdentiqueAlert from './amendment/IdentiqueAlert'
import SkeletonLoader from './amendment/SkeletonLoader'

export default function AmendmentDetail({ amendment, onClose, isLoading }) {
  // ── Safe Rendering : Skeleton si en cours de chargement ──
  if (isLoading) {
    return (
      <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-6 h-full">
        <SkeletonLoader type="card" />
      </div>
    )
  }

  if (!amendment) {
    return (
      <div className="rounded-lg border border-dashed border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-8 h-full flex items-center justify-center">
        <p className="text-sm text-ink-500 dark:text-ink-300 text-center">
          Sélectionne un amendement dans le tableau pour voir son détail.
        </p>
      </div>
    )
  }

  const a = amendment
  const res = a.resultat_ia

  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 flex flex-col h-full">
      <div className="border-b border-ink-100 dark:border-ink-700 px-5 py-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-500 dark:text-ink-400">
            {a.texte_examine?.titre}
            {a.texte_examine?.lecture ? ` · ${a.texte_examine.lecture}` : ''}
          </p>
          <h3 className="font-display text-xl text-slate-900 dark:text-plume mt-0.5">
            {a.article ? (a.article.trim().toLowerCase().startsWith('article') ? a.article : `Article ${a.article}`) : 'Article —'} — Amendement n° {a.numero}
            {a.rectification ? ` ${a.rectification}` : ''}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-ink-500 hover:text-ink-900 dark:text-ink-400 dark:hover:text-plume text-sm shrink-0"
          aria-label="Fermer le détail"
        >
          Fermer ✕
        </button>
      </div>

      <div className="px-5 py-4 space-y-5 overflow-y-auto scroll-thin">
        {/* ── Alerte Identique Officiel AN ── */}
        <IdentiqueAlert
          isIdentical={a.isIdentical ?? a.est_identique_officiel ?? false}
          discussionId={a.discussionId ?? a.id_discussion_identique}
        />

        {/* ── Contexte législatif (titre tronqué + tooltip) ── */}
        {(a.title || a.dossier_titre) && (
          <LegislativeContext
            title={a.title || a.dossier_titre}
            dossierRef={a.dossier_ref}
          />
        )}

        <div className="flex flex-wrap gap-4 text-sm">
          {/* ── Auteur enrichi ── */}
          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs mb-1">Auteur(s)</p>
            {a.auteur_nom && a.auteur_nom !== "Inconnu" ? (
              <AuthorBadge data={{
                auteur_nom: a.auteur_nom,
                auteur_prenom: a.auteur_prenom,
                auteur_trigramme: a.auteur_trigramme
              }} />
            ) : (
              <div className="max-h-24 overflow-y-auto text-sm bg-gray-100 text-slate-900 dark:bg-[#1A1B22] dark:text-white border border-gray-300 dark:border-gray-700 p-2 rounded mt-1">
                <p className="font-medium">
                  {a.rapporteur ? 'Rapporteur — ' : ''}
                  {(a.auteurs || []).join(', ') || '—'}
                </p>
              </div>
            )}
          </div>

          {/* ── Groupe politique ── */}
          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs mb-1">Groupe</p>
            <PoliticalGroupTag
              group={a.groupe_politique}
              groupRef={a.groupRef ?? a.groupe_politique_ref}
            />
          </div>

          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs">Date de dépôt</p>
            <p className="text-ink-900 dark:text-plume font-medium">{a.date_depot || '—'}</p>
          </div>
          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs">Point d'impact</p>
            <ImpactBadge type={a.point_impact?.type} />
          </div>
        </div>

        {/* ── Résultat IA (avec Chain of Thought) ── */}
        <section className="rounded-md bg-slate-50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-800 p-3.5">
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Résultat du classement
          </h4>
          {res ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-slate-900 dark:text-plume">Rang {res.rang}</span>
                <GroupeBadge type={res.groupe?.type} />

                {/* ── 💡 Tooltip Chain of Thought ── */}
                {res.analyse_intention && (
                  <div className="group relative inline-flex">
                    <span className="cursor-help text-base" title={res.analyse_intention}>💡</span>
                    <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 bg-slate-900 text-white text-xs rounded-lg shadow-xl p-3 leading-relaxed">
                      <p className="font-semibold text-amber-300 mb-1">🧠 Raisonnement de l'IA</p>
                      <p className="mb-1">{res.analyse_intention}</p>
                      {res.analyse_politique && (
                        <p className="text-slate-300 border-t border-slate-700 pt-1 mt-1">{res.analyse_politique}</p>
                      )}
                      {res.niveau_confiance != null && (
                        <p className="text-slate-400 mt-1">Confiance : {(res.niveau_confiance * 100).toFixed(0)}%</p>
                      )}
                      {res.cached && (
                        <p className="text-green-400 mt-1 text-[10px]">📦 Résultat en cache</p>
                      )}
                      <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-[1px] border-4 border-transparent border-t-slate-900" />
                    </div>
                  </div>
                )}
              </div>
              <p className="text-ink-700 dark:text-ink-300">{res.justification}</p>
            </div>
          ) : (
            <p className="text-sm text-ink-500 dark:text-ink-400 italic">
              Pas encore classé — lance le classement depuis le bouton en haut de page.
            </p>
          )}
        </section>

        {a.texte_loi_reference && (
          <section className="bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/40 rounded-md p-4">
            <h4 className="font-display text-sm uppercase tracking-wide text-amber-900 dark:text-amber-200 mb-2 flex items-center gap-1.5">
              <span>📜</span> Texte de loi initial de référence ({a.article ? (a.article.trim().toLowerCase().startsWith('article') ? a.article : `Article ${a.article}`) : 'Article'})
            </h4>
            <ScrollableText text={a.texte_loi_reference} />
          </section>
        )}

        <section className="bg-gray-50 dark:bg-surface border border-ink-200 dark:border-ink-700 rounded-md p-4">
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Dispositif
          </h4>
          <ScrollableText text={a.dispositif} />
        </section>

        <section className="bg-gray-50 dark:bg-surface border border-ink-200 dark:border-ink-700 rounded-md p-4">
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Exposé sommaire
          </h4>
          <ScrollableText text={a.expose_sommaire} />
        </section>
      </div>
    </div>
  )
}
