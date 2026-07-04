const LABELS = {
  suppression_article: 'Suppression d\u2019article',
  redaction_globale_article: 'Rédaction globale (article)',
  suppression_alinea: 'Suppression d\u2019alinéa',
  redaction_globale_alinea: 'Rédaction globale (alinéa)',
  point_restreint: 'Point d\u2019impact restreint',
  article_entier: 'Article entier',
}

const STYLES = {
  suppression_article: 'bg-red-50 text-red-700 ring-red-200',
  redaction_globale_article: 'bg-amber-50 text-amber-700 ring-amber-200',
  suppression_alinea: 'bg-orange-50 text-orange-700 ring-orange-200',
  redaction_globale_alinea: 'bg-yellow-50 text-yellow-800 ring-yellow-200',
  point_restreint: 'bg-marine-50 text-marine-700 ring-marine-100',
  article_entier: 'bg-marine-50 text-marine-700 ring-marine-100',
}

export default function ImpactBadge({ type }) {
  if (!type) return <span className="text-ink-500 text-xs">—</span>

  const label = LABELS[type] || type
  const style = STYLES[type] || 'bg-ink-100 text-ink-700 ring-ink-300'

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${style}`}
    >
      {label}
    </span>
  )
}
