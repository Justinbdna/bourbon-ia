// Génère un document RTF au format "préjaune" de l'Assemblée nationale :
// amendements organisés par article, avec crochets Dc. (discussion commune)
// et Id. (identiques) tracés à l'aide de tabulations et de caractères de
// dessin de boîte (╓ ║ ╙), comme dans les préjaunes officiels.

const GROUP_LABELS = {
  identiques: 'Id.',
  discussion_commune: 'Dc.',
}

// Convertit une chaîne JS en texte RTF valide : échappe les caractères
// spéciaux RTF (\ { }) et encode tout caractère non-ASCII (accents,
// caractères de dessin de boîte) en séquence \uNNNN? — la méthode la plus
// robuste pour générer du RTF depuis du JS, sans se soucier de l'encodage.
function rtfEscape(str) {
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

// Pour chaque amendement (dans l'ordre d'affichage courant), détermine le
// label ("Dc."/"Id.", uniquement sur la première ligne du groupe) et le
// glyphe de crochet (╓ premier, ║ milieu, ╙ dernier) à afficher.
// Les doublons et additionnels ne sont pas mis entre crochets dans le
// préjaune officiel : seuls Dc. et Id. le sont.
function computeLineDecorations(amendments) {
  const decos = []
  let i = 0
  while (i < amendments.length) {
    const g = amendments[i].resultat_ia?.groupe
    const bracketable = g?.groupe_id && GROUP_LABELS[g.type]

    if (!bracketable) {
      decos.push({ label: '', glyph: '' })
      i += 1
      continue
    }

    let j = i + 1
    while (j < amendments.length && amendments[j].resultat_ia?.groupe?.groupe_id === g.groupe_id) {
      j += 1
    }
    const label = GROUP_LABELS[g.type]
    for (let k = i; k < j; k++) {
      let glyph = '║'
      if (k === i) glyph = '╓'
      else if (k === j - 1) glyph = '╙'
      decos.push({ label: k === i ? label : '', glyph })
    }
    i = j
  }
  return decos
}

// Déduit l'en-tête de section ("ARTICLE 5", "APRÈS L'ARTICLE 12") à partir
// du champ `article`. Les articles additionnels ("12 bis (nouveau)") sont
// regroupés sous un unique "APRÈS L'ARTICLE 12", comme dans le préjaune réel.
function computeSectionHeader(article) {
  const m = String(article).match(
    /^(\d+)\s*(bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies)?\s*\(nouveau\)/i
  )
  if (m) return `APRÈS L'ARTICLE ${m[1]}`
  return `ARTICLE ${article}`
}

// Construit la séquence de tabulations d'une ligne : 3 tabulations pour
// atteindre la colonne du label, 1 pour celle du glyphe, 1 pour celle du
// contenu — soit toujours 5 tabulations au total, que les colonnes
// intermédiaires soient vides ou non (schéma cohérent sur toutes les lignes).
function buildLine(label, glyph, content) {
  let s = '\\tab \\tab \\tab '
  s += label ? rtfEscape(label) : ''
  s += '\\tab '
  s += glyph ? rtfEscape(glyph + ' ') : ''
  s += '\\tab '
  s += rtfEscape(content)
  return s
}

export function generateRtfPrejaune(amendments) {
  const decos = computeLineDecorations(amendments)
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

  const titre = amendments[0]?.texte_examine?.titre
  if (titre) {
    parts.push(`\\pard\\f0\\fs24\\b\\ul ${rtfEscape(titre)}\\b0\\ul0\\par\\par`)
  }

  let lastHeader = null
  amendments.forEach((a, idx) => {
    const header = computeSectionHeader(a.article)
    if (header !== lastHeader) {
      if (lastHeader !== null) parts.push('\\par')
      parts.push(`\\pard\\f0\\fs24\\b ${rtfEscape(header)}\\b0\\par`)
      lastHeader = header
    }
    const deco = decos[idx]
    const auteursText = a.auteurs && a.auteurs.length ? a.auteurs.join(', ') : 'la commission'
    const content = `Adt n\u00b0 ${a.numero}${a.rectification ? ' ' + a.rectification : ''} de ${auteursText}`
    parts.push(
      `\\pard\\f0\\fs22\\tx851\\tx1321\\tx1985 ${buildLine(deco.label, deco.glyph, content)}\\par`
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
