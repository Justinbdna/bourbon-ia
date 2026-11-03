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
