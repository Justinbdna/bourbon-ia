import { getDecryptedSettings } from '../utils/crypto'

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

export class ClassifyError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ClassifyError'
    this.status = status
  }
}

export const LOCAL_PROMPT_SYSTEM = `Administrateur légistique de séance. Compare l'amendement candidat aux amendements déposés sur le même article.
Réponds EXCLUSIVEMENT par un unique objet JSON fermé sur une ligne.
Schéma strict : {"statut":"Isolé"|"Identique"|"Discussion commune","confiance":0.85,"cible":null|"NUMERO","justification":"1 phrase concise"}
Interdiction absolue de générer du texte hors du JSON.`

export const LOCAL_ONE_SHOT_MESSAGES = [
  {
    role: 'user',
    content: "Amendement A (Article 3) : Supprimer l'alinéa 1.",
  },
  {
    role: 'assistant',
    content: '{"statut":"Isolé","confiance":0.95,"cible":null,"justification":"Suppression sans autre amendement concurrent sur cet alinéa."}',
  },
]

export const LOCAL_STOP_SEQUENCES = ['\n\n', '}\n', '\n{', '```']

export const STATUTS_VALIDES = ['Isolé', 'Identique', 'Discussion commune']

/**
 * Parseur JSON chirurgical résilient aux bavardages multi-lignes, balises Markdown et coupures de fin de token.
 * Extrait le premier bloc JSON valide { ... }, tente une fermeture automatique si l'accolade a été tronquée,
 * et applique un repli gracieux vers "Isolé" en cas d'impossibilité de parsing.
 */
export function safeParseJson(rawText) {
  if (!rawText || typeof rawText !== 'string') {
    return {
      statut: 'Isolé',
      confiance: 0.0,
      cible: null,
      justification: 'Repli technique : réponse vide ou absente du modèle.',
    }
  }

  // Nettoyage des éventuels blocs <think> et codeblocks
  const sansThink = rawText.replace(/<think>[\s\S]*?<\/think>/gi, ' ').replace(/```[a-z]*|```/gi, ' ')
  let match = sansThink.match(/\{[\s\S]*?\}/)
  let jsonString = match ? match[0] : null

  // Si pas d'accolade fermante complète, tentative de fermeture automatique résiliente
  if (!jsonString) {
    const debutIdx = sansThink.indexOf('{')
    if (debutIdx !== -1) {
      let extrait = sansThink.slice(debutIdx).trim()
      let inString = false
      let escaped = false
      for (let i = 0; i < extrait.length; i++) {
        const c = extrait[i]
        if (inString) {
          if (escaped) escaped = false
          else if (c === '\\') escaped = true
          else if (c === '"') inString = false
        } else if (c === '"') {
          inString = true
        }
      }
      if (inString) {
        extrait += '"'
      }
      if (!extrait.endsWith('}')) {
        extrait += '}'
      }
      try {
        JSON.parse(extrait)
        jsonString = extrait
      } catch {
        // Réparation impossible, maintien de jsonString = null
      }
    }
  }

  if (!jsonString) {
    return {
      statut: 'Isolé',
      confiance: 0.0,
      cible: null,
      justification: 'Repli technique : aucun objet JSON détecté dans la réponse.',
    }
  }

  try {
    const parsed = JSON.parse(jsonString)
    let statut = parsed.statut
    const rawConfiance = parsed.confiance ?? parsed.niveau_confiance
    const confiance = typeof rawConfiance === 'number' ? rawConfiance : 0.85
    let cible = parsed.cible || parsed.id_discussion_cible || null
    let justification = parsed.justification || parsed.analyse_intention || parsed.analyse_politique || ''

    if (!STATUTS_VALIDES.includes(statut)) {
      if (typeof statut === 'string') {
        const lower = statut.toLowerCase()
        if (lower.includes('identique')) statut = 'Identique'
        else if (lower.includes('discussion') || lower.includes('commune') || lower.includes('similaire')) statut = 'Discussion commune'
        else statut = 'Isolé'
      } else {
        statut = 'Isolé'
      }
      if (!justification) {
        justification = 'Amendement analysé comme isolé sans concurrence directe.'
      }
    }

    if (statut === 'Isolé') {
      cible = null
    }

    return {
      statut,
      confiance: Math.min(1.0, Math.max(0.0, Number(confiance) || 0.85)),
      cible: cible ? String(cible) : null,
      justification: justification || 'Classification sémantique enregistrée.',
    }
  } catch (err) {
    return {
      statut: 'Isolé',
      confiance: 0.0,
      cible: null,
      justification: `Repli technique : erreur d'analyse JSON (${err.message}).`,
    }
  }
}

/**
 * Construit un payload directif et ultra-court pour l'inférence locale (LM Studio / Apple Silicon).
 */
