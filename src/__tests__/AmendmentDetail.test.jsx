import { describe, it, expect } from 'vitest'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import AmendmentDetail, {
  computeWordDiff,
  extractTargetedLawSegment,
  formatCleanArticleHeading,
} from '../components/AmendmentDetail'
import { filtrerAmendements } from '../components/AmendmentTable'
import { generateRtfPrejaune } from '../utils/exportRtf'

describe('AmendmentDetail.jsx — Stabilité Hooks, Métadonnées & Comparateur Loi/Amendement', () => {
  const sampleWithLaw = {
    id: 'AM-100',
    uid: 'AM-100',
    numero: '100',
    article: 'Article 3',
    auteur_nom: 'Lachaud',
    auteur_prenom: 'Bastien',
    auteur_trigramme: 'BLA',
    groupe_politique: 'LFI-NFP',
    groupRef: 'PO845413',
    dateDepot: '2026-03-15',
    texte_loi_reference: '(1) Le délai de déclaration est fixé à trente jours.\n(2) Un décret précise les modalités.',
    dispositif: "À l'alinéa 1, substituer aux mots : « trente jours » les mots : « soixante jours ».",
    expose_sommaire: 'Doublement du délai de déclaration.',
    resultat_ia: {
      rang: 1,
      statut: 'Discussion commune',
      groupe: { type: 'discussion_commune', groupe_id: 'DC-ART3' },
      justification: 'Divergence sur la durée du délai.',
    },
  }

  const sampleWithoutLaw = {
    id: 'AM-101',
    uid: 'AM-101',
    numero: '101',
    article: 'Article 9',
    auteurs: ['M. Jean Dupont'],
    groupe_politique: 'EPR',
    dispositif: 'Supprimer cet article.',
    expose_sommaire: 'Amendement de suppression.',
  }

  it('monte sans erreur React Hooks dans tous les états (null, isLoading, amendement complet)', () => {
    const htmlEmpty = renderToStaticMarkup(<AmendmentDetail amendment={null} allAmendments={[]} />)
    expect(htmlEmpty).toContain('Sélectionne un amendement dans le tableau')

    const htmlLoading = renderToStaticMarkup(<AmendmentDetail amendment={sampleWithLaw} isLoading={true} />)
    expect(htmlLoading).toContain('animate-pulse')

    const htmlFull = renderToStaticMarkup(
      <AmendmentDetail amendment={sampleWithLaw} allAmendments={[sampleWithLaw, sampleWithoutLaw]} />
    )
    expect(htmlFull).toContain('Article 3 — Amendement n° 100')
    expect(htmlFull).toContain('2026-03-15')
    expect(htmlFull).toContain('Discussion commune')
    expect(htmlFull).toContain('⚖️ Comparer avec le texte de loi initial')
  })

  it('extrait l’alinéa ciblé du texte de loi de référence et calcule le diff mot-à-mot', () => {
    const segment = extractTargetedLawSegment(sampleWithLaw.texte_loi_reference, sampleWithLaw.dispositif)
    expect(segment).toBe('Le délai de déclaration est fixé à trente jours.')

    const diff = computeWordDiff(segment, 'Le délai de déclaration est fixé à soixante jours.')
    const deleted = diff.filter((d) => d.type === 'del').map((d) => d.text)
    const added = diff.filter((d) => d.type === 'add').map((d) => d.text)

    expect(deleted).toContain('trente')
    expect(added).toContain('soixante')
  })

  it('affiche le comparateur visuel Loi initiale vs Amendement et le repli propre sans texte de loi', () => {
    const htmlDiffLaw = renderToStaticMarkup(
      <AmendmentDetail amendment={sampleWithLaw} allAmendments={[sampleWithLaw]} initialCompareWithLaw={true} />
    )
    expect(htmlDiffLaw).toContain('data-testid="law-diff-view"')
    expect(htmlDiffLaw).toContain('texte de loi initial')
    expect(htmlDiffLaw).toContain('modification proposée')
    expect(htmlDiffLaw).toContain('line-through')

    const htmlFallback = renderToStaticMarkup(
      <AmendmentDetail amendment={sampleWithoutLaw} allAmendments={[sampleWithoutLaw]} initialCompareWithLaw={true} />
    )
    expect(htmlFallback).toContain('data-testid="law-diff-fallback"')
    expect(htmlFallback).toContain('Texte de loi initial non disponible')
  })

  it('nettoie les titres d’articles dupliqués via formatCleanArticleHeading', () => {
    expect(formatCleanArticleHeading('Article Article PREMIER')).toBe('Article PREMIER')
    expect(formatCleanArticleHeading('3 bis')).toBe('Article 3 bis')
  })

  it('filtre dynamiquement les amendements par Article et par Groupe politique', () => {
    const liasse = [
      { id: '1', numero: '1', article: 'Article PREMIER', groupe_politique: 'LFI-NFP', dispositif: 'Texte 1' },
      { id: '2', numero: '2', article: 'Article 3 BIS', groupe_politique: 'EPR', dispositif: 'Texte 2' },
      { id: '3', numero: '3', article: 'Article 3 BIS', groupe_politique: 'LFI-NFP', dispositif: 'Texte 3' },
    ]

    const parArt3Bis = filtrerAmendements(liasse, { article: '3 BIS', groupe: '' })
    expect(parArt3Bis.map((a) => a.id)).toEqual(['2', '3'])

    const parGroupeLfi = filtrerAmendements(liasse, { article: '', groupe: 'LFI-NFP' })
    expect(parGroupeLfi.map((a) => a.id)).toEqual(['1', '3'])

    const combine = filtrerAmendements(liasse, { article: '3 BIS', groupe: 'EPR' })
    expect(combine.map((a) => a.id)).toEqual(['2'])

    const reinitialise = filtrerAmendements(liasse, { article: '', groupe: '' })
    expect(reinitialise.length).toBe(3)
  })

  it('affiche la pastille d’arbitrage manuel, l’alerte d’amendement tombant et les persiste dans l’export RTF', () => {
    const amArbitre = {
      ...sampleWithLaw,
      statut: 'Identique',
      cible_numero: '101',
      arbitrage_manuel: true,
      tombe_si_adoption_de: ['10', '11'],
      resultat_ia: {
        ...sampleWithLaw.resultat_ia,
        statut: 'Identique',
        cible_numero: '101',
        groupe: { type: 'identiques', groupe_id: 'id_manuel_101' },
      },
    }

    const html = renderToStaticMarkup(<AmendmentDetail amendment={amArbitre} allAmendments={[amArbitre, sampleWithoutLaw]} />)
    expect(html).toContain('data-testid="badge-arbitrage-manuel"')
    expect(html).toContain('Arbitré manuellement')
    expect(html).toContain('Tombe si adoption de 10, 11')
    expect(html).toContain('data-testid="select-arbitrage-statut"')

    const rtf = generateRtfPrejaune([amArbitre])
    expect(rtf).toContain('[Id.]')
    expect(rtf).toContain('Tombe si adoption de 10, 11')
  })
})
