import { describe, it, expect } from 'vitest'
import { categorieAmendement, calculerBilan } from '../utils/bilan'

// Amendement tel que renvoyé par /api/v2/mecanique puis /api/v2/analyser-llm.
function amdt(statut_mecanique, resultat_ia, extra = {}) {
  const skip = statut_mecanique !== 'NOUVEAU'
  return { id: Math.random().toString(36), statut_mecanique, _skipLLM: skip, skip_llm: skip, resultat_ia, ...extra }
}

describe('bilan.js — catégories et bilan du classement', () => {
  it('non classé → null', () => {
    expect(categorieAmendement({ id: 'A' })).toBeNull()
  })

  it('classe chaque statut dans sa catégorie', () => {
    expect(categorieAmendement(amdt('DOUBLON_MECANIQUE', { statut: 'Doublon' }))).toBe('doublon')
    expect(categorieAmendement(amdt('IDENTIQUE_OFFICIEL', { statut: 'Identique' }))).toBe('identique')
    expect(categorieAmendement(amdt('ISOLE_MECANIQUE', { statut: 'Isolé' }, {
      justification_mecanique: 'Irrecevable (Art. 40 - Recevabilité financière)',
    }))).toBe('ecarte')
    expect(categorieAmendement(amdt('ISOLE_MECANIQUE', { statut: 'Isolé' }))).toBe('isole')
    expect(categorieAmendement(amdt('NOUVEAU', { statut: 'Discussion commune', analyse_intention: 'Même alinéa.' }))).toBe('commune')
    expect(categorieAmendement(amdt('NOUVEAU', { statut: 'Similaire', analyse_intention: 'Proche.' }))).toBe('commune')
    expect(categorieAmendement(amdt('NOUVEAU', { statut: 'Isolé', analyse_intention: 'Seul.' }))).toBe('isole')
  })

  it("cas ambigu pas encore analysé → en attente d'IA ; échec → erreur", () => {
    expect(categorieAmendement(amdt('NOUVEAU', { statut: 'Isolé', justification: "En attente d'analyse IA...", analyse_intention: '' }))).toBe('attente')
    expect(categorieAmendement(amdt('NOUVEAU', { statut: 'Erreur IA', analyse_intention: '⚠️ Impossible de joindre l\'IA' }))).toBe('erreur')
  })

  it('compte les triés sans IA et les analysés par l\'IA', () => {
    const bilan = calculerBilan([
      amdt('DOUBLON_MECANIQUE', { statut: 'Doublon' }),
      amdt('IDENTIQUE_MECANIQUE', { statut: 'Identique' }),
      amdt('NOUVEAU', { statut: 'Discussion commune', analyse_intention: 'Même alinéa.' }),
      amdt('NOUVEAU', { statut: 'Erreur IA', analyse_intention: '⚠️' }),
      { id: 'non-classe' },
    ])

    expect(bilan).toMatchObject({ total: 5, classes: 4, sansIA: 2, parIA: 1 })
    expect(bilan.parCategorie).toMatchObject({ doublon: 1, identique: 1, commune: 1, erreur: 1, isole: 0 })
  })
})
