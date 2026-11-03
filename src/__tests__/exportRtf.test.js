import { describe, it, expect } from 'vitest'
import {
  rtfEscape,
  generateRtfPrejaune,
  isValidGroupIdentifier,
  resolveAmendmentGroup,
} from '../utils/exportRtf'

describe('exportRtf.js — Générateur Préjaune RTF', () => {
  it('échappe rigoureusement les métacaractères RTF (\\, {, })', () => {
    const raw = 'Texte avec \\ anti-slash, { accolade ouvrante et } fermante.'
    const escaped = rtfEscape(raw)

    expect(escaped).toBe('Texte avec \\\\ anti-slash, \\{ accolade ouvrante et \\} fermante.')
  })

  it('convertit les caractères accentués et glyphes de dessin de boîte en séquences Unicode RTF', () => {
    const accents = 'éàçù'
    const escapedAccents = rtfEscape(accents)
    expect(escapedAccents).toBe('\\u233?\\u224?\\u231?\\u249?')

    const glyphs = '╓║╙'
    const escapedGlyphs = rtfEscape(glyphs)
    expect(escapedGlyphs).toContain('\\u')
  })

  it('génère un en-tête et une structure RTF valide', () => {
    const amendments = [
      {
        id: 'AM1',
        numero: '1',
        article: '1',
        auteurs: ['M. Dupont', 'Mme Martin'],
        texte_examine: { titre: 'Projet de loi de finances' },
        resultat_ia: {
          statut: 'Discussion commune',
          groupe: { type: 'discussion_commune', groupe_id: 'GRP-1' },
          analyse_intention: 'Suppression article',
        },
      },
      {
        id: 'AM2',
        numero: '2',
        article: '1',
        auteurs: ['M. Durand'],
        resultat_ia: {
          statut: 'Discussion commune',
          groupe: { type: 'discussion_commune', groupe_id: 'GRP-1' },
          analyse_intention: 'Suppression alinéa',
        },
      },
    ]

    const rtf = generateRtfPrejaune(amendments)

    expect(rtf).toContain('{\\rtf1\\ansi\\ansicpg1252\\deff0')
    expect(rtf).toContain('Projet de loi de finances')
    expect(rtf).toContain('ARTICLE 1')
    expect(rtf).toContain('M. Dupont, Mme Martin')
    expect(rtf).toContain('[Dc.]')
  })

  it('bannit définitivement les faux positifs liés à "NUMERO", "Article PREMIER" ou null', () => {
    expect(isValidGroupIdentifier('NUMERO')).toBe(false)
    expect(isValidGroupIdentifier('Article PREMIER')).toBe(false)
    expect(isValidGroupIdentifier('ARTICLE 3 BIS')).toBe(false)
    expect(isValidGroupIdentifier(null)).toBe(false)
    expect(isValidGroupIdentifier('null')).toBe(false)
    expect(isValidGroupIdentifier('dc_art_1er_p_12')).toBe(true)
    expect(isValidGroupIdentifier('id_art_12_abcd1234')).toBe(true)

    const hallucinated = [
      {
        id: 'AM-FALSE-1',
        numero: '101',
        article: 'Article PREMIER',
        auteurs: ['M. Test'],
        statut: 'Discussion commune',
        groupe_conflit_id: 'NUMERO',
        cible_numero: 'Article PREMIER',
      },
      {
        id: 'AM-FALSE-2',
        numero: '102',
        article: 'Article PREMIER',
        auteurs: ['Mme Test'],
        statut: 'Isolé',
        groupe_conflit_id: null,
        cible_numero: null,
      },
    ]

    expect(resolveAmendmentGroup(hallucinated[0])).toBeNull()
    expect(resolveAmendmentGroup(hallucinated[1])).toBeNull()

    const rtf = generateRtfPrejaune(hallucinated)
    expect(rtf).not.toContain('[Dc.]')
    expect(rtf).not.toContain('[Id.]')
  })

  it('exploite groupe_conflit_id et cible_numero du moteur Python pour tracer [Id.] et [Dc.]', () => {
    const amendments = [
      {
        id: 'AM-1',
        numero: '12',
        article: 'Article PREMIER',
        auteurs: ['M. Alpha'],
        statut: 'Identique',
        groupe_conflit_id: 'id_article_premier_11223344',
        cible_numero: '42',
      },
      {
        id: 'AM-2',
        numero: '25',
        article: 'Article PREMIER',
        auteurs: ['M. Beta'],
        statut: 'Discussion commune',
        groupe_conflit_id: 'dc_article_premier_p_25',
        cible_numero: '68',
      },
      {
        id: 'AM-3',
        numero: '42',
        article: 'Article PREMIER',
        auteurs: ['Mme Gamma'],
        statut: 'Identique',
        groupe_conflit_id: 'id_article_premier_11223344',
        cible_numero: '12',
      },
      {
        id: 'AM-4',
        numero: '68',
        article: 'Article PREMIER',
        auteurs: ['M. Delta'],
        statut: 'Discussion commune',
        groupe_conflit_id: 'dc_article_premier_p_25',
        cible_numero: '25',
      },
    ]

    const rtf = generateRtfPrejaune(amendments)
    expect(rtf).toContain('ARTICLE PREMIER')
    expect(rtf).not.toContain('ARTICLE Article PREMIER')
    expect(rtf).toContain('[Id.]')
    expect(rtf).toContain('[Dc.]')
    // Crochets d'ouverture (╓ = \u9555?) et de fermeture (╙ = \u9561?)
    expect(rtf).toContain('\\u9555?')
    expect(rtf).toContain('\\u9561?')
  })
})
