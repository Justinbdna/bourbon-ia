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

  const provider = aiSettings.provider || 'local'
  const localUrl = (aiSettings.localUrl || 'http://localhost:1234/v1').trim().replace(/\/+$/, '')

  const payload = {
    amendements,
    model: provider === 'local' ? (aiSettings.localModel || 'local-model') : (aiSettings.groqModel || 'llama-3.3-70b-versatile'),
    provider,
    llm_endpoint: provider === 'local' ? localUrl : 'https://api.groq.com/openai/v1',
    api_key: aiSettings.apiKey || 'local-key',
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
  const aTraiter = mecaniques.filter(a => a.statut_mecanique === 'NOUVEAU')
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