export function buildLocalChatPayload(amendement, candidats = [], options = {}) {
  const { model = 'local-model', temperature = 0.1 } = options
  const article = amendement.article_vise || amendement.article || 'Article'
  const disp = (amendement.dispositif_raw || amendement.dispositif || '').slice(0, 300)
  const expose = (amendement.expose_sommaire || amendement.exposeSommaire || '').slice(0, 180)

  let userMsg = `Amendement candidat (${article}) : ${disp}`
  if (expose) userMsg += ` | Exposé : ${expose}`

  if (candidats.length > 0) {
    userMsg += '\nAmendements concurrents déjà déposés :'
    candidats.slice(0, 5).forEach((c, idx) => {
      const cId = c.id || c.uid || c.id_discussion || `CAND-${idx + 1}`
      const cDisp = (c.dispositif || c.dispositif_raw || '').slice(0, 200)
      userMsg += `\n- [${cId}] : ${cDisp}`
    })
  } else {
    userMsg += '\nAucun autre amendement concurrent sur cette division.'
  }

  return {
    model,
    messages: [
      { role: 'system', content: LOCAL_PROMPT_SYSTEM },
      ...LOCAL_ONE_SHOT_MESSAGES,
      { role: 'user', content: userMsg },
    ],
    temperature,
    max_tokens: 250,
    stop: LOCAL_STOP_SEQUENCES,
  }
}

export async function normalizeAmendments(amendements) {
  const response = await fetch(`${API_BASE_URL}/api/normalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    body: JSON.stringify({ amendements, model: 'openai/gpt-oss-20b' }),
  })
  if (!response.ok) {
    throw new ClassifyError(`Erreur de normalisation: ${await response.text()}`, response.status)
  }
  return await response.json()
}

/**
 * Analyse de surtransposition et de conformité européenne (Chantier 1).
 * Interroge l'endpoint FastAPI /api/v2/surtransposition avec fallback gracieux.
 */
export async function analyzeSurtransposition(amendement, options = {}) {
  const { signal } = options
  try {
    const response = await fetch(`${API_BASE_URL}/api/v2/surtransposition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
      signal,
      body: JSON.stringify({
        amendement_uid: amendement.id || amendement.uid,
        dispositif: amendement.dispositif_raw || amendement.dispositif || '',
        expose_sommaire: amendement.expose_sommaire || amendement.exposeSommaire || '',
        article_vise: amendement.article_vise || amendement.article || '',
        celex_id: amendement.celex_id || null,
      }),
    })
    if (!response.ok) {
      return null
    }
    return await response.json()
  } catch {
    // Mode hors-ligne ou indisponible : repli gracieux
    return null
  }
}

// Réglages IA communs au classement et au résumé (cf. ⚙️ Réglages IA).
function reglagesLLM(aiSettings = {}) {
  const apiKey = (aiSettings.apiKey || '').trim()
  const rawProvider = aiSettings.provider || 'local'
  const provider = (rawProvider !== 'local' && apiKey) ? 'groq' : rawProvider
  const localUrl = (aiSettings.localUrl || 'http://localhost:1234/v1').trim().replace(/\/+$/, '')
  const safeGroqModel = (aiSettings.groqModel && aiSettings.groqModel !== 'llama-3.3-70b-versatile')
    ? aiSettings.groqModel
    : 'openai/gpt-oss-20b'
  return {
    model: provider === 'local' ? (aiSettings.localModel || 'local-model') : safeGroqModel,
    provider,
    llm_endpoint: provider === 'local' ? localUrl : 'https://api.groq.com/openai/v1',
    api_key: apiKey || (provider === 'local' ? 'local-key' : ''),
  }
}

/**
 * Résumé neutre (1 à 2 phrases) d'un amendement, généré par l'IA à la demande.
 * Lève ClassifyError avec un message lisible en cas d'échec.
 */
