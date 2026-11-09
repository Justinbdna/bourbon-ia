const LABELS = {
  suppression_article: 'Suppression d\u2019article',
  redaction_globale_article: 'Rédaction globale (article)',
  suppression_alinea: 'Suppression d\u2019alinéa',
  redaction_globale_alinea: 'Rédaction globale (alinéa)',
  point_restreint: 'Point d\u2019impact restreint',
  article_entier: 'Article entier',
}

const STYLES = {
  suppression_article: 'bg-red-50 text-red-700 ring-red-200 dark:bg-red-950/60 dark:ring-red-800/50 dark:text-red-300',
  redaction_globale_article: 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/60 dark:ring-amber-800/50 dark:text-amber-300',
  suppression_alinea: 'bg-orange-50 text-orange-700 ring-orange-200 dark:bg-orange-950/60 dark:ring-orange-800/50 dark:text-orange-300',
  redaction_globale_alinea: 'bg-yellow-50 text-yellow-800 ring-yellow-200 dark:bg-yellow-950/60 dark:ring-yellow-800/50 dark:text-yellow-300',
  point_restreint: 'bg-slate-100 text-slate-700 ring-slate-300 dark:bg-slate-900/60 dark:ring-slate-700/50 dark:text-slate-300',
  article_entier: 'bg-slate-100 text-slate-700 ring-slate-300 dark:bg-slate-900/60 dark:ring-slate-700/50 dark:text-slate-300',
}

function formaterImpact(type) {
  if (!type) return ''
  const cle = String(type).toLowerCase().replace(/^redaction_alinea$/, 'redaction_globale_alinea')
  if (LABELS[cle]) return LABELS[cle]

  let texte = String(type).trim()
  texte = texte.replace(/,?\s*insérer l['’]article suivant\s*:?/gi, '')
  texte = texte.replace(/\bAVANT\s+L['’]ARTICLE\s+PREMIER\b/gi, 'Avant art. 1er')
  texte = texte.replace(/\bAPR[ÈE]S\s+L['’]ARTICLE\s+PREMIER\b/gi, 'Après art. 1er')
  texte = texte.replace(/\bAVANT\s+L['’]ARTICLE\s+/gi, 'Avant art. ')
  texte = texte.replace(/\bAPR[ÈE]S\s+L['’]ARTICLE\s+/gi, 'Après art. ')
  texte = texte.replace(/\bARTICLE\s+PREMIER\b/gi, 'Art. 1er')
  texte = texte.replace(/\bARTICLE\s+/gi, 'Art. ')
  return texte.trim()
}

export default function ImpactBadge({ type }) {
  if (!type) return <span className="text-ink-500 text-xs">—</span>

  const cle = String(type).toLowerCase().replace(/^redaction_alinea$/, 'redaction_globale_alinea')
  const label = formaterImpact(type)
  const style = STYLES[cle] || 'bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800/70 dark:text-slate-300 dark:ring-slate-700'

  return (
    <span
      title={String(type)}
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 whitespace-nowrap text-xs font-medium ring-1 ring-inset ${style}`}
    >
      {label}
    </span>
  )
}
