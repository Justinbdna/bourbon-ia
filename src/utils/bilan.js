/**
 * bilan.js — Catégorie de chaque amendement après classement, et bilan chiffré
 * affiché en tête du tableau (<BilanClassement>).
 *
 * Une seule catégorie par amendement, testée dans cet ordre :
 *   doublon → écarté (irrecevable, retiré ou vide) → erreur IA → en attente d'IA
 *   → identique → discussion commune → isolé.
 */

export const CATEGORIES = ['commune', 'identique', 'doublon', 'ecarte', 'isole', 'attente', 'erreur']

// Doublon = même texte, même auteur, même commission (moteur déterministe).
export function estDoublon(a) {
  return a.statut_mecanique === 'DOUBLON_MECANIQUE' || a.resultat_ia?.statut === 'Doublon'
}

// Irrecevable (Art. 40 / 45), retiré ou sans dispositif : écarté de la séance.
export function estEcarte(a) {
  const statut = String(a.statut || a.resultat_ia?.statut || a.statut_mecanique || '').toLowerCase()
  const sort = String(a.sort || a.raw_dict?.sort || '').toLowerCase()
  const justification = String(a.justification_mecanique || '').toLowerCase()
  return [statut, sort, justification].some(
    (texte) => texte.includes('irrecevable') || texte.includes('retiré') || texte.includes('retire')
  )
}

// Envoyé à l'IA (cas ambigu) et pas encore analysé.
function enAttenteIA(a) {
  return a.statut_mecanique === 'NOUVEAU' && !a._skipLLM && !a.skip_llm && !a.resultat_ia?.analyse_intention
}

/** Catégorie d'un amendement classé, ou null s'il n'a pas encore été classé. */
export function categorieAmendement(a) {
  if (!a?.resultat_ia) return null
  if (estDoublon(a)) return 'doublon'
  if (estEcarte(a)) return 'ecarte'

  const statut = String(a.resultat_ia.statut || a.statut || '')
  if (statut.startsWith('Erreur')) return 'erreur'
  if (enAttenteIA(a)) return 'attente'
  if (statut === 'Identique' || statut === 'Identiques') return 'identique'
  if (statut === 'Discussion commune' || statut === 'Incompatible' || statut === 'Similaire') return 'commune'
  return 'isole'
}

/**
 * Bilan du classement : effectif par catégorie, nombre d'amendements triés
 * sans IA (moteur déterministe) et nombre analysés par l'IA.
 * `classes` vaut 0 tant que le classement n'a pas été lancé.
 */
export function calculerBilan(amendments) {
  const parCategorie = Object.fromEntries(CATEGORIES.map((c) => [c, 0]))
  let classes = 0
  let sansIA = 0
  let parIA = 0

  for (const a of amendments) {
    const categorie = categorieAmendement(a)
    if (!categorie) continue
    classes++
    parCategorie[categorie]++
    if (a._skipLLM || a.skip_llm || a.statut_mecanique !== 'NOUVEAU') sansIA++
    else if (categorie !== 'attente' && categorie !== 'erreur') parIA++
  }

  return { total: amendments.length, classes, sansIA, parIA, parCategorie }
}
