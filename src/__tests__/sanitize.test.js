import { describe, it, expect } from 'vitest'
import { stripHtmlForDisplay } from '../utils/sanitize'
import { formatCleanArticleHeading } from '../components/AmendmentDetail'

describe('Assainissement HTML et Formatage des Titres Légistiques', () => {
  it('stripHtmlForDisplay supprime les balises <p style="..."> et retourne le texte pur', () => {
    const raw = '<p style="text-align: justify;">Supprimer cet article.</p>'
    expect(stripHtmlForDisplay(raw)).toBe('Supprimer cet article.')
  })

  it('stripHtmlForDisplay décode correctement les entités XML/HTML de l\'Assemblée', () => {
    const raw = '<p>Mme&nbsp;Joncour&#160;&#x2011; &laquo;Article 1er&raquo; &amp; &quot;Gage&quot;</p>'
    expect(stripHtmlForDisplay(raw)).toBe('Mme Joncour ‑ «Article 1er» & "Gage"')
  })

  it('stripHtmlForDisplay gère les sauts de ligne <br/> et retours paragraphe proprement', () => {
    const raw = '<p>Alinéa 1.<br/>Alinéa 2.</p><p>Alinéa 3.</p>'
    expect(stripHtmlForDisplay(raw)).toBe('Alinéa 1. Alinéa 2. Alinéa 3.')
  })

  it('formatCleanArticleHeading évite la duplication "Article Article PREMIER"', () => {
    expect(formatCleanArticleHeading('Article Article PREMIER')).toBe('Article PREMIER')
    expect(formatCleanArticleHeading('Article PREMIER')).toBe('Article PREMIER')
    expect(formatCleanArticleHeading('article premier')).toBe('Article premier')
  })

  it('formatCleanArticleHeading ne préfixe jamais si déjà précédé de "Après l\'article" ou "Avant l\'article"', () => {
    expect(formatCleanArticleHeading("Après l'article 2")).toBe("Après l'article 2")
    expect(formatCleanArticleHeading("Avant l'article PREMIER")).toBe("Avant l'article PREMIER")
    expect(formatCleanArticleHeading("APRÈS L'ARTICLE 3")).toBe("APRÈS L'ARTICLE 3")
  })

  it('formatCleanArticleHeading préfixe correctement les numéros bruts', () => {
    expect(formatCleanArticleHeading('PREMIER')).toBe('Article PREMIER')
    expect(formatCleanArticleHeading('2')).toBe('Article 2')
    expect(formatCleanArticleHeading('10 bis')).toBe('Article 10 bis')
  })
})
