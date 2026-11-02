import { describe, it, expect } from 'vitest'
import { stripHtmlForDisplay, stripHtmlTags, articleSortKey, compareArticles } from '../utils/sanitize'
import { formatCleanArticleHeading } from '../components/AmendmentDetail'
import { resolvePoliticalGroup } from '../components/amendment/PoliticalGroupTag'

describe('Assainissement HTML, Tri Parlementaire et Séparation Groupe/Statut', () => {
  it('stripHtmlTags supprime les balises <p style="text-align: justify;"> et retourne le texte pur', () => {
    const raw = '<p style="text-align: justify;">Supprimer cet article.</p>'
    expect(stripHtmlTags(raw)).toBe('Supprimer cet article.')
    expect(stripHtmlForDisplay(raw)).toBe('Supprimer cet article.')
  })

  it('stripHtmlTags décode correctement les entités XML/HTML (&rsquo;, &nbsp;, &#160;, &quot;) et balises doublement échappées', () => {
    const raw = '<p>Mme&nbsp;Joncour&#160;&#x2011; &laquo;L&rsquo;article 1er&raquo; &amp; &quot;Gage&quot;</p>'
    expect(stripHtmlTags(raw)).toBe('Mme Joncour ‑ «L’article 1er» & "Gage"')

    const doubleEscaped = '&lt;p style="text-align: justify;"&gt;Supprimer cet article.&lt;/p&gt;'
    expect(stripHtmlTags(doubleEscaped)).toBe('Supprimer cet article.')
  })

  it('stripHtmlForDisplay gère les sauts de ligne <br/> et retours paragraphe proprement', () => {
    const raw = '<p>Alinéa 1.<br/>Alinéa 2.</p><p>Alinéa 3.</p>'
    expect(stripHtmlForDisplay(raw)).toBe('Alinéa 1. Alinéa 2. Alinéa 3.')
  })

  it('articleSortKey garantit que Article PREMIER < Article 2 < Article 10', () => {
    const k1 = articleSortKey('Article PREMIER')
    const k2 = articleSortKey('Article 2')
    const k10 = articleSortKey('Article 10')
    expect(k1[0]).toBeLessThan(k2[0])
    expect(k2[0]).toBeLessThan(k10[0])

    const list = [
      { article: 'Article 10' },
      { article: 'Article 2' },
      { article: "APRÈS L'ARTICLE PREMIER" },
      { article: 'Article PREMIER' },
      { article: "AVANT L'ARTICLE PREMIER" },
      { article: 'TITRE' },
    ]
    const sorted = [...list].sort(compareArticles).map((x) => x.article)
    expect(sorted).toEqual([
      'TITRE',
      "AVANT L'ARTICLE PREMIER",
      'Article PREMIER',
      "APRÈS L'ARTICLE PREMIER",
      'Article 2',
      'Article 10',
    ])
  })

  it('resolvePoliticalGroup résout les codes organes AN et exclut les statuts de tri', () => {
    expect(resolvePoliticalGroup('', 'PO845413', [])).toBe('LFI-NFP')
    expect(resolvePoliticalGroup('RN', '', [])).toBe('RN')
    expect(resolvePoliticalGroup('Isolé', '', [])).toBe('')
    expect(resolvePoliticalGroup('Discussion commune', '', ['Mme Martin (EcoS)'])).toBe('EcoS')
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
