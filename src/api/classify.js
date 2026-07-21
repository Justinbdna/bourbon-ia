import { preSortAmendements } from '../utils/sortingEngine'

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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amendements, model: 'llama3-8b-8192' }),
  })
  if (!response.ok) {
    throw new ClassifyError(`Erreur de normalisation: ${await response.text()}`, response.status)
  }
  return await response.json()
}

export async function classifyAmendments(amendements, options = {}) {
  const { aiSettings = {}, isReasoningMode = false, abortRef = { current: false }, onProgress = () => {} } = options
  const provider = aiSettings.provider || 'groq'

  // PRÉ-TRI MÉCANIQUE
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
    avertissements.push(`✅ ${preClassified.length} amendement(s) classé(s) mécaniquement (Identiques).`)
  }

  // Notifier l'UI pour les amendements pré-classés
  preClassified.forEach((res, i) => {
    onProgress(res, i + 1, amendements.length, avertissements)
  })

  let processedCount = preClassified.length

  if (toClassifyByLLM.length === 0) {
    return { classement: preClassified, avertissements, modele_utilise: 'Moteur déterministe (sans IA)' }
  }

  const systemPrompt = isReasoningMode
    ? "Tu es un expert. Prends le temps de réfléchir et d'analyser. À la TOUTE FIN de ton analyse, tu DOIS obligatoirement générer un bloc JSON pur respectant EXACTEMENT ce format : {\"statut\": \"Identique\" | \"Discussion commune\" | \"Isolé\", \"justification\": \"en français\", \"alerte_couleur\": \"vert\" | \"orange\" | \"gris\"}"
    : "TU ES UN AUTOMATE. AUCUNE RÉFLEXION AUTORISÉE. Renvoie UNIQUEMENT le JSON pur, sans aucun texte avant ni après. Format STRICT : {\"statut\": \"Identique\" | \"Discussion commune\" | \"Isolé\", \"justification\": \"en français\", \"alerte_couleur\": \"vert\" | \"orange\" | \"gris\"}"

  const reference_brut = toClassifyByLLM[0]
  const refResult = {
    id: reference_brut.id || reference_brut.numero,
    statut: 'Isolé',
    justification: 'Premier du lot (Référence).',
    alerte_couleur: 'vert',
    rang: processedCount + 1
  }
  
  const resultats = [refResult]
  processedCount++
  onProgress(refResult, processedCount, amendements.length, avertissements)

  let localUrl = (aiSettings.localUrl || 'http://localhost:1234/v1').trim()
  localUrl = localUrl.replace(/\/+$/, '').replace(/\/[vV]1$/, '')
  const endpoint = provider === 'local' ? `${localUrl}/v1/chat/completions` : `${API_BASE_URL}/api/analyze`

  // Preflight local
  if (provider === 'local') {
    try {
      const preflight = await fetch(`${localUrl}/v1/models`, { method: 'GET', signal: AbortSignal.timeout(5000) })
      if (!preflight.ok) throw new Error(`Status ${preflight.status}`)
    } catch (err) {
      const diag = 'Connexion impossible vers LM Studio (CORS, non démarré, etc.)'
      avertissements.push(`⚠️ Serveur local injoignable. ${diag}`)
      const fallback = toClassifyByLLM.map((am, i) => {
         processedCount++
         const res = { id: am.id || am.numero, statut: 'Erreur', justification: diag, alerte_couleur: 'rouge', rang: processedCount }
         onProgress(res, processedCount, amendements.length, avertissements)
         return res
      })
      return { classement: [...preClassified, ...fallback], avertissements, modele_utilise: 'Local - Erreur' }
    }
  }

  let consecutiveFailures = 0

  for (let i = 1; i < toClassifyByLLM.length; i++) {
    if (abortRef.current) {
      avertissements.push("🛑 Classement annulé par l'utilisateur.")
      break
    }

    const am = toClassifyByLLM[i]
    processedCount++

    if (consecutiveFailures >= 2) {
      const res = { id: am.id || am.numero, statut: 'Erreur', justification: 'Interrompu : trop d\'échecs.', alerte_couleur: 'rouge', rang: processedCount }
      resultats.push(res)
      onProgress(res, processedCount, amendements.length, avertissements)
      continue
    }

    try {
      let parsed = null

      if (provider === 'local') {
        const userPrompt = `REF: ${reference_brut.dispositif}\nTEST: ${am.dispositif}`
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'local-model',
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: userPrompt }
            ],
            temperature: isReasoningMode ? 0.6 : 0.1,
            max_tokens: 8192
          })
        })
        if (!res.ok) throw new Error(`API a répondu ${res.status}`)
        const jsonRes = await res.json()
        const contenu = jsonRes.choices[0].message.content.trim()

        // Extracteur blindé
        const firstBrace = contenu.indexOf('{')
        const lastBrace = contenu.lastIndexOf('}')
        if (firstBrace === -1 || lastBrace === -1 || lastBrace < firstBrace) {
           throw new Error("Aucun objet JSON trouvé dans la réponse")
        }
        const jsonStr = contenu.substring(firstBrace, lastBrace + 1)
        parsed = JSON.parse(jsonStr)
      } else {
        // Mode Cloud Groq (Backend FastAPI)
        // On envoie un batch de 2 amendements : la ref et celui à tester
        const payload = {
          amendements: [reference_brut, am],
          provider: 'groq',
          api_key: aiSettings.apiKey || null,
          system_prompt: systemPrompt
        }
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        if (!res.ok) {
          const status = res.status
          if (status === 429) throw new Error('Quota de tokens dépassé.')
          throw new Error(`Erreur Vercel ${status}`)
        }
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
           // le premier résultat retourné par le backend correspond au testé
           parsed = data[0]
        } else {
           throw new Error("Réponse Vercel invalide")
        }
      }

      const statut = parsed.statut || 'Isolé'
      const alerte_couleur = parsed.alerte_couleur || (statut === 'Identique' ? 'orange' : 'vert')
      
      const finalRes = {
        id: am.id || am.numero,
        statut,
        justification: parsed.justification || '',
        alerte_couleur,
        rang: processedCount
      }
      
      // Assignation de groupe
      if (finalRes.statut === 'Identique') {
         finalRes.groupe = { type: 'identiques', groupe_id: 'grp-identiques-llm' }
      } else if (finalRes.statut === 'Discussion commune' || finalRes.statut === 'Incompatible') {
         finalRes.groupe = { type: 'discussion_commune', groupe_id: 'grp-discussion_commune-1' }
      }

      resultats.push(finalRes)
      onProgress(finalRes, processedCount, amendements.length, avertissements)
      consecutiveFailures = 0

    } catch (err) {
      console.error('Erreur IA:', err)
      consecutiveFailures++
      const errorRes = {
        id: am.id || am.numero,
        statut: 'Erreur IA',
        justification: err.message || 'Échec de traitement.',
        alerte_couleur: 'rouge',
        rang: processedCount
      }
      resultats.push(errorRes)
      onProgress(errorRes, processedCount, amendements.length, avertissements)
    }
  }

  const allResults = [...preClassified, ...resultats]
  return { classement: allResults, avertissements, modele_utilise: provider === 'local' ? 'Local' : 'Groq (Cloud)' }
}
