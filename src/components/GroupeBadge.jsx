const LABELS = {
  discussion_commune: 'Discussion commune',
  Incompatible: 'Discussion commune',
  identiques: 'Identiques',
  Identique: 'Identiques',
  doublon: 'Doublon',
  Doublon: 'Doublon',
  Nouveau: 'Isolé',
  isole: 'Isolé',
}

const STYLES = {
  discussion_commune: 'bg-purple-100 text-purple-800 ring-purple-300',
  Incompatible: 'bg-purple-100 text-purple-800 ring-purple-300',
  identiques: 'bg-blue-100 text-blue-800 ring-blue-300',
  Identique: 'bg-blue-100 text-blue-800 ring-blue-300',
  doublon: 'bg-red-100 text-red-800 ring-red-300',
  Doublon: 'bg-red-100 text-red-800 ring-red-300',
  Nouveau: 'bg-ink-100 text-ink-800 ring-ink-300',
  isole: 'bg-ink-100 text-ink-800 ring-ink-300',
  Erreur: 'bg-red-100 text-red-800 ring-red-300',
}

export default function GroupeBadge({ type }) {
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
