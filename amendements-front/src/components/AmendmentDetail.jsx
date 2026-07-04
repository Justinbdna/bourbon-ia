import ScrollableText from './ScrollableText'
import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'

export default function AmendmentDetail({ amendment, onClose }) {
  if (!amendment) {
    return (
      <div className="rounded-lg border border-dashed border-ink-300 bg-white p-8 h-full flex items-center justify-center">
        <p className="text-sm text-ink-500 text-center">
          Sélectionne un amendement dans le tableau pour voir son détail.
        </p>
      </div>
    )
  }

  const a = amendment
  const res = a.resultat_ia

  return (
    <div className="rounded-lg border border-ink-300 bg-white flex flex-col h-full">
      <div className="border-b border-ink-100 px-5 py-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-500">
            {a.texte_examine?.titre}
            {a.texte_examine?.lecture ? ` · ${a.texte_examine.lecture}` : ''}
          </p>
          <h3 className="font-display text-xl text-marine-900 mt-0.5">
            Article {a.article} — Amendement n° {a.numero}
            {a.rectification ? ` ${a.rectification}` : ''}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-ink-500 hover:text-ink-900 text-sm shrink-0"
          aria-label="Fermer le détail"
        >
          Fermer ✕
        </button>
      </div>

      <div className="px-5 py-4 space-y-5 overflow-y-auto scroll-thin">
        <div className="flex flex-wrap gap-4 text-sm">
          <div>
            <p className="text-ink-500 text-xs">Auteur(s)</p>
            <p className="text-ink-900 font-medium">
              {a.rapporteur ? 'Rapporteur — ' : ''}
              {(a.auteurs || []).join(', ') || '—'}
            </p>
          </div>
          <div>
            <p className="text-ink-500 text-xs">Date de dépôt</p>
            <p className="text-ink-900 font-medium">{a.date_depot || '—'}</p>
          </div>
          <div>
            <p className="text-ink-500 text-xs">Point d'impact</p>
            <ImpactBadge type={a.point_impact?.type} />
          </div>
        </div>

        <section className="rounded-md bg-marine-50 border border-marine-100 p-3.5">
          <h4 className="font-display text-sm uppercase tracking-wide text-marine-800 mb-2">
            Résultat du classement IA
          </h4>
          {res ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-marine-900">Rang {res.rang}</span>
                <GroupeBadge type={res.groupe?.type} />
              </div>
              <p className="text-ink-700">{res.justification}</p>
            </div>
          ) : (
            <p className="text-sm text-ink-500 italic">
              Pas encore classé — lance le classement IA depuis le bouton en haut de page.
            </p>
          )}
        </section>

        <section>
          <h4 className="font-display text-sm uppercase tracking-wide text-marine-800 mb-2">
            Dispositif
          </h4>
          <ScrollableText text={a.dispositif} />
        </section>

        <section>
          <h4 className="font-display text-sm uppercase tracking-wide text-marine-800 mb-2">
            Exposé sommaire
          </h4>
          <ScrollableText text={a.expose_sommaire} />
        </section>
      </div>
    </div>
  )
}
