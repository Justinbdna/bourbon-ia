/**
 * Web Worker — Moteur de pré-tri déterministe (off-Main-Thread).
 * Reçoit un tableau d'amendements via postMessage, effectue le tri
 * et la détection des identiques/doublons, puis renvoie le résultat.
 */

function extraireActionEtNiveau(texte) {
  const t = (texte || '').toLowerCase().trim()
  if (t.startsWith('supprimer cet article') || t.startsWith("supprimer l'article")) {
    return { priorite: 1, type: 'article_suppression' }
  }
  if (t.startsWith('rédiger ainsi cet article') || t.startsWith("rédiger ainsi l'article")) {
    return { priorite: 2, type: 'article_redaction' }
  }
  if (t.includes("supprimer l'alinéa") || t.includes('supprimer les alinéas')) {
    return { priorite: 3, type: 'alinea_suppression' }
  }
  if (t.includes("rédiger ainsi l'alinéa") || t.includes('rédiger ainsi cet alinéa')) {
    return { priorite: 4, type: 'alinea_redaction' }
  }
  return { priorite: 5, type: 'restreint' }
}

function normaliserTexte(texte) {
  return (texte || '')
    .replace(/[.,;!?:"'(){}[\]\-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

function preSortAmendements(amendements) {
  if (!amendements || amendements.length === 0) return []

  const enriched = amendements.map((am) => {
    const texte = am.dispositif || am.texte || ''
    const { priorite } = extraireActionEtNiveau(texte)
    return { ...am, _priorite: priorite }
  })

  enriched.sort((a, b) => {
    const artA = String(a.article || '')
    const artB = String(b.article || '')
    const artCmp = artA.localeCompare(artB, 'fr', { numeric: true })
    if (artCmp !== 0) return artCmp
    if (a._priorite !== b._priorite) return a._priorite - b._priorite
    return String(a.numero || '').localeCompare(String(b.numero || ''), 'fr', { numeric: true })
  })

  const groupes = new Map()
  for (const am of enriched) {
    const dispo = normaliserTexte(am.dispositif || am.texte || '')
    const art = normaliserTexte(String(am.article || ''))
    if (!dispo) continue
    const key = `${art}|||${dispo}`
    if (!groupes.has(key)) groupes.set(key, [])
    groupes.get(key).push(am)
  }

  let grpCounter = 0
  for (const [, members] of groupes) {
    if (members.length >= 2) {
      grpCounter++
      const groupeId = `grp-doc-${grpCounter}`
      const authorMap = new Map()
      for (const m of members) {
        const author = (m.auteurs && m.auteurs.length > 0) ? m.auteurs[0] : (m.rapporteur ? 'Rapporteur' : 'Inconnu')
        if (!authorMap.has(author)) authorMap.set(author, [])
        authorMap.get(author).push(m)
      }
      const isIdentique = authorMap.size > 1
      for (const [, subMembers] of authorMap) {
        if (subMembers.length > 1) {
          for (let i = 0; i < subMembers.length; i++) {
            const type = (isIdentique && i === 0) ? 'identiques' : 'doublon'
            subMembers[i]._groupe = { type, groupe_id: groupeId }
            subMembers[i]._skipLLM = true
          }
        } else if (isIdentique) {
          subMembers[0]._groupe = { type: 'identiques', groupe_id: groupeId }
          subMembers[0]._skipLLM = true
        }
      }
    }
  }

  return enriched.map((am, i) => {
    const result = { ...am }
    result._rang = i + 1
    if (!result._groupe) result._groupe = null
    if (!result._skipLLM) result._skipLLM = false
    delete result._priorite
    return result
  })
}

self.onmessage = function (e) {
  const result = preSortAmendements(e.data)
  self.postMessage(result)
}
