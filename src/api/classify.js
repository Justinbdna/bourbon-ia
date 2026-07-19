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

  // --- MODE CLOUD (Groq via Vercel) avec CHUNKING ---
  // Vercel coupe au bout de 10s. On découpe en lots de 5 amendements max.
  const CHUNK_SIZE = 5
  const allResults = []
  const allWarnings = []

  for (let start = 0; start < amendements.length; start += CHUNK_SIZE) {
    const chunk = amendements.slice(start, start + CHUNK_SIZE)
    
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
      allResults.push(...data)
    } else if (data.classement) {
      allResults.push(...data.classement)
      if (data.avertissements) allWarnings.push(...data.avertissements)
    }
  }

  // Recalculer les rangs globaux après fusion des lots
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

  // --- CLASSEMENT : Le serveur répond, on peut travailler ---
  const systemPrompt = `RÈGLE DE CLASSEMENT MVP : Tu es un administrateur de l'Assemblée nationale. Tu dois classer une liste d'amendements.
- Si plusieurs amendements ciblent le même article et ont le même dispositif, classe-les en 'Identique'.
- S'ils diffèrent légèrement, classe-les en 'Discussion commune'.
- Sinon, classe en 'Isolé'.
RÈGLES DE FORMATAGE ABSOLUES :
1. Renvoie un tableau JSON valide.
2. Conserve la valeur exacte de la clé 'id'.
3. 'statut' doit être 'Identique', 'Discussion commune', ou 'Isolé'.
Format attendu: [{"id": "...", "statut": "Isolé", "justification": "...", "alerte_couleur": "gris"}]`

  const reference_brut = amendements[0]
  const resultats = [{
    id: reference_brut.id || reference_brut.numero,
    statut: "Isolé",
    justification: "Premier du lot (Référence).",
    alerte_couleur: "vert",
    rang: 1
  }]

  const avertissements = []
  let consecutiveFailures = 0

  for (let i = 1; i < amendements.length; i++) {
    // Fail-fast : si 2 requêtes consécutives échouent, on arrête tout
    if (consecutiveFailures >= 2) {
      resultats.push({
        id: amendements[i].id || amendements[i].numero,
        statut: 'Erreur',
        justification: 'Classement interrompu : trop d\'échecs consécutifs.',
        alerte_couleur: 'rouge',
        rang: i + 1
      })
      continue
    }

    const am = amendements[i]
    const userPrompt = `REF - Auteur: ${reference_brut.auteurs}\nTexte: ${reference_brut.dispositif}\nTEST - Auteur: ${am.auteurs}\nTexte: ${am.dispositif}`

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
          max_tokens: 1500
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

      // Extraction JSON ultra-robuste (alignée sur le parseur backend)
      let parsed
      try {
        // 1. Retirer les balises Markdown
        contenu = contenu.replace(/^```(?:json)?\s*/m, '').replace(/\s*```$/m, '').trim()
        // 2. Extraire le premier objet ou tableau JSON trouvé
        const jsonMatch = contenu.match(/\[.*\]|\{.*\}/s)
        if (jsonMatch) contenu = jsonMatch[0]
        parsed = JSON.parse(contenu)
      } catch (parseErr) {
        console.error('JSON invalide reçu de LM Studio:', contenu)
        // Tentative de sauvetage : extraire juste le premier objet { ... }
        const objMatch = contenu.match(/\{[^{}]*\}/)
        if (objMatch) {
          try { parsed = JSON.parse(objMatch[0]) } catch { parsed = null }
        }
        if (!parsed) throw new Error('Format JSON invalide renvoyé par l\'IA Locale')
      }
      if (Array.isArray(parsed)) parsed = parsed[0]

      const statut = parsed.statut || "Isolé"
      const alerte_couleur = statut === "Identique" ? "orange" : "vert"

      resultats.push({
        id: am.id || am.numero,
        statut: statut,
        justification: parsed.justification || "",
        alerte_couleur: alerte_couleur,
        rang: i + 1
      })
      consecutiveFailures = 0 // Reset en cas de succès
    } catch (err) {
      console.error("Erreur LM Studio:", err)
      consecutiveFailures++
      resultats.push({
        id: am.id || am.numero,
        statut: "Erreur",
        justification: "Échec de communication avec LM Studio.",
        alerte_couleur: "rouge",
        rang: i + 1
      })
      avertissements.push(`L'amendement ${am.numero} a échoué.`)
    }
  }

  // Attribution des groupes
  for (const r of resultats) {
    if (r.statut === "Identique") {
      r.groupe = { type: "identiques", groupe_id: `grp-identiques-1` }
    } else if (r.statut === "Discussion commune") {
      r.groupe = { type: "discussion_commune", groupe_id: `grp-discussion_commune-1` }
    }
  }

  return { classement: resultats, avertissements, modele_utilise: 'LM Studio (Local)' }
}
