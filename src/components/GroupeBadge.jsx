const LABELS = {
  discussion_commune: 'Discussion commune',
  identiques: 'Identiques',
  doublon: 'Doublon',
  additionnel: 'Additionnel',
  isole: 'Isolé',
}

const STYLES = {
  discussion_commune: 'bg-purple-50 text-purple-700 ring-purple-200',
  identiques: 'bg-blue-50 text-blue-700 ring-blue-200',
  doublon: 'bg-red-50 text-red-700 ring-red-200',
  additionnel: 'bg-teal-50 text-teal-700 ring-teal-200',
  isole: 'bg-ink-100 text-ink-600 ring-ink-300',
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
