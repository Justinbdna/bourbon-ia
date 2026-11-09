import { describe, it, expect } from 'vitest'
import { trierEntrees } from '../utils/tri'

const entrees = (liste) => liste.map((a, idx) => ({ a, idx }))
const ids = (resultat) => resultat.map(({ a }) => a.id)

describe('tri.js — ordre du tableau des amendements', () => {
  it('par défaut, du plus récent au plus ancien selon la date de dépôt', () => {
    const liste = entrees([
      { id: 'A', dateDepot: '2025-12-01T00:00:00.000Z' },
      { id: 'B', dateDepot: '2025-12-09T00:00:00.000Z' },
      { id: 'C', dateDepot: '2025-12-05T00:00:00.000Z' },
    ])

    expect(ids(trierEntrees(liste, 'recent'))).toEqual(['B', 'C', 'A'])
    expect(ids(trierEntrees(liste, 'ancien'))).toEqual(['A', 'C', 'B'])
  })

  it('sans date, le numéro d’ordre de dépôt (fin de l’uid) fait foi', () => {
    const liste = entrees([
      { id: 'AMANR5L17PO419604B1641P0D1N000018' },
      { id: 'AMANR5L17PO419604B1641P0D1N000137' },
      { id: 'AMANR5L17PO419604B1641P0D1N000065' },
    ])

    expect(ids(trierEntrees(liste, 'recent')).map((u) => u.slice(-3))).toEqual(['137', '065', '018'])
  })

  it('« ordre du texte » conserve l’ordre de la liasse', () => {
    const liste = entrees([{ id: 'X', dateDepot: '2025-01-01' }, { id: 'Y', dateDepot: '2026-01-01' }])

    expect(ids(trierEntrees(liste, 'texte'))).toEqual(['X', 'Y'])
  })
})