export async function resumerAmendement(amendement, aiSettings = {}, options = {}) {
  let settings = { ...aiSettings }
  if (!settings.apiKey) {
    try {
      const decrypted = await getDecryptedSettings()
      if (decrypted) {
        settings = { ...decrypted, ...settings, apiKey: settings.apiKey || decrypted.apiKey || '' }
      }
    } catch {
      // ignore
    }
  }

  console.log("[Bourbon.ia] Transmission clé IA :", settings?.apiKey ? "Clé personnalisée injectée" : "Clé serveur par défaut")

  const response = await fetch(`${API_BASE_URL}/api/v2/resumer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    signal: options.signal,
    body: JSON.stringify({
      amendement_uid: amendement.id || amendement.uid || null,
      article: amendement.article || null,
      dispositif: amendement.dispositif || '',
      expose_sommaire: amendement.expose_sommaire || '',
      texte_loi_reference: amendement.texte_loi_reference || null,
      ...reglagesLLM(settings),
    }),
  })
  if (!response.ok) {
    let detail = `Erreur ${response.status}`
    try {
      detail = (await response.json()).detail || detail
    } catch {
      // réponse non JSON : on garde le code HTTP
    }
    throw new ClassifyError(detail, response.status)
  }
  return (await response.json()).resume
}

/**
 * Repli JS local déterministe au cas où le serveur Python est hors-ligne.
 * Applique l'empreinte textuelle (Identiques [Id.]) et la collision d'alinéas (Discussions communes [Dc.]).
 */
export function classifyMechanicallyLocalFallback(amendements = []) {
  const startMs = Date.now()
  const normFp = (txt) =>
    String(txt || '')
      .replace(/<[^>]+>/g, ' ')
      .toLowerCase()
      .replace(/^(?:à|a)\s+l['’]alinéa\s+\d+\s*,?\s*/i, '')
      .replace(/[^\p{L}\p{N}]+/gu, '')
      .trim()

  const byArticle = new Map()
  amendements.forEach((a, idx) => {
    const art = String(a.article_vise || a.article || 'SANS_ARTICLE').trim().toUpperCase()
    if (!byArticle.has(art)) byArticle.set(art, [])
    byArticle.get(art).push({ a, idx })
  })

  const out = amendements.map((a) => ({ ...a }))
  let nbIdentiques = 0
  let nbDc = 0
  let nbIsoles = 0

  for (const [art, items] of byArticle.entries()) {
    const artSlug = art.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'art'
    const fpGroups = new Map()
    for (const item of items) {
      const fp = normFp(item.a.dispositif || item.a.dispositif_raw || '')
      if (fp) {
        if (!fpGroups.has(fp)) fpGroups.set(fp, [])
        fpGroups.get(fp).push(item)
      }
    }

    const handledIdx = new Set()
    for (const [fp, members] of fpGroups.entries()) {
      if (members.length >= 2) {
        const pivotNum = String(members[0].a.numero || members[0].a.id || '')
        const gid = `id_${artSlug}_${fp.slice(0, 8)}`
        for (const m of members) {
          handledIdx.add(m.idx)
          nbIdentiques++
          const num = String(m.a.numero || m.a.id || '')
          const cible = num === pivotNum ? String(members[1].a.numero || members[1].a.id || '') : pivotNum
          const justif =
            num === pivotNum
              ? `Amendement identique au n° ${cible} (pivot de série identique).`
              : `Identique à l'amendement n° ${pivotNum} (dispositif rigoureusement identique).`
          out[m.idx] = {
            ...out[m.idx],
            statut: 'Identique',
            confiance: 1.0,
            groupe_conflit_id: gid,
            cible_numero: cible,
            justification: justif,
            resultat_ia: {
              id: out[m.idx].id || out[m.idx].uid,
              statut: 'Identique',
              confiance: 1.0,
              niveau_confiance: 1.0,
              cible,
              cible_numero: cible,
              id_discussion_cible: cible,
              groupe_conflit_id: gid,
              justification: justif,
              analyse_intention: justif,
              analyse_politique: 'Regroupement mécanique par empreinte textuelle.',
              alerte_couleur: 'bleu',
              groupe: { type: 'identiques', groupe_id: gid },
            },
          }
        }
      }
    }

    const remaining = items.filter((it) => !handledIdx.has(it.idx))
    if (remaining.length >= 2) {
      const pivotNum = String(remaining[0].a.numero || remaining[0].a.id || '')
      const gid = `dc_${artSlug}_p_${pivotNum}`
      for (const m of remaining) {
        nbDc++
        const num = String(m.a.numero || m.a.id || '')
        const cible = num === pivotNum ? String(remaining[1].a.numero || remaining[1].a.id || '') : pivotNum
        const justif = `Discussion commune sur ${art} avec l'amendement n° ${cible}.`
        out[m.idx] = {
          ...out[m.idx],
          statut: 'Discussion commune',
          confiance: 0.95,
          groupe_conflit_id: gid,
          cible_numero: cible,
          justification: justif,
          resultat_ia: {
            id: out[m.idx].id || out[m.idx].uid,
            statut: 'Discussion commune',
            confiance: 0.95,
            niveau_confiance: 0.95,
            cible,
            cible_numero: cible,
            id_discussion_cible: cible,
            groupe_conflit_id: gid,
            justification: justif,
            analyse_intention: justif,
            analyse_politique: 'Mise en discussion commune déterministe.',
            alerte_couleur: 'orange',
            groupe: { type: 'discussion_commune', groupe_id: gid },
          },
        }
      }
    } else if (remaining.length === 1) {
      const m = remaining[0]
      nbIsoles++
      const justif = 'Amendement isolé sans collision directe sur cette division.'
      out[m.idx] = {
        ...out[m.idx],
        statut: 'Isolé',
        confiance: 1.0,
        groupe_conflit_id: null,
        cible_numero: null,
        justification: justif,
        resultat_ia: {
          id: out[m.idx].id || out[m.idx].uid,
          statut: 'Isolé',
          confiance: 1.0,
          niveau_confiance: 1.0,
          cible: null,
          cible_numero: null,
          id_discussion_cible: null,
          groupe_conflit_id: null,
          justification: justif,
          analyse_intention: justif,
          analyse_politique: 'Examen autonome.',
          alerte_couleur: 'gris',
          groupe: null,
        },
      }
    }
  }

  Object.defineProperty(out, '_meta', {
    value: {
      duree_ms: Math.max(1, Date.now() - startMs),
      statistiques: {
        identiques: nbIdentiques,
        discussions_communes: nbDc,
        isoles: nbIsoles,
      },
    },
    enumerable: false,
    configurable: true,
  })
  return out
}

