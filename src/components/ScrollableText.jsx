import { useMemo, useState } from 'react'

const LINE_LIMIT = 20
const COLLAPSED_HEIGHT = 320 // px, ~20 lignes en text-sm/leading-relaxed

/**
 * Affiche un texte d'amendement. Si le contenu dépasse ~20 lignes,
 * le texte est présenté dans une zone à hauteur fixe et défilante,
 * avec un bouton pour le déplier entièrement si besoin.
 */
export default function ScrollableText({ text, className = '' }) {
  const [expanded, setExpanded] = useState(false)

  const lineCount = useMemo(() => {
    if (!text) return 0
    // Compte les retours à la ligne explicites + une estimation
    // des lignes supplémentaires dues au retour automatique.
    const explicitLines = text.split('\n')
    const estimatedWrap = explicitLines.reduce(
      (sum, line) => sum + Math.max(1, Math.ceil(line.length / 100)),
      0
    )
    return estimatedWrap
  }, [text])

  if (!text) {
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
        {text}
      </div>

      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-xs font-medium text-marine-700 hover:text-marine-900 underline underline-offset-2"
        >
          {expanded ? 'Réduire' : `Afficher tout (${lineCount} lignes environ)`}
        </button>
      )}
    </div>
  )
}
