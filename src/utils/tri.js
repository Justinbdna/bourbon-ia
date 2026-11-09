/**
 * tri.js — Ordre d'affichage du tableau des amendements.
 *
 * Par défaut, du plus récent au plus ancien ; « ordre du texte » garde l'ordre
 * de la liasse (articles), seul ordre où le glisser-déposer a un sens.
 * L'export préjaune suit toujours l'ordre du texte.
 */

export const TRIS = [
  { cle: 'recent', libelle: 'Plus récents d’abord' },
  { cle: 'ancien', libelle: 'Plus anciens d’abord' },
  { cle: 'texte', libelle: 'Ordre du texte (articles)' },
]

// Clé chronologique : date de dépôt, puis numéro d'ordre de dépôt (fin de
// l'uid AN, ex. …N000137) — seul repère quand le fichier ne porte pas de date.
function cleChronologique(a) {
  const date = Date.parse(a.dateDepot || '') || 0
  const ordre = Number(String(a.uid || a.id || '').match(/N0*(\d+)$/)?.[1] || String(a.numero || '').match(/\d+/)?.[0] || 0)
  return [date, ordre]
}

export function comparerChronologie(x, y) {
  const [dx, ox] = cleChronologique(x)
  const [dy, oy] = cleChronologique(y)
  return dx - dy || ox - oy
}

/**
 * Trie des entrées `{ a, idx }` (amendement + index dans la liste complète).
 * 'texte' laisse l'ordre tel quel ; à égalité, l'ordre de la liasse départage.
 */
export function trierEntrees(entrees, tri) {
  if (tri === 'texte') return entrees
  const sens = tri === 'ancien' ? 1 : -1
  return [...entrees].sort((x, y) => sens * comparerChronologie(x.a, y.a) || x.idx - y.idx)
}
