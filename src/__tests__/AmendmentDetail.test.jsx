import { describe, it, expect } from 'vitest'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import AmendmentDetail, {
  computeWordDiff,
  extractTargetedLawSegment,
  formatCleanArticleHeading,
} from '../components/AmendmentDetail'

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
})
