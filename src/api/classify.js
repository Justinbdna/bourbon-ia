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

  // Logique originelle pour le Cloud (Groq) via Vercel
  const payload = {
    amendements,
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
    throw new ClassifyError(`Erreur API Vercel ${response.status}: ${errorText}`, response.status)
  }

  const data = await response.json()
  if (Array.isArray(data)) {
    return { classement: data, avertissements: [], modele_utilise: 'Groq (Cloud)' }
  }
  return data
}

// Fonction dédiée pour appeler LM Studio DIRECTEMENT depuis le navigateur
async function classifyWithLocalAI(amendements, aiSettings) {
  const localUrl = aiSettings.localUrl || 'http://localhost:1234/v1'
  const endpoint = `${localUrl}/chat/completions`
  
  if (amendements.length === 0) return { classement: [], avertissements: [], modele_utilise: 'Local' }

  // 1. Définir le prompt système (identique au backend)
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
    statut: "Isolé", // Force le premier à Isolé ou Nouveau par défaut
    justification: "Premier du lot (Référence).",
    alerte_couleur: "vert",
    rang: 1
  }]

  const avertissements = []
  
  // 2. Traiter les suivants un par un pour ne pas surcharger le modèle local
  for (let i = 1; i < amendements.length; i++) {
    const am = amendements[i]
    const userPrompt = `REF - Auteur: ${reference_brut.auteurs}\nTexte: ${reference_brut.dispositif}\nTEST - Auteur: ${am.auteurs}\nTexte: ${am.dispositif}`
    
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'local-model', // LM Studio ignore souvent le nom
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt }
          ],
          temperature: 0.1,
          max_tokens: 200
        })
      })

      if (!res.ok) throw new Error("Erreur réseau vers LM Studio")
      
      const jsonRes = await res.json()
      let contenu = jsonRes.choices[0].message.content.trim()
      
      // Nettoyage Markdown (```json ... ```)
      contenu = contenu.replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '').trim()
      const match = contenu.match(/\[.*\]|\{.*\}/s)
      if (match) contenu = match[0]
      
      let parsed = JSON.parse(contenu)
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
    } catch (err) {
      console.error("Erreur LM Studio:", err)
      resultats.push({
        id: am.id || am.numero,
        statut: "Erreur",
        justification: "Échec de connexion ou de formatage avec LM Studio.",
        alerte_couleur: "rouge",
        rang: i + 1
      })
      avertissements.push(`L'amendement ${am.numero} a échoué en local.`)
    }
  }

  // 3. Attribution des groupes basique
  let grpId = 1
  for (const r of resultats) {
    if (r.statut === "Identique") {
      r.groupe = { type: "identiques", groupe_id: `grp-identiques-1` }
    } else if (r.statut === "Discussion commune") {
      r.groupe = { type: "discussion_commune", groupe_id: `grp-discussion_commune-1` }
    }
  }

  return { classement: resultats, avertissements, modele_utilise: 'LM Studio (Local)' }
}
