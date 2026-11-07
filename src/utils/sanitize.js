/**
 * src/utils/sanitize.js — Assainissement HTML et décodage d'entités légistiques
 * ==============================================================================
 * Purge rigoureusement les balises HTML (<p style="...">, <br/>, <div>) et
 * décode toutes les entités HTML/XML issues des données de l'Assemblée nationale.
 */

export function stripHtmlForDisplay(text) {
  if (!text || typeof text !== 'string') return text || ''
  return text
    // Remplacement des sauts de ligne et paragraphes HTML par un espace propre ou un saut
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<\/(p|div)>/gi, ' ')
    // Suppression stricte de toutes les balises HTML
    .replace(/<[^>]+>/g, '')
    // Décodage des espaces insécables et tirets cadratins / insécables
    .replace(/&nbsp;/gi, ' ')
    .replace(/&#160;/gi, ' ')
    .replace(/&#x2011;/gi, '‑')
    // Décodage des guillemets français et anglais
    .replace(/&laquo;/gi, '«')
    .replace(/&raquo;/gi, '»')
    .replace(/&quot;/gi, '"')
    .replace(/&apos;/gi, "'")
    // Décodage des comparateurs et esperluettes
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&amp;/gi, '&')
    // Remplacement des espaces multiples tout en préservant la lisibilité
    .replace(/[ \t]+/g, ' ')
    .replace(/\n\s*\n+/g, '\n\n')
    .trim()
}
