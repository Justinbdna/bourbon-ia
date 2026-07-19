import { preSortAmendements } from '../utils/sortingEngine'

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

/**
 * Erreur typée pour distinguer les cas d'usage côté UI
 * (hors-sujet / erreur Mistral / erreur réseau).
 */
export class ClassifyError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ClassifyError'
    this.status = status
  }
}

/**
 * Normalise les JSON bruts de l'Assemblée nationale en objets plats pour le Front.
 */
export async function normalizeAmendments(amendements) {
  const response = await fetch(`${API_BASE_URL}/api/normalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amendements, model: 'llama3-8b-8192' }),
  })
  
  if (!response.ok) {
    throw new ClassifyError(`Erreur de normalisation: ${await response.text()}`, response.status)
  }
  
  return await response.json()
}

/**
 * Envoie les amendements au backend FastAPI pour classement par l'IA.
 * Renvoie { classement, avertissements, modele_utilise }.
 */
export async function classifyAmendments(amendements, aiSettings = {}) {
  const provider = aiSettings.provider || 'groq'
  
  if (provider === 'local') {
    return await classifyWithLocalAI(amendements, aiSettings)
  }

  // --- PRÉ-TRI MÉCANIQUE (Portage du moteur de Yassine) ---
  const preSorted = preSortAmendements(amendements)
  const toSendToLLM = preSorted.filter(am => !am._skipLLM)
  const preClassified = preSorted.filter(am => am._skipLLM).map(am => ({
    id: am.id,
    statut: 'Identique',
    justification: 'Détecté mécaniquement : même article et même dispositif.',
    alerte_couleur: 'orange',
    rang: am._rang,
    groupe: am._groupe
  }))

  const allWarnings = []
  if (preClassified.length > 0) {
    allWarnings.push(`✅ ${preClassified.length} amendement(s) classé(s) mécaniquement (Identiques).`)
  }

  if (toSendToLLM.length === 0) {
    return { classement: preClassified, avertissements: allWarnings, modele_utilise: 'Moteur déterministe (sans IA)' }
  }

  // --- MODE CLOUD (Groq via Vercel) avec CHUNKING ---
  // Vercel coupe au bout de 10s. On découpe en lots de 5 amendements max.
  const CHUNK_SIZE = 5
  const llmResults = []

  // On nettoie les champs internes avant d'envoyer au backend
  const cleanForBackend = toSendToLLM.map(({ _rang, _groupe, _skipLLM, ...rest }) => rest)

  for (let start = 0; start < cleanForBackend.length; start += CHUNK_SIZE) {
    const chunk = cleanForBackend.slice(start, start + CHUNK_SIZE)
    
    const payload = {
      amendements: chunk,
      provider: 'groq',
      api_key: aiSettings.apiKey || null
    }

    let response;
    try {
      response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } catch (err) {
      throw new ClassifyError(
        `Impossible de joindre le serveur Vercel. (${err.message})`,
        0
      )
    }

    if (!response.ok) {
      const errorText = await response.text()
      const status = response.status
      
      // Message explicite pour les erreurs de quota (429)
      if (status === 429 || status === 500 && errorText.toLowerCase().includes('rate limit')) {
        throw new ClassifyError(
          `⚠️ Quota de tokens dépassé (Erreur ${status}). Ouvrez les ⚙️ Réglages IA pour : saisir votre propre clé API Groq (gratuite), ou basculer sur une IA Locale (LM Studio/Ollama) gratuite et illimitée.`,
          status
        )
      }
      throw new ClassifyError(`Erreur API Vercel ${status}: ${errorText}`, status)
    }

    const data = await response.json()
    if (Array.isArray(data)) {
      llmResults.push(...data)
    } else if (data.classement) {
      llmResults.push(...data.classement)
      if (data.avertissements) allWarnings.push(...data.avertissements)
    }
  }

  // Fusion : pré-classés + résultats LLM, puis re-ranking global
  const allResults = [...preClassified, ...llmResults]
  allResults.forEach((r, i) => { r.rang = i + 1 })

  return { classement: allResults, avertissements: allWarnings, modele_utilise: 'Groq (Cloud)' }
}

// Fonction dédiée pour appeler LM Studio DIRECTEMENT depuis le navigateur
async function classifyWithLocalAI(amendements, aiSettings) {
  if (amendements.length === 0) return { classement: [], avertissements: [], modele_utilise: 'Local' }

  // --- NETTOYAGE URL ---
  let localUrl = (aiSettings.localUrl || 'http://localhost:1234/v1').trim()
  localUrl = localUrl.replace(/\/+$/, '')
  localUrl = localUrl.replace(/\/[vV]1$/, '')
  const baseUrl = `${localUrl}/v1`
  const endpoint = `${baseUrl}/chat/completions`

  // --- PREFLIGHT : Test de connectivité AVANT la boucle ---
  try {
    const preflight = await fetch(`${baseUrl}/models`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000) // Timeout 5s max
    })
    if (!preflight.ok) {
      throw new Error(`LM Studio a répondu ${preflight.status}`)
    }
  } catch (preflightErr) {
    console.error('Preflight LM Studio échoué:', preflightErr)

    // Diagnostic précis de l'erreur
    let diagnostic = ''
    const msg = preflightErr.message || ''
    if (msg.includes('Failed to fetch') || msg.includes('Load failed') || msg.includes('NetworkError')) {
      diagnostic = 'Connexion impossible vers LM Studio. Causes possibles :\n'
        + '• Le serveur LM Studio n\'est pas démarré\n'
        + '• Aucun modèle n\'est chargé dans LM Studio\n'
        + '• Blocage CORS (site HTTPS → localhost HTTP)\n'
        + '→ Solution : Activez le CORS dans LM Studio (Server Settings), ou lancez le site en local (npm run dev).'
    } else if (msg.includes('TimeoutError') || msg.includes('timed out')) {
      diagnostic = 'LM Studio ne répond pas (timeout 5s). Vérifiez qu\'un modèle est bien chargé.'
    } else {
      diagnostic = `Erreur de connexion LM Studio : ${msg}`
    }

    // Court-circuit : marquer TOUS les amendements en Erreur immédiatement
    const fallback = amendements.map((am, i) => ({
      id: am.id || am.numero,
      statut: 'Erreur',
      justification: diagnostic,
      alerte_couleur: 'rouge',
      rang: i + 1
    }))
    return {
      classement: fallback,
      avertissements: [`⚠️ Serveur local injoignable. Aucun amendement n'a pu être classé. ${diagnostic.split('\n')[0]}`],
      modele_utilise: 'LM Studio (Local) — Hors ligne'
    }
  }

  // --- PRÉ-TRI MÉCANIQUE (Portage du moteur de Yassine) ---
  const preSorted = preSortAmendements(amendements)
  const toClassifyByLLM = preSorted.filter(am => !am._skipLLM)
  const preClassified = preSorted.filter(am => am._skipLLM).map(am => ({
    id: am.id,
    statut: 'Identique',
    justification: 'Détecté mécaniquement : même article et même dispositif.',
    alerte_couleur: 'orange',
    rang: am._rang,
    groupe: am._groupe
  }))

  const avertissements = []
  if (preClassified.length > 0) {
    avertissements.push(`✅ ${preClassified.length} amendement(s) classé(s) mécaniquement (Identiques). Tokens économisés.`)
  }

  if (toClassifyByLLM.length === 0) {
    return { classement: preClassified, avertissements, modele_utilise: 'Moteur déterministe (sans IA)' }
  }

  // --- CLASSEMENT LLM pour les amendements non déterminés ---
  const systemPrompt = `TU ES UN AUTOMATE DE CLASSEMENT. RÉPONSE UNIQUE JSON SANS COMMENTAIRE : {"statut": "Identique" | "Discussion commune" | "Isolé", "justification": "...", "alerte_couleur": "orange" | "vert" | "gris"}. NE LISTE JAMAIS LES AUTEURS. SI PLUSIEURS OBJETS, GARDE UNIQUEMENT LE PREMIER.`

  const reference_brut = toClassifyByLLM[0]
  const resultats = [{
    id: reference_brut.id || reference_brut.numero,
    statut: 'Isolé',
    justification: 'Premier du lot (Référence).',
    alerte_couleur: 'vert',
    rang: 1
  }]

  let consecutiveFailures = 0

  for (let i = 1; i < toClassifyByLLM.length; i++) {
    // Fail-fast : si 2 requêtes consécutives échouent, on arrête tout
    if (consecutiveFailures >= 2) {
      resultats.push({
        id: toClassifyByLLM[i].id || toClassifyByLLM[i].numero,
        statut: 'Erreur',
        justification: 'Classement interrompu : trop d\'échecs consécutifs.',
        alerte_couleur: 'rouge',
        rang: i + 1
      })
      continue
    }

    const am = toClassifyByLLM[i]
    const userPrompt = `REF: ${reference_brut.dispositif}\nTEST: ${am.dispositif}`

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'local-model',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt }
          ],
          temperature: 0.1,
          max_tokens: 8192
        })
      })

      if (!res.ok) throw new Error(`LM Studio a répondu ${res.status}`)

      const jsonRes = await res.json()

      // Vérifier si le modèle a été coupé par la limite de tokens
      const finishReason = jsonRes.choices[0].finish_reason
      if (finishReason === 'length') {
        console.warn(`Amendement ${am.numero} : réponse tronquée (finish_reason=length)`)
      }

      let contenu = jsonRes.choices[0].message.content.trim()

      // --- PARSEUR JSON ANTI-HALLUCINATION ---
      let parsed;
      try {
        let cleanContent = contenu.replace(/^```(?:json)?\s*/m, '').replace(/\s*```$/m, '').trim();
        const jsonMatch = cleanContent.match(/\[[\s\S]*\]|\{[\s\S]*\}/);
        if (jsonMatch) cleanContent = jsonMatch[0];
        cleanContent = cleanContent.replace(/,\s*([\]}])/g, '$1');
        parsed = JSON.parse(cleanContent);
        if (Array.isArray(parsed)) {
          if (parsed.length > 0) {
            parsed = parsed[0]; // Correction hallucination multi-auteurs
          } else {
            throw new Error('Tableau JSON vide retourné');
          }
        }
      } catch (parseError) {
        console.error('Erreur de parsing JSON brut:', contenu);
        throw new Error('Format JSON invalide renvoyé par l\'IA Locale');
      }

      const statut = parsed.statut || 'Isolé'
      const alerte_couleur = parsed.alerte_couleur || (statut === 'Identique' ? 'orange' : 'vert')

      resultats.push({
        id: am.id || am.numero,
        statut,
        justification: parsed.justification || '',
        alerte_couleur,
        rang: i + 1
      })
      consecutiveFailures = 0
    } catch (err) {
      console.error('Erreur LM Studio:', err)
      consecutiveFailures++
      resultats.push({
        id: am.id || am.numero,
        statut: 'Erreur',
        justification: 'Échec de communication avec LM Studio.',
        alerte_couleur: 'rouge',
        rang: i + 1
      })
      avertissements.push(`L'amendement ${am.numero} a échoué.`)
    }
  }

  // Attribution des groupes pour les résultats LLM
  for (const r of resultats) {
    if (r.statut === 'Identique') {
      r.groupe = { type: 'identiques', groupe_id: 'grp-identiques-llm' }
    } else if (r.statut === 'Discussion commune') {
      r.groupe = { type: 'discussion_commune', groupe_id: 'grp-discussion_commune-1' }
    }
  }

  // Fusion : pré-classés + résultats LLM, puis re-ranking global
  const allResults = [...preClassified, ...resultats]
  allResults.forEach((r, i) => { r.rang = i + 1 })

  return { classement: allResults, avertissements, modele_utilise: 'LM Studio (Local)' }
}
