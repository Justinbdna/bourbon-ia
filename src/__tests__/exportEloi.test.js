import { describe, it, expect } from 'vitest'
import { buildEloiPayload } from '../utils/exportEloi'
import { computeWordDiff } from '../components/AmendmentDetail'

describe('exportEloi utility', () => {
  it('construit un payload conforme au schéma Éloi avec métadonnées de séance', () => {
    const fakeAmendments = [
      {
        id: 'AMD-1',
        numero: '12',
        article: 'Article 1er',
        dispositif: 'Supprimer cet article.',
        expose_sommaire: 'Exposé sommaire.',
        statut: 'Discussion commune',
        priorite_appel: 1,
        libelle_appel: '1. Suppression globale',
        tombe_si_adoption: false,
        est_cavalier_art45: false,
        auteur_nom: 'Dupont',
        groupe_politique: 'EPR',
      },
      {
        id: 'AMD-2',
        numero: '13',
        article: 'Article 1er',
        dispositif: 'Compléter cet article.',
        expose_sommaire: 'Exposé sommaire.',
        statut: 'Discussion commune',
        priorite_appel: 5,
        libelle_appel: '5. Insertion / Adjonction',
        tombe_si_adoption: true,
        alerte_tombant: '⚠️ Tombe si adoption de 12',
        parent_suppression_numero: '12',
        est_cavalier_art45: true,
        alerte_art45: '⚠️ Risque Art. 45',
        auteur_nom: 'Durand',
        groupe_politique: 'LFI-NFP',
        arbitre_manuellement: true,
      },
    ]

    const result = buildEloiPayload(fakeAmendments)

    expect(result.format).toBe('ELOI_AN_JSON_v1')
    expect(result.total_amendements).toBe(2)
    expect(result.amendements).toHaveLength(2)

    const first = result.amendements[0]
    expect(first.numero).toBe('12')
    expect(first.ordre_de_seance.priorite_appel_art98).toBe(1)
    expect(first.ordre_de_seance.est_tombant).toBe(false)

    const second = result.amendements[1]
    expect(second.numero).toBe('13')
    expect(second.ordre_de_seance.est_tombant).toBe(true)
    expect(second.ordre_de_seance.alerte_tombant).toContain('12')
    expect(second.ordre_de_seance.est_cavalier_art45).toBe(true)
    expect(second.ordre_de_seance.arbitre_manuellement).toBe(true)
  })
})

describe('computeWordDiff in AmendmentDetail', () => {
  it('identifie correctement les mots identiques, ajoutés et supprimés', () => {
    const t1 = 'Supprimer le mot chat'
    const t2 = 'Supprimer le mot chien'

    const diff = computeWordDiff(t1, t2)
    const types = diff.map((d) => d.type)

    expect(types).toContain('del')
    expect(types).toContain('add')
    expect(types).toContain('same')

    const delChunk = diff.find((d) => d.type === 'del')
    expect(delChunk.text).toBe('chat')

    const addChunk = diff.find((d) => d.type === 'add')
    expect(addChunk.text).toBe('chien')
  })
})
