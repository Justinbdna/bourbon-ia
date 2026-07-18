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
export async function classifyAmendments(amendements) {
  const payload = { amendements }
  console.log("PAYLOAD ENVOYÉ:", payload)

  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch (err) {
    throw new ClassifyError(
      `Impossible de joindre le serveur (${API_BASE_URL}). Le backend est-il bien lancé ? (${err.message})`,
      0
    )
  }

  if (!response.ok) {
    const errorText = await response.text()
    console.error("RÉPONSE BRUTE:", errorText)
    throw new ClassifyError(`Erreur ${response.status}: ${errorText}`, response.status)
  }

  let data = null
  try {
    data = await response.json()
  } catch {
    // pas de corps JSON exploitable
  }

  // Traduction du tableau direct en objet attendu par le front
  if (Array.isArray(data)) {
    return { classement: data, avertissements: [], modele_utilise: 'Local' }
  }
  return data
}
