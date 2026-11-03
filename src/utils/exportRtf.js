// Génère un document RTF au format "préjaune" de l'Assemblée nationale :
// amendements organisés par article, avec crochets Dc. (discussion commune)
// et Id. (identiques) tracés à l'aide de tabulations et de caractères de
// dessin de boîte (╓ ║ ╙), comme dans les préjaunes officiels.

const GROUP_LABELS = {
  identiques: 'Id.',
  discussion_commune: 'Dc.',
}

const INVALID_GROUP_TOKENS = new Set([
  '',
  'NULL',
  'UNDEFINED',
  'NONE',
  'NUMERO',
  'NUMÉRO',
  'ISOLE',
  'ISOLÉ',
  'ARTICLE PREMIER',
  'ARTICLE 1ER',
])

/**
 * Vérifie qu'un identifiant de groupe ou numéro cible n'est pas un faux positif
 * ("NUMERO", "Article PREMIER", "null", etc.).
 */
export function isValidGroupIdentifier(val) {
  if (val == null) return false
  const s = String(val).trim()
  if (!s) return false
  const upper = s.toUpperCase()
  if (INVALID_GROUP_TOKENS.has(upper)) return false
  if (/^ARTICLE\s+/i.test(s)) return false
  return true
}

/**
 * Résout le descripteur de groupe ({ type: 'identiques' | 'discussion_commune', groupe_id })
 * d'un amendement à partir des champs du moteur déterministe Python ou de `resultat_ia`.
 */
export function resolveAmendmentGroup(a) {
  if (!a || typeof a !== 'object') return null
  const statut = a.resultat_ia?.statut || a.statut || ''
  if (statut === 'Isolé') return null

  const explicitType = a.resultat_ia?.groupe?.type
  let type = null
  if (statut === 'Identique' || statut === 'Identiques' || explicitType === 'identiques') {
    type = 'identiques'
  } else if (
    statut === 'Discussion commune' ||
    statut === 'Incompatible' ||
    explicitType === 'discussion_commune'
  ) {
    type = 'discussion_commune'
  }

  const candidates = [
    a.groupe_conflit_id,
    a.resultat_ia?.groupe_conflit_id,
    a.resultat_ia?.groupe?.groupe_id,
    a.cible_numero,
    a.resultat_ia?.cible_numero,
    a.resultat_ia?.cible,
    a.resultat_ia?.id_discussion_cible,
  ]

  let validId = null
  for (const c of candidates) {
    if (isValidGroupIdentifier(c)) {
      validId = String(c).trim()
      break
    }
  }

  if (!validId) return null

  if (!type) {
    if (validId.startsWith('id_')) type = 'identiques'
    else if (validId.startsWith('dc_')) type = 'discussion_commune'
  }

  if (!type || !GROUP_LABELS[type]) return null

  // Si l'identifiant est simplement un numéro cible (sans préfixe id_/dc_/GRP),
  // construire une clé canonique symétrique entre le numéro de l'amendement et sa cible
  if (/^\d+$/.test(validId) && a.numero != null && /^\d+$/.test(String(a.numero).trim())) {
    const n1 = String(a.numero).trim()
    const n2 = validId
    const pair = [n1, n2].sort((x, y) => Number(x) - Number(y))
    const sec = computeSectionHeader(a.article || a.article_vise || '')
    validId = `${type}_${sec}_${pair[0]}_${pair[1]}`
  }

  return { type, groupe_id: validId }
}

// Convertit une chaîne JS en texte RTF valide : échappe les caractères
// spéciaux RTF (\ { }) et encode tout caractère non-ASCII (accents,
// caractères de dessin de boîte) en séquence \uNNNN? — la méthode la plus
// robuste pour générer du RTF depuis du JS, sans se soucier de l'encodage.
export function rtfEscape(str) {
  let out = ''
  for (const ch of String(str)) {
    const code = ch.codePointAt(0)
    if (ch === '\\' || ch === '{' || ch === '}') {
      out += '\\' + ch
    } else if (code < 128) {
      out += ch
    } else {
      const signed = code > 32767 ? code - 65536 : code
      out += `\\u${signed}?`
    }
  }
  return out
}

// Regroupe de façon contiguë, au sein de chaque section d'article, les amendements
// partageant le même `groupe_id` valide afin que les crochets ╓ ║ ╙ englobent
// chaque grappe d'identiques ([Id.]) ou de discussion commune ([Dc.]).
function groupContiguouslyBySection(amendments) {
  if (!Array.isArray(amendments) || amendments.length <= 1) return amendments || []
  const result = []
  let i = 0
  while (i < amendments.length) {
    const sectionHeader = computeSectionHeader(amendments[i].article || amendments[i].article_vise || '')
    let j = i + 1
    while (
      j < amendments.length &&
      computeSectionHeader(amendments[j].article || amendments[j].article_vise || '') === sectionHeader
    ) {
      j += 1
    }

    const sectionItems = amendments.slice(i, j)
    const buckets = new Map()
    const orderedKeys = []

    sectionItems.forEach((item, idx) => {
      const grp = resolveAmendmentGroup(item)
      const key = grp ? `grp:${grp.type}:${grp.groupe_id}` : `single:${idx}`
      if (!buckets.has(key)) {
        buckets.set(key, [])
        orderedKeys.push(key)
      }
      buckets.get(key).push(item)
    })

    for (const k of orderedKeys) {
      result.push(...buckets.get(k))
    }

    i = j
  }
  return result
}