/**
 * Exécute le moteur déterministe légistique Python (`POST /api/v2/classer-regles`)
 * en un seul appel ultra-rapide (< 200 ms pour 341 amendements), sans solliciter de LLM.
 * Fusionne `statut`, `groupe_conflit_id`, `cible_numero`, `justification` et `resultat_ia`
 * dans l'état local des amendements.
 */
export async function classifyMechanically(amendements, options = {}) {
  const { signal } = options
  if (!Array.isArray(amendements) || amendements.length === 0) {
    return []
  }

  let data
  try {
    const resMec = await fetch(`${API_BASE_URL}/api/v2/classer-regles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
      signal,
      body: JSON.stringify({ amendements }),
    })

    if (!resMec.ok) {
      const errorText = await resMec.text().catch(() => 'Erreur inconnue')
      throw new ClassifyError(`Moteur Déterministe : ${errorText}`, resMec.status)
    }

    data = await resMec.json()
  } catch (err) {
    if (err?.name === 'AbortError' || err?.name === 'ClassifyError') {
      throw err
    }
    // Repli local déterministe si le backend Python est hors-ligne
    return classifyMechanicallyLocalFallback(amendements)
  }

  const serverList = Array.isArray(data) ? data : (data?.amendements || [])
  const byKey = new Map()
  serverList.forEach((srv) => {
    const kId = srv.id || srv.uid
    const kNum = srv.numero != null ? String(srv.numero) : null
    if (kId) byKey.set(String(kId), srv)
    if (kNum && !byKey.has(`num:${kNum}`)) byKey.set(`num:${kNum}`, srv)
  })

  const merged = amendements.map((orig, idx) => {
    const kId = orig.id || orig.uid
    const kNum = orig.numero != null ? String(orig.numero) : null
    const srv =
      (kId && byKey.get(String(kId))) ||
      (kNum && byKey.get(`num:${kNum}`)) ||
      serverList[idx]

    if (!srv) return orig

    return {
      ...orig,
      ...srv,
      id: orig.id || srv.id || orig.uid || srv.uid,
      uid: orig.uid || srv.uid || orig.id || srv.id,
      article: orig.article || srv.article,
      auteurs: orig.auteurs || srv.auteurs,
      groupe_politique: orig.groupe_politique || srv.groupe_politique,
      commission: orig.commission || srv.commission,
      commission_libelle: orig.commission_libelle || srv.commission_libelle,
      commission_mots_cles: orig.commission_mots_cles || srv.commission_mots_cles,
      commission_hors_champ: orig.commission_hors_champ ?? srv.commission_hors_champ,
      point_impact: orig.point_impact || srv.point_impact,
      statut: srv.statut,
      confiance: srv.confiance ?? 1.0,
      groupe_conflit_id: srv.groupe_conflit_id ?? null,
      cible_numero: srv.cible_numero ?? null,
      justification: srv.justification || srv.resultat_ia?.justification || '',
      resultat_ia: srv.resultat_ia || {
        id: orig.id || srv.id,
        statut: srv.statut,
        confiance: srv.confiance ?? 1.0,
        niveau_confiance: srv.confiance ?? 1.0,
        cible: srv.cible_numero ?? null,
        cible_numero: srv.cible_numero ?? null,
        id_discussion_cible: srv.cible_numero ?? null,
        groupe_conflit_id: srv.groupe_conflit_id ?? null,
        justification: srv.justification || '',
        analyse_intention: srv.justification || '',
        groupe: srv.groupe_conflit_id
          ? {
              type: srv.statut === 'Identique' ? 'identiques' : 'discussion_commune',
              groupe_id: srv.groupe_conflit_id,
            }
          : null,
      },
    }
  })

  if (data && typeof data === 'object' && !Array.isArray(data)) {
    Object.defineProperty(merged, '_meta', {
      value: {
        duree_ms: data.duree_ms,
        statistiques: data.statistiques,
        total: data.total,
      },
      enumerable: false,
      configurable: true,
    })
  }

  return merged
}

export const classifyMechanicalOnly = classifyMechanically

/**
 * Fusionne la synthèse rédigée par l'IA dans un amendement déjà qualifié par le moteur déterministe
 * SANS JAMAIS altérer `statut`, `groupe_conflit_id`, `cible_numero` ni `resultat_ia.groupe`.
 */
export function mergeAiExplanationIntoAmendment(amendement, aiResponse) {
  const aiBlock = aiResponse?.resultat_ia || aiResponse || {}
  const preservedStatut = amendement.resultat_ia?.statut || amendement.statut || aiBlock.statut || 'Discussion commune'
  const preservedGroupId =
    amendement.groupe_conflit_id ??
    amendement.resultat_ia?.groupe_conflit_id ??
    amendement.resultat_ia?.groupe?.groupe_id ??
    null
  const preservedCible =
    amendement.cible_numero ??
    amendement.resultat_ia?.cible_numero ??
    amendement.resultat_ia?.id_discussion_cible ??
    null
  const preservedGroupeObj =
    amendement.resultat_ia?.groupe ||
    (preservedGroupId
      ? {
          type: preservedStatut === 'Identique' ? 'identiques' : 'discussion_commune',
          groupe_id: preservedGroupId,
        }
      : null)

  const newJustification =
    aiBlock.justification ||
    aiBlock.analyse_intention ||
    aiBlock.analyse_politique ||
    amendement.justification ||
    amendement.resultat_ia?.justification ||
    ''
  const newIntention = aiBlock.analyse_intention || newJustification
  const newPolitique = aiBlock.analyse_politique || amendement.resultat_ia?.analyse_politique || ''

  const updatedResultatIa = {
    ...amendement.resultat_ia,
    id: amendement.id || amendement.uid,
    statut: preservedStatut,
    groupe_conflit_id: preservedGroupId,
    cible: preservedCible,
    cible_numero: preservedCible,
    id_discussion_cible: preservedCible,
    groupe: preservedGroupeObj,
    justification: newJustification,
    analyse_intention: newIntention,
    analyse_politique: newPolitique,
    explication_ia: true,
  }

  return {
    ...amendement,
    statut: preservedStatut,
    groupe_conflit_id: preservedGroupId,
    cible_numero: preservedCible,
    justification: newJustification,
    resultat_ia: updatedResultatIa,
  }
}

/**
 * Analyse sémantique unitaire ciblée par l'IA d'un amendement spécifique (ex: "🔍 Pourquoi ce conflit ? (IA)").
 * Cible uniquement l'amendement et ses concurrents sur le même article / cluster,
 * et retourne l'objet `resultat_ia` enrichi tout en préservant le statut et le groupe déterministes.
 */
export async function analyzeSingleAmendment(targetUid, amendements, aiSettings = {}, options = {}) {
  const { signal } = options

  let settings = { ...aiSettings }
  if (!settings.apiKey) {
    try {
      const decrypted = await getDecryptedSettings()
      if (decrypted) {
        settings = { ...decrypted, ...settings, apiKey: settings.apiKey || decrypted.apiKey || '' }
      }
    } catch {
      // ignore
    }
  }

  const targetAm = amendements.find((a) => a.id === targetUid || a.uid === targetUid)
  const targetArt = targetAm?.article_vise || targetAm?.article
  const targetCluster = targetAm?.groupe_conflit_id || targetAm?.resultat_ia?.groupe?.groupe_id

  // Restreindre le contexte aux concurrents directs du même cluster ou du même article
  const clusterSubset = targetAm
    ? amendements.filter((a) => {
        if (a.id === targetUid || a.uid === targetUid) return true
        const aCluster = a.groupe_conflit_id || a.resultat_ia?.groupe?.groupe_id
        if (targetCluster && aCluster && targetCluster === aCluster) return true
        const aArt = a.article_vise || a.article
        return Boolean(targetArt && aArt && String(targetArt).trim() === String(aArt).trim())
      })
    : amendements

  const llmConf = reglagesLLM(settings)
  const isLocal = llmConf.provider === 'local' || llmConf.provider === 'lmstudio'

  const payload = {
    amendements: clusterSubset,
    target_uid: targetUid,
    ...llmConf,
    temperature: 0.1,
    max_tokens: isLocal ? 250 : 350,
    ...(isLocal ? { stop: LOCAL_STOP_SEQUENCES } : {}),
  }

  const response = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    signal,
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => 'Erreur unitaire')
    throw new ClassifyError(`Analyse unitaire IA : ${errorText}`, response.status)
  }

  const rawJson = await response.json()
  if (targetAm && (targetAm.statut || targetAm.resultat_ia?.statut)) {
    return mergeAiExplanationIntoAmendment(targetAm, rawJson).resultat_ia
  }
  return rawJson?.resultat_ia || rawJson
}

/**
 * Enrichit par l'IA UNIQUEMENT les amendements déjà qualifiés en "Discussion commune"
 * (bouton « 🤖 Expliquer les conflits par IA »).
 * Ne recalcule PAS les statuts et ne modifie aucun groupe légistique (`groupe_conflit_id`, `cible_numero`).
 */
export async function explainConflictsWithAI(amendements, options = {}) {
  const {
    aiSettings = {},
    signal,
    onProgress = () => {},
    onMechanical = () => {},
    throttleDelayMs = 1200,
    retryDelayMs = 6000,
  } = options

  let workingList = Array.isArray(amendements) ? [...amendements] : []
  if (workingList.length === 0) return []

  // Si le classement mécanique n'a pas encore été lancé, l'exécuter d'abord en ~100 ms
  const hasAnyStatus = workingList.some((a) => Boolean(a.statut || a.resultat_ia?.statut))
  if (!hasAnyStatus) {
    workingList = await classifyMechanically(workingList, { signal })
    onMechanical(workingList)
  }

  const conflictsToExplain = workingList.filter(
    (a) => (a.resultat_ia?.statut || a.statut) === 'Discussion commune'
  )

  const totalConflicts = conflictsToExplain.length
  onProgress(null, 0, totalConflicts, [...workingList])

  if (totalConflicts === 0) {
    return workingList
  }

  let settings = { ...aiSettings }
  if (!settings.apiKey) {
    try {
      const decrypted = await getDecryptedSettings()
      if (decrypted) {
        settings = { ...decrypted, ...settings, apiKey: settings.apiKey || decrypted.apiKey || '' }
      }
    } catch {
      // ignore
    }
  }

  const llmConf = reglagesLLM(settings)
  const isLocal = llmConf.provider === 'local' || llmConf.provider === 'lmstudio'
  const effectiveThrottleMs = isLocal ? 0 : throttleDelayMs
  const unitTimeoutMs = isLocal ? 10000 : 45000

  let completedCount = 0

  for (let i = 0; i < conflictsToExplain.length; i++) {
    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }

    if (!isLocal && effectiveThrottleMs > 0 && i > 0) {
      await new Promise((resolve) => setTimeout(resolve, effectiveThrottleMs))
    }

    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }

    const amd = conflictsToExplain[i]
    const targetUid = amd.id || amd.uid
    const targetArt = amd.article_vise || amd.article
    const targetCluster = amd.groupe_conflit_id || amd.resultat_ia?.groupe?.groupe_id

    const clusterSubset = workingList.filter((a) => {
      if ((a.id || a.uid) === targetUid) return true
      const aCluster = a.groupe_conflit_id || a.resultat_ia?.groupe?.groupe_id
      if (targetCluster && aCluster && targetCluster === aCluster) return true
      const aArt = a.article_vise || a.article
      return Boolean(targetArt && aArt && String(targetArt).trim() === String(aArt).trim())
    })

    const singlePayload = {
      amendements: clusterSubset,
      target_uid: targetUid,
      ...llmConf,
      temperature: 0.1,
      max_tokens: isLocal ? 250 : 350,
      ...(isLocal ? { stop: LOCAL_STOP_SEQUENCES } : {}),
    }

    const unitController = new AbortController()
    let isUnitTimeout = false
    const timeoutId = setTimeout(() => {
      isUnitTimeout = true
      unitController.abort()
    }, unitTimeoutMs)

    const onGlobalAbort = () => unitController.abort()
    if (signal) {
      signal.addEventListener('abort', onGlobalAbort, { once: true })
    }

    try {
      let resSingle = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        signal: unitController.signal,
        body: JSON.stringify(singlePayload),
      })

      if (!isLocal && resSingle.status === 429) {
        await new Promise((resolve) => setTimeout(resolve, retryDelayMs))
        if (signal?.aborted) {
          throw new DOMException('Aborted', 'AbortError')
        }
        resSingle = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
          signal: unitController.signal,
          body: JSON.stringify(singlePayload),
        })
      }

      if (!resSingle.ok) {
        const errText = await resSingle.text().catch(() => 'Erreur API unitaire')
        if (resSingle.status === 401 || resSingle.status === 503) {
          let detail = errText
          try {
            detail = JSON.parse(errText).detail || errText
          } catch {
            // garde errText
          }
          throw new ClassifyError(
            `${detail}. Ouvrez ⚙️ Réglages IA → 🔑 Clé API pour saisir votre clé Groq valide (gsk_...), ou mettez à jour GROQ_API_KEY dans Vercel puis redéployez.`,
            resSingle.status
          )
        }
        completedCount++
        onProgress(amd.resultat_ia, completedCount, totalConflicts, [...workingList])
        continue
      }

      const res = await resSingle.json()
      const idxInGlobal = workingList.findIndex((r) => (r.id || r.uid) === targetUid)
      if (idxInGlobal !== -1) {
        workingList[idxInGlobal] = mergeAiExplanationIntoAmendment(workingList[idxInGlobal], res)
      }
      completedCount++
      onProgress(
        workingList[idxInGlobal]?.resultat_ia || res.resultat_ia,
        completedCount,
        totalConflicts,
        [...workingList]
      )
    } catch (err) {
      if (signal?.aborted) {
        throw new DOMException('Aborted', 'AbortError')
      }
      if (err.name === 'ClassifyError') throw err
      if (isUnitTimeout) {
        console.warn(`[Bourbon.ia] Coupe-circuit explication IA (${unitTimeoutMs / 1000}s) sur ${targetUid}`)
      }
      completedCount++
      onProgress(amd.resultat_ia, completedCount, totalConflicts, [...workingList])
    } finally {
      clearTimeout(timeoutId)
      if (signal) {
        signal.removeEventListener('abort', onGlobalAbort)
      }
    }
  }

  return workingList
}

/**
 * Pipeline V2 — Orchestrateur frontend pour le backend FastAPI V2
 * (Tri déterministe → Cache SQLite → LLM Sémantique → Data Mapper)
 *
 * Retourne directement les amendements enrichis + classés, prêts pour React.
 */
export async function classifyAmendmentsV2(amendements, options = {}) {
  const {
    aiSettings = {},
    signal,
    onProgress = () => {},
    onMechanical = () => {},
    throttleDelayMs = 1200,
    retryDelayMs = 6000,
  } = options

  let settings = { ...aiSettings }
  if (!settings.apiKey) {
    try {
      const decrypted = await getDecryptedSettings()
      if (decrypted) {
        settings = { ...decrypted, ...settings, apiKey: settings.apiKey || decrypted.apiKey || '' }
      }
    } catch {
      // ignore
    }
  }

  console.log("[Bourbon.ia] Transmission clé IA :", settings?.apiKey ? "Clé personnalisée injectée" : "Clé serveur par défaut")

  const llmConf = reglagesLLM(settings)
  const isLocal = llmConf.provider === 'local' || llmConf.provider === 'lmstudio'

  const payload = {
    amendements,
    ...llmConf,
    temperature: 0.1,
    max_tokens: isLocal ? 250 : 350,
    ...(isLocal ? { stop: LOCAL_STOP_SEQUENCES } : {}),
  }

  // 1. Tri mécanique immédiat (sans LLM)
  const resMec = await fetch(`${API_BASE_URL}/api/v2/mecanique`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    signal,
    body: JSON.stringify(payload),
  })

  if (!resMec.ok) {
    const errorText = await resMec.text().catch(() => 'Erreur inconnue')
    throw new ClassifyError(`Pipeline V2 Mécanique : ${errorText}`, resMec.status)
  }

  const mecaniques = await resMec.json()
  // Met à jour l'UI instantanément avec le tri mécanique
  onMechanical(mecaniques)

  // 2. Traitement LLM (Frontend Orchestrator)
  // Les amendements marqués _skipLLM (identiques ou isolés mécaniquement) ne sollicitent pas le LLM
  const aTraiter = mecaniques.filter(a => a.statut_mecanique === 'NOUVEAU' && !a._skipLLM && !a.skip_llm)
  const nb_classes = mecaniques.length - aTraiter.length

  // Appel immédiat pour que le compteur s'incrémente des triés mécaniques
  onProgress(null, nb_classes, mecaniques.length, [])

  const resultatsGlobaux = [...mecaniques]
  const total = mecaniques.length

  // Cadence séquentielle stricte (1 seul slot actif) :
  // - Mode local : 1 worker séquentiel strict pour allouer 100 % de la mémoire unifiée et du GPU Metal (M1 Pro)
  //   avec zéro sleep artificiel (0 ms) pour une cadence maximale continue sans à-coups.
  // - Mode Groq / distant : cadence protectrice 1 200 ms et 1 worker séquentiel (anti-429).
  const CONCURRENCY = 1
  const effectiveThrottleMs = isLocal ? 0 : throttleDelayMs
  const unitTimeoutMs = isLocal ? 10000 : 45000

  let completedCount = 0
  let nextQueueIndex = 0

  async function worker() {
    while (nextQueueIndex < aTraiter.length) {
      if (signal?.aborted) {
        throw new DOMException('Aborted', 'AbortError')
      }
      const itemIdx = nextQueueIndex++
      const amd = aTraiter[itemIdx]

      // Cooldown protecteur : actif uniquement en mode distant (Groq) entre requêtes successives
      if (!isLocal && effectiveThrottleMs > 0 && itemIdx > 0) {
        await new Promise((resolve) => setTimeout(resolve, effectiveThrottleMs))
      }

      if (signal?.aborted) {
        throw new DOMException('Aborted', 'AbortError')
      }

      const singlePayload = {
        ...payload,
        target_uid: amd.id,
      }

      // Coupe-circuit unitaire (timeout strict de 10s en local pour éviter tout gel de file)
      const unitController = new AbortController()
      let isUnitTimeout = false
      const timeoutId = setTimeout(() => {
        isUnitTimeout = true
        unitController.abort()
      }, unitTimeoutMs)

      const onGlobalAbort = () => unitController.abort()
      if (signal) {
        signal.addEventListener('abort', onGlobalAbort, { once: true })
      }

      try {
        let resSingle = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
          signal: unitController.signal,
          body: JSON.stringify(singlePayload),
        })

        // Gestion Anti-429 & Backoff (1 tentative de retry après 6 secondes pour reconstituer la fenêtre de tokens Groq)
        if (!isLocal && resSingle.status === 429) {
          await new Promise((resolve) => setTimeout(resolve, retryDelayMs))
          if (signal?.aborted) {
            throw new DOMException('Aborted', 'AbortError')
          }
          resSingle = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
            signal: unitController.signal,
            body: JSON.stringify(singlePayload),
          })
        }

        if (!resSingle.ok) {
          const errText = await resSingle.text().catch(() => 'Erreur API unitaire')
          if (resSingle.status === 401 || resSingle.status === 503) {
            let detail = errText
            try {
              detail = JSON.parse(errText).detail || errText
            } catch {
              // garde errText
            }
            throw new ClassifyError(
              `${detail}. Ouvrez ⚙️ Réglages IA → 🔑 Clé API pour saisir votre clé Groq valide (gsk_...), ou mettez à jour GROQ_API_KEY dans Vercel puis redéployez.`,
              resSingle.status
            )
          }
          if (resSingle.status === 429) {
            // Second échec 429 consécutif : marquer en attente sans bloquer le reste de l'ordonnancement
            completedCount++
            const indexObj = resultatsGlobaux.findIndex(r => r.id === amd.id)
            if (indexObj !== -1) {
              const waitingRes = {
                id: amd.id,
                statut: 'Isolé',
                analyse_intention: '⏳ En attente (Quota IA temporairement atteint — HTTP 429).',
                analyse_politique: 'Mise en attente automatique suite au plafond de requêtes par minute.',
                justification: 'Quota de tokens par minute atteint (HTTP 429).',
                alerte_couleur: 'orange',
                niveau_confiance: 0.0,
              }
              resultatsGlobaux[indexObj] = {
                ...resultatsGlobaux[indexObj],
                resultat_ia: waitingRes,
              }
              onProgress(waitingRes, nb_classes + completedCount, total, [...resultatsGlobaux])
            }
            continue
          }
          throw new Error(errText)
        }

        const res = await resSingle.json()

        // Mettre à jour le tableau global
        const indexObj = resultatsGlobaux.findIndex(r => r.id === amd.id)
        if (indexObj !== -1) {
          resultatsGlobaux[indexObj] = res
        }

        completedCount++

        // Remonter la progression au composant React au fil de l'eau
        if (res.resultat_ia) {
          onProgress(res.resultat_ia, nb_classes + completedCount, total, [...resultatsGlobaux])
        }

      } catch (err) {
        if (signal?.aborted) {
          throw new DOMException('Aborted', 'AbortError')
        }
        if (err.name === 'ClassifyError') throw err

        // Coupe-circuit unitaire activé (timeout local ou réseau)
        if (isUnitTimeout || (err.name === 'AbortError' && isUnitTimeout)) {
          console.warn(`[Bourbon.ia] Coupe-circuit activé : timeout ${unitTimeoutMs / 1000}s dépassé pour ${amd.id}`)
          completedCount++
          const indexObj = resultatsGlobaux.findIndex(r => r.id === amd.id)
          if (indexObj !== -1) {
            const timeoutRes = {
              id: amd.id,
              statut: 'Isolé',
              analyse_intention: 'Délai de réponse dépassé en local (timeout 10s).',
              analyse_politique: 'Traitement interrompu après expiration du délai d\'attente de 10s.',
              justification: 'Délai de réponse dépassé en local (timeout 10s).',
              alerte_couleur: 'gris',
              niveau_confiance: 0.5,
            }
            resultatsGlobaux[indexObj] = {
              ...resultatsGlobaux[indexObj],
              resultat_ia: timeoutRes,
            }
            onProgress(timeoutRes, nb_classes + completedCount, total, [...resultatsGlobaux])
          }
          continue
        }

        console.error(`Erreur LLM sur ${amd.id}:`, err)

        completedCount++
        const indexObj = resultatsGlobaux.findIndex(r => r.id === amd.id)
        if (indexObj !== -1) {
          const errorRes = {
            id: amd.id,
            statut: 'Erreur IA',
            analyse_intention: '⚠️ Impossible de joindre l\'IA ou erreur lors de l\'analyse.',
            analyse_politique: 'Analyse sémantique indisponible.',
            justification: err.message || 'Échec de traitement.',
            alerte_couleur: 'rouge',
            niveau_confiance: 0.0,
          }
          resultatsGlobaux[indexObj] = {
            ...resultatsGlobaux[indexObj],
            resultat_ia: errorRes,
          }
          onProgress(errorRes, nb_classes + completedCount, total, [...resultatsGlobaux])
        }
      } finally {
        clearTimeout(timeoutId)
        if (signal) {
          signal.removeEventListener('abort', onGlobalAbort)
        }
      }
    }
  }

  const workerCount = Math.min(CONCURRENCY, aTraiter.length)
  if (workerCount > 0) {
    const workers = Array.from({ length: workerCount }, () => worker())
    await Promise.all(workers)
  }

  return resultatsGlobaux
}
