import { getDecryptedSettings } from '../utils/crypto'

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

export class ClassifyError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ClassifyError'
    this.status = status
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
    throttleDelayMs = 350,
    retryDelayMs = 2500,
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

  const payload = {
    amendements,
    ...reglagesLLM(settings),
    temperature: 0.1,
    max_tokens: 1024,
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

  // 2. Boucle LLM Séquentielle (Frontend Orchestrator)
  // Les amendements marqués _skipLLM (identiques ou isolés mécaniquement) ne sollicitent pas le LLM
  const aTraiter = mecaniques.filter(a => a.statut_mecanique === 'NOUVEAU' && !a._skipLLM && !a.skip_llm)
  const nb_classes = mecaniques.length - aTraiter.length

  // Appel immédiat pour que le compteur s'incrémente des triés mécaniques
  onProgress(null, nb_classes, mecaniques.length, [])

  const resultatsGlobaux = [...mecaniques]

  let currentIdx = 0
  const total = mecaniques.length

  for (let i = 0; i < aTraiter.length; i++) {
    const amd = aTraiter[i]
    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }

    // Délai de lissage incompressible de 350 ms entre deux requêtes vers /api/v2/analyser-llm
    if (i > 0 && throttleDelayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, throttleDelayMs))
    }

    const singlePayload = {
      ...payload,
      target_uid: amd.id
    }

    try {
      let resSingle = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        signal,
        body: JSON.stringify(singlePayload),
      })

      // Gestion Anti-429 & Backoff Exponentiel (1 tentative de retry après 2,5 secondes)
      if (resSingle.status === 429) {
        await new Promise((resolve) => setTimeout(resolve, retryDelayMs))
        if (signal?.aborted) {
          throw new DOMException('Aborted', 'AbortError')
        }
        resSingle = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
          signal,
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
          currentIdx++
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
              resultat_ia: waitingRes
            }
            onProgress(waitingRes, nb_classes + currentIdx, total, resultatsGlobaux)
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

      currentIdx++

      // Remonter la progression au composant React
      if (res.resultat_ia) {
        onProgress(res.resultat_ia, nb_classes + currentIdx, total, resultatsGlobaux)
      }

    } catch (err) {
      if (err.name === 'AbortError' || err.name === 'ClassifyError') throw err
      console.error(`Erreur LLM sur ${amd.id}:`, err)

      currentIdx++
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
          resultat_ia: errorRes
        }
        onProgress(errorRes, nb_classes + currentIdx, total, resultatsGlobaux)
      }
    }
  }

  return resultatsGlobaux
}