// Pour chaque amendement (dans l'ordre d'affichage courant), détermine le
// label ("Dc."/"Id.", uniquement sur la première ligne du groupe) et le
// glyphe de crochet (╓ premier, ║ milieu, ╙ dernier) à afficher.
// Les doublons et additionnels ne sont pas mis entre crochets dans le
// préjaune officiel : seuls Dc. et Id. le sont.
function computeLineDecorations(amendments) {
  const decos = []
  let i = 0
  while (i < amendments.length) {
    const g = resolveAmendmentGroup(amendments[i])
    const bracketable = g?.groupe_id && GROUP_LABELS[g.type]

    if (!bracketable) {
      decos.push({ label: '', glyph: '' })
      i += 1
      continue
    }

    let j = i + 1
    while (j < amendments.length) {
      const gj = resolveAmendmentGroup(amendments[j])
      if (gj?.groupe_id === g.groupe_id && gj?.type === g.type) {
        j += 1
      } else {
        break
      }
    }
    const label = GROUP_LABELS[g.type]
    if (j - i === 1) {
      decos.push({ label, glyph: '╓' })
    } else {
      for (let k = i; k < j; k++) {
        let glyph = '║'
        if (k === i) glyph = '╓'
        else if (k === j - 1) glyph = '╙'
        decos.push({ label: k === i ? label : '', glyph })
      }
    }
    i = j
  }
  return decos
}

// Déduit l'en-tête de section ("ARTICLE 5", "APRÈS L'ARTICLE 12") à partir
// du champ `article`. Les articles additionnels ("12 bis (nouveau)") sont
// regroupés sous un unique "APRÈS L'ARTICLE 12", comme dans le préjaune réel.
function computeSectionHeader(article) {
  const raw = String(article || '').trim()
  const mApres = raw.match(/apr[eè]s\s+l['’]article\s+(.+)$/i)
  if (mApres) {
    return `APRÈS L'ARTICLE ${mApres[1].trim().toUpperCase()}`
  }
  const m = raw.match(
    /^(?:article\s+)?(\d+|premier|1er)\s*(bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies)?\s*\(nouveau\)/i
  )
  if (m) return `APRÈS L'ARTICLE ${m[1].toUpperCase()}`
  const stripped = raw.replace(/^article\s+/i, '').trim()
  return `ARTICLE ${stripped || raw}`
}

// Construit la séquence de tabulations d'une ligne : 3 tabulations pour
// atteindre la colonne du label, 1 pour celle du glyphe, 1 pour celle du
// contenu — soit toujours 5 tabulations au total, que les colonnes
// intermédiaires soient vides ou non (schéma cohérent sur toutes les lignes).
function buildLine(label, glyph, escapedContent) {
  let s = '\\tab \\tab \\tab '
  s += label ? rtfEscape(label) : ''
  s += '\\tab '
  s += glyph ? rtfEscape(glyph + ' ') : ''
  s += '\\tab '
  s += escapedContent
  return s
}

export function generateRtfPrejaune(amendments) {
  const orderedAmendments = groupContiguouslyBySection(amendments)
  const decos = computeLineDecorations(orderedAmendments)
  const parts = []

  parts.push('{\\rtf1\\ansi\\ansicpg1252\\deff0')
  parts.push('{\\fonttbl{\\f0\\froman\\fcharset0 Times New Roman;}}')
  parts.push('\\paperw11907\\paperh16840\\margl1843\\margr1418\\margt850\\margb567')
  parts.push('\\pard\\qc\\f0\\fs24\\b Version provisoire du pr\\u233?-jaune\\b0\\par')
  parts.push(
    `\\pard\\qc\\f0\\fs18\\i G\\u233?n\\u233?r\\u233? le ${new Date().toLocaleDateString(
      'fr-FR'
    )} \\u8212? Dc. = discussion commune, Id. = identiques\\i0\\par\\par`
  )

  const titre = orderedAmendments[0]?.texte_examine?.titre
  if (titre) {
    parts.push(`\\pard\\f0\\fs24\\b\\ul ${rtfEscape(titre)}\\b0\\ul0\\par\\par`)
  }

  let lastHeader = null
  orderedAmendments.forEach((a, idx) => {
    const header = computeSectionHeader(a.article || a.article_vise)
    if (header !== lastHeader) {
      if (lastHeader !== null) parts.push('\\par')
      parts.push(`\\pard\\f0\\fs24\\b ${rtfEscape(header)}\\b0\\par`)
      lastHeader = header
    }
    const deco = decos[idx]
    const auteursArr = Array.isArray(a.auteurs) ? a.auteurs : a.auteurs ? [String(a.auteurs)] : []
    const auteursText = auteursArr.length ? auteursArr.join(', ') : 'la commission'

    const resolvedGrp = resolveAmendmentGroup(a)
    let prefix = ''
    if (resolvedGrp?.type === 'discussion_commune') {
      prefix = '\\b [Dc.]\\b0  '
    } else if (resolvedGrp?.type === 'identiques') {
      prefix = '\\b [Id.]\\b0  '
    }

    const rawContent = `Adt n\u00b0 ${a.numero}${a.rectification ? ' ' + a.rectification : ''} de ${auteursText}`
    const escapedContent = prefix + rtfEscape(rawContent)

    parts.push(
      `\\pard\\f0\\fs22\\tx851\\tx1321\\tx1985 ${buildLine(deco.label, deco.glyph, escapedContent)}\\par`
    )
  })

  parts.push('}')
  return parts.join('\n')
}

export function downloadRtf(amendments, filename) {
  const rtf = generateRtfPrejaune(amendments)
  const blob = new Blob([rtf], { type: 'application/rtf' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
