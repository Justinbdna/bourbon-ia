/**
 * Portage JavaScript du moteur de tri déterministe de Yassine (sorting_engine.py).
 * Ce tri est purement mécanique (Regex sur le chapeau du dispositif), sans IA,
 * pour garantir le respect des procédures de classement de l'Assemblée nationale.
 *
 * Hiérarchie stricte du classement :
 * 1. Suppression de l'article (impact maximal, fait tomber les autres)
 * 2. Rédaction globale de l'article
 * 3. Suppression de l'alinéa
 * 4. Rédaction globale de l'alinéa
 * 5. Point d'impact restreint (mot, phrase, substitution)
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

/**
 * Normalise un texte pour comparaison d'identité mécanique.
 * Retire la ponctuation, les espaces multiples, met en minuscules.
 */
function normaliserTexte(texte) {
  return (texte || '')
    .replace(/[.,;!?:"'(){}[\]\-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

/**
 * Moteur de pré-tri déterministe + détection d'identiques.
 *
 * 1. Trie les amendements par (article, priorité d'action, numéro)
 * 2. Détecte les amendements mécaniquement identiques (même article + même dispositif)
 * 3. Retourne les amendements enrichis de métadonnées internes :
 *    - _rang : position dans l'ordre de tri mécanique
 *    - _groupe : { type, groupe_id } si identique, sinon null
 *    - _skipLLM : true si le classement est déjà déterminé mécaniquement
 *
 * @param {Array} amendements - Liste brute d'amendements normalisés
 * @returns {Array} - Amendements triés et enrichis
 */
export function preSortAmendements(amendements) {
  if (!amendements || amendements.length === 0) return []

  // ÉTAPE 1 : Enrichir avec la priorité d'action
  const enriched = amendements.map((am) => {
    const texte = am.dispositif || am.texte || ''
    const { priorite } = extraireActionEtNiveau(texte)
    return { ...am, _priorite: priorite }
  })

  // ÉTAPE 2 : Tri par doctrine (article → priorité → numéro)
  enriched.sort((a, b) => {
    const artA = String(a.article || '')
    const artB = String(b.article || '')
    const artCmp = artA.localeCompare(artB, 'fr', { numeric: true })
    if (artCmp !== 0) return artCmp
    if (a._priorite !== b._priorite) return a._priorite - b._priorite
    return String(a.numero || '').localeCompare(String(b.numero || ''), 'fr', { numeric: true })
  })

  // ÉTAPE 3 : Détection mécanique des "Identiques" et "Doublons"
  // Clé = article normalisé + dispositif normalisé → liste d'amendements
  const groupes = new Map()
  for (const am of enriched) {
    const dispo = normaliserTexte(am.dispositif || am.texte || '')
    const art = normaliserTexte(String(am.article || ''))
    if (!dispo) continue // pas de dispositif = pas de comparaison possible
    const key = `${art}|||${dispo}`
    if (!groupes.has(key)) groupes.set(key, [])
    groupes.get(key).push(am)
  }

  let grpCounter = 0
  for (const [, members] of groupes) {
    if (members.length >= 2) {
      grpCounter++
      const groupeId = `grp-doc-${grpCounter}`
      
      // Séparer par auteur principal pour identifier les Doublons vs Identiques
      const authorMap = new Map()
      for (const m of members) {
        const author = (m.auteurs && m.auteurs.length > 0) ? m.auteurs[0] : (m.rapporteur ? 'Rapporteur' : 'Inconnu')
        if (!authorMap.has(author)) authorMap.set(author, [])
        authorMap.get(author).push(m)
      }

      const isIdentique = authorMap.size > 1

      for (const [author, subMembers] of authorMap) {
        if (subMembers.length > 1) {
          // Doublons (même auteur, même texte)
          for (let i = 0; i < subMembers.length; i++) {
            const type = (isIdentique && i === 0) ? 'identiques' : 'doublon'
            subMembers[i]._groupe = { type, groupe_id: groupeId }
            subMembers[i]._skipLLM = true
          }
        } else if (isIdentique) {
          // Identiques (auteurs différents)
          subMembers[0]._groupe = { type: 'identiques', groupe_id: groupeId }
          subMembers[0]._skipLLM = true
        }
      }
    }
  }

  // ÉTAPE 4 : Assigner les rangs et nettoyer les champs internes de tri
  return enriched.map((am, i) => {
    const result = { ...am }
    result._rang = i + 1
    if (!result._groupe) result._groupe = null
    if (!result._skipLLM) result._skipLLM = false
    delete result._priorite
    return result
  })
}

/**
 * Version asynchrone du pré-tri : déporte le calcul dans un Web Worker
 * pour éviter de bloquer le Main Thread du navigateur sur les gros volumes.
 * Fallback synchrone si les Workers ne sont pas disponibles.
 */
export function preSortAmendementsAsync(amendements) {
  if (!amendements || amendements.length === 0) return Promise.resolve([])
  
  // Seuil : utiliser le Worker uniquement si le volume le justifie (> 200 amendements)
  if (amendements.length <= 200 || typeof Worker === 'undefined') {
    return Promise.resolve(preSortAmendements(amendements))
  }

  return new Promise((resolve, reject) => {
    try {
      const worker = new Worker(
        new URL('./sortingWorker.js', import.meta.url),
        { type: 'module' }
      )
      worker.onmessage = (e) => {
        resolve(e.data)
        worker.terminate()
      }
      worker.onerror = (err) => {
        console.warn('[Bourbon.IA] Web Worker indisponible, fallback synchrone.', err)
        resolve(preSortAmendements(amendements))
        worker.terminate()
      }
      worker.postMessage(amendements)
    } catch (e) {
      console.warn('[Bourbon.IA] Web Worker non supporté, fallback synchrone.', e)
      resolve(preSortAmendements(amendements))
    }
  })
}
