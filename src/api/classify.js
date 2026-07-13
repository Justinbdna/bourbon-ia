const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
 * Envoie les amendements au backend FastAPI pour classement par l'IA.
 * Renvoie { classement, avertissements, modele_utilise }.
 */
export async function classifyAmendments(amendements) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/classify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amendements }),
    })
  } catch (err) {
    throw new ClassifyError(
      `Impossible de joindre le serveur (${API_BASE_URL}). Le backend est-il bien lancé ? (${err.message})`,
      0
    )
  }

  let data = null
  try {
    data = await response.json()
  } catch {
    // pas de corps JSON exploitable
  }

  if (!response.ok) {
    const detail = data?.detail || `Erreur serveur (${response.status})`
    throw new ClassifyError(detail, response.status)
  }

  return data
}
