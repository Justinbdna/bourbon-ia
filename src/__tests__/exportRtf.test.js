import { describe, it, expect } from 'vitest'
import { rtfEscape, generateRtfPrejaune } from '../utils/exportRtf'

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
})
