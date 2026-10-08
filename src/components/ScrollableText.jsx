import { useMemo, useState } from 'react'

const LINE_LIMIT = 20
const COLLAPSED_HEIGHT = 320 // px, ~20 lignes en text-sm/leading-relaxed

export function stripHtml(text) {
  if (!text || typeof text !== 'string') return text || ''
  return text
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&#160;/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/\n\s*\n+/g, '\n\n')
    .trim()
}

/**
 * Affiche un texte d'amendement assaini sans balises HTML brutes.
 */
export default function ScrollableText({ text, className = '' }) {
  const [expanded, setExpanded] = useState(false)

  const cleanText = useMemo(() => {
    return stripHtml(text)
  }, [text])

  const lineCount = useMemo(() => {
    if (!cleanText) return 0
    // Compte les retours à la ligne explicites + une estimation
    // des lignes supplémentaires dues au retour automatique.
    const explicitLines = cleanText.split('\n')
    const estimatedWrap = explicitLines.reduce(
      (sum, line) => sum + Math.max(1, Math.ceil(line.length / 100)),
      0
    )
    return estimatedWrap
  }, [cleanText])

  if (!cleanText) {
    return <p className="text-ink-500 italic text-sm">— Non renseigné —</p>
  }

  const isLong = lineCount > LINE_LIMIT

  return (
    <div className={className}>
      <div
        className={`scroll-thin whitespace-pre-wrap text-sm leading-relaxed text-ink-800 ${
          isLong && !expanded ? 'overflow-y-auto pr-2' : ''
        }`}
        style={isLong && !expanded ? { maxHeight: COLLAPSED_HEIGHT } : undefined}
      >
        {cleanText}
      </div>

      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white underline underline-offset-2"
        >
          {expanded ? 'Réduire' : `Afficher tout (${lineCount} lignes environ)`}
        </button>
      )}
    </div>
  )
}
