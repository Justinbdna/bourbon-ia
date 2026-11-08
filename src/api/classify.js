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
    body: JSON.stringify({ amendements, model: 'llama3-8b-8192' }),
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
  const provider = aiSettings.provider || 'local'
  const localUrl = (aiSettings.localUrl || 'http://localhost:1234/v1').trim().replace(/\/+$/, '')
  return {
    model: provider === 'local' ? (aiSettings.localModel || 'local-model') : (aiSettings.groqModel || 'openai/gpt-oss-20b'),
    provider,
    llm_endpoint: provider === 'local' ? localUrl : 'https://api.groq.com/openai/v1',
    api_key: aiSettings.apiKey || 'local-key',
  }
}

/**
 * Résumé neutre (1 à 2 phrases) d'un amendement, généré par l'IA à la demande.
 * Lève ClassifyError avec un message lisible en cas d'échec.
 */
export async function resumerAmendement(amendement, aiSettings = {}, options = {}) {
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
      ...reglagesLLM(aiSettings),
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

// ─── Import direct d'un dossier législatif (données ouvertes de l'AN) ───
async function getImportDossier(chemin, params = {}, options = {}) {
  const query = new URLSearchParams(params).toString()
  const response = await fetch(`${API_BASE_URL}${chemin}${query ? `?${query}` : ''}`, {
    headers: { 'ngrok-skip-browser-warning': 'true' },
    signal: options.signal,
  })
  if (!response.ok) {
    let detail = `Erreur ${response.status}`
    try {
      const corps = await response.json()
      detail = corps.error || corps.detail || detail
    } catch {
      // réponse non JSON : on garde le code HTTP
    }
    throw new ClassifyError(detail, response.status)
  }
  return await response.json()
}

/** Dossiers législatifs (XVIIe législature) dont le titre contient `recherche`. */
export async function rechercherDossiers(recherche, options = {}) {
  return (await getImportDossier('/api/v2/dossiers', { recherche }, options)).dossiers
}

/** Étapes de lecture du dossier ayant des amendements à l'Assemblée : [{ etape, libelle, nb }]. */
export async function listerLiasses(dossierUid, options = {}) {
  return (await getImportDossier(`/api/v2/dossiers/${encodeURIComponent(dossierUid)}/liasses`, {}, options)).liasses
}

/** Amendements d'une liasse, au format brut de l'AN : { amendements, total, tronque }. */
export async function chargerLiasse(dossierUid, etape, options = {}) {
  return await getImportDossier(`/api/v2/dossiers/${encodeURIComponent(dossierUid)}/amendements`, { etape }, options)
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
  } = options

  const payload = {
    amendements,
    ...reglagesLLM(aiSettings),
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

  for (const amd of aTraiter) {
    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }

    const singlePayload = {
      ...payload,
      target_uid: amd.id
    }

    try {
      const resSingle = await fetch(`${API_BASE_URL}/api/v2/analyser-llm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        signal,
        body: JSON.stringify(singlePayload),
      })

      if (!resSingle.ok) {
        const errText = await resSingle.text().catch(() => 'Erreur API unitaire')
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
        onProgress(res.resultat_ia, nb_classes + currentIdx, total, [])
      }

    } catch (err) {
      if (err.name === 'AbortError') throw err
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
        onProgress(errorRes, nb_classes + currentIdx, total, [])
      }
    }
  }

  return resultatsGlobaux
}
