/**
 * src/utils/sanitize.js — Assainissement HTML, décodage d'entités et tri parlementaire
 * =====================================================================================
 * Purge rigoureusement les balises HTML (<p style="...">, <br/>, <div>, y compris
 * doublement échappées) et décode toutes les entités HTML/XML de l'Assemblée nationale.
 */

export function stripHtmlTags(html) {
  if (!html || typeof html !== 'string') return html || ''
  return html
    // Décodage préalable des chevrons échappés pour attraper les balises encodées (&lt;p style=...&gt;)
    .replace(/&lt;(\/?[a-zA-Z][^&]*?)&gt;/g, '<$1>')
    // Remplacement des sauts de ligne et paragraphes HTML par un espace propre
    .replace(/<\/p>\s*<p[^>]*>/gi, ' ')
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<\/(p|div)>/gi, ' ')
    // Suppression stricte de toutes les balises HTML (<p style="text-align: justify;">, etc.)
    .replace(/<[^>]+>/g, '')
    // Décodage des espaces insécables et tirets cadratins / insécables
    .replace(/&nbsp;/gi, ' ')
    .replace(/&#160;/gi, ' ')
    .replace(/&#x00a0;/gi, ' ')
    .replace(/&#x2011;/gi, '‑')
    // Décodage des apostrophes et guillemets typographiques français/anglais
    .replace(/&rsquo;/gi, '’')
    .replace(/&lsquo;/gi, '‘')
    .replace(/&ldquo;/gi, '“')
    .replace(/&rdquo;/gi, '”')
    .replace(/&laquo;/gi, '«')
    .replace(/&raquo;/gi, '»')
    .replace(/&quot;/gi, '"')
    .replace(/&apos;/gi, "'")
    .replace(/&#39;/gi, "'")
    .replace(/&ndash;/gi, '–')
    .replace(/&mdash;/gi, '—')
    .replace(/&oelig;/gi, 'œ')
    .replace(/&OElig;/gi, 'Œ')
    .replace(/&hellip;/gi, '…')
    // Décodage des entités numériques décimales et hexadécimales génériques
    .replace(/&#(\d+);/g, (_, dec) => {
      const code = parseInt(dec, 10)
      return code === 160 ? ' ' : String.fromCodePoint(code)
    })
    .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => {
      const code = parseInt(hex, 16)
      return code === 160 ? ' ' : String.fromCodePoint(code)
    })
    // Décodage des comparateurs et esperluettes
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&amp;/gi, '&')
    // Filet de sécurité final contre toute balise résiduelle
    .replace(/<\/?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^>]*)?>/g, '')
    // Remplacement des espaces multiples tout en préservant la lisibilité
    .replace(/[ \t]+/g, ' ')
    .replace(/\n\s*\n+/g, '\n\n')
    .trim()
}

export const stripHtmlForDisplay = stripHtmlTags

const LATIN_SUFFIX_RANK = {
  bis: 1,
  ter: 2,
  quater: 3,
  quinquies: 4,
  sexies: 5,
  septies: 6,
  octies: 7,
  nonies: 8,
  decies: 9,
  undecies: 10,
  duodecies: 11,
}

/**
 * Calcule la clé de tri parlementaire stricte [num_article, pos_relative, suffix_rank]
 * garantissant que Article PREMIER (1) précède toujours Article 2 (2).
 */
export function articleSortKey(articleInput) {
  const raw = typeof articleInput === 'object' && articleInput !== null
    ? (articleInput.article || articleInput.article_vise || '')
    : String(articleInput || '')
  const s = raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()
    .trim()

  if (!s) return [9999, 0, 0]

  if (/\b(TITRE|INTITULE|PREAMBULE|LIMINAIRE)\b/.test(s)) {
    return [0, 0, 0]
  }

  let posArticle = 0
  if (/\bAVANT\b/.test(s)) {
    posArticle = -1
  } else if (/\bAPRES\b/.test(s) || /\bADDITIONNEL\b/.test(s)) {
    posArticle = 1
  }

  let suffixRank = 0
  for (const [latin, rank] of Object.entries(LATIN_SUFFIX_RANK)) {
    if (new RegExp(`\\b${latin.toUpperCase()}\\b`).test(s)) {
      suffixRank = rank
      posArticle = 1
      break
    }
  }
  if (posArticle === 1 && suffixRank === 0) {
    suffixRank = 1
  }

  if (/\b(PREMIER|1ER|UNIQUE|LIMINAIRE)\b/.test(s)) {
    return [1, posArticle, suffixRank]
  }

  const mNum = s.match(/\b(\d+)\b/)
  if (mNum) {
    return [parseInt(mNum[1], 10), posArticle, suffixRank]
  }

  return [9999, posArticle, suffixRank]
}

export function compareArticles(a, b) {
  const ka = articleSortKey(a)
  const kb = articleSortKey(b)
  for (let i = 0; i < 3; i++) {
    if (ka[i] !== kb[i]) return ka[i] - kb[i]
  }
  return 0
}
