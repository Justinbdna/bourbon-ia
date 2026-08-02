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

/**
 * Nettoie le payload de réponse LLM (surtout pour les modèles de raisonnement).
 * 1. Supprime les blocs <think>...</think>
 * 2. Extrait le premier { ou [ jusqu'au dernier } ou ]
 */
function cleanJsonPayload(rawText) {
  if (!rawText) return ""
  let text = rawText.replace(/<think>[\s\S]*?<\/think>/gi, '')
  
  // Supprimer les blocs Markdown
  text = text.replace(/```[a-z]*\n?/gi, '')
  text = text.replace(/```/g, '')

  
  const firstBrace = text.indexOf('{')
  const firstBracket = text.indexOf('[')
  const lastBrace = text.lastIndexOf('}')
  const lastBracket = text.lastIndexOf(']')

  let start = -1
  let end = -1

  if (firstBrace !== -1 && (firstBracket === -1 || firstBrace < firstBracket)) {
    start = firstBrace
    end = lastBrace
  } else if (firstBracket !== -1) {
    start = firstBracket
    end = lastBracket
  }

  if (start === -1 || end === -1 || end < start) {
    throw new Error("Aucun objet JSON valide trouvé dans la réponse")
  }

  return text.substring(start, end + 1)
}

/**
 * Temporisation annulable : résout après `ms` millisecondes,
 * mais rejette immédiatement si `signal` est avorté.
 */
function cancellableDelay(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(new DOMException('Aborted', 'AbortError')); return }
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }, { once: true })
  })
}

export async function classifyAmendments(amendements, options = {}) {
  const {
    aiSettings = {},
    isReasoningMode = false,
    abortRef = { current: false },
    signal,            // AbortController.signal
    onProgress = () => {}
  } = options
  const provider = aiSettings.provider || 'local'

  // PRÉ-TRI MÉCANIQUE
  const preSorted = preSortAmendements(amendements)
  const toClassifyByLLM = preSorted.filter(am => !am._skipLLM)
  const preClassified = preSorted.filter(am => am._skipLLM).map(am => ({
    id: am.id,
    statut: am._groupe?.type === 'doublon' ? 'Doublon' : 'Identique',
    justification: am._groupe?.type === 'doublon' 
      ? 'Détecté mécaniquement : Doublon irrecevable (même auteur, même texte).'
      : 'Détecté mécaniquement : Identique admissible (même texte, auteurs différents).',
    alerte_couleur: am._groupe?.type === 'doublon' ? 'rouge' : 'orange',
    rang: am._rang,
    groupe: am._groupe
  }))

  const avertissements = []
  if (preClassified.length > 0) {
    avertissements.push(`✅ ${preClassified.length} amendement(s) classé(s) mécaniquement (Identiques/Doublons).`)
  }

  // Notifier l'UI pour les amendements pré-classés
  preClassified.forEach((res, i) => {
    onProgress(res, i + 1, amendements.length, avertissements)
  })

  let processedCount = preClassified.length

  if (toClassifyByLLM.length === 0) {
    return { classement: preClassified, avertissements, modele_utilise: 'Moteur déterministe (sans IA)' }
  }

  const baseRules = "TU DOIS RENVOYER UNIQUEMENT DU JSON BRUT. AUCUN FORMATAGE MARKDOWN. AUCUNE BALISE.\nRÈGLE ABSOLUE : N'utilise JAMAIS les statuts 'Identique' ou 'Doublon'. Ces statuts sont gérés en amont par le système. Tu dois uniquement détecter les 'Discussion commune' ou 'Isolé'.\n\n"
  const systemPrompt = isReasoningMode
    ? baseRules + "Tu es un expert. Prends le temps de réfléchir et d'analyser. À la TOUTE FIN de ton analyse, génère le bloc JSON pur respectant EXACTEMENT ce format : {\"statut\": \"Discussion commune\" | \"Isolé\", \"justification\": \"en français\", \"alerte_couleur\": \"vert\" | \"orange\" | \"gris\"}"
    : baseRules + "TU ES UN AUTOMATE. AUCUNE RÉFLEXION AUTORISÉE. Renvoie UNIQUEMENT le JSON pur respectant EXACTEMENT ce format : {\"statut\": \"Discussion commune\" | \"Isolé\", \"justification\": \"en français\", \"alerte_couleur\": \"vert\" | \"orange\" | \"gris\"}"

  const dynamicMaxTokens = isReasoningMode ? 16384 : 4096

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
      const preflight = await fetch(`${localUrl}/v1/models`, {
        method: 'GET',
        signal: signal || AbortSignal.timeout(5000)
      })
      if (!preflight.ok) throw new Error(`Status ${preflight.status}`)
    } catch (err) {
      if (err.name === 'AbortError') throw err
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
    // Vérification d'annulation AVANT chaque itération
    if (abortRef.current || signal?.aborted) {
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
        const refPrompt = isReasoningMode && reference_brut.expose_sommaire 
          ? `REF_DISPOSITIF: ${reference_brut.dispositif}\nREF_EXPOSE: ${reference_brut.expose_sommaire}` 
          : `REF_DISPOSITIF: ${reference_brut.dispositif}`
        const amPrompt = isReasoningMode && am.expose_sommaire 
          ? `TEST_DISPOSITIF: ${am.dispositif}\nTEST_EXPOSE: ${am.expose_sommaire}` 
          : `TEST_DISPOSITIF: ${am.dispositif}`
        const userPrompt = `${refPrompt}\n\n${amPrompt}`

        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal,
          body: JSON.stringify({
            model: 'local-model',
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: userPrompt }
            ],
            temperature: isReasoningMode ? 0.6 : 0.1,
            max_tokens: dynamicMaxTokens
          })
        })
        if (!res.ok) throw new Error(`API a répondu ${res.status}`)
        const jsonRes = await res.json()
        const contenu = jsonRes.choices[0].message.content.trim()

        // Extracteur blindé avec suppression des <think>
        const jsonStr = cleanJsonPayload(contenu)
        parsed = JSON.parse(jsonStr)
      } else {
        // Mode Cloud Groq (Backend FastAPI)
        const cloudAmends = isReasoningMode 
          ? [reference_brut, am] 
          : [
              { ...reference_brut, expose_sommaire: undefined }, 
              { ...am, expose_sommaire: undefined }
            ]

        const payload = {
          amendements: cloudAmends,
          provider: 'groq',
          api_key: aiSettings.apiKey || null,
          system_prompt: systemPrompt,
          max_tokens: dynamicMaxTokens
        }
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal,
          body: JSON.stringify(payload)
        })
        if (!res.ok) {
          const status = res.status
          if (status === 429) throw new Error('Quota de tokens dépassé.')
          throw new Error(`Erreur Vercel ${status}`)
        }
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
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
      // Propager les AbortError pour arrêter proprement la boucle
      if (err.name === 'AbortError') {
        avertissements.push("🛑 Classement annulé par l'utilisateur.")
        break
      }
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

    // ⏱️ Temporisation Anti-Rate-Limit — ANNULABLE
    try {
      await cancellableDelay(3000, signal)
    } catch (e) {
      if (e.name === 'AbortError') {
        avertissements.push("🛑 Classement annulé par l'utilisateur.")
        break
      }
    }
  }

  const allResults = [...preClassified, ...resultats]
  return { classement: allResults, avertissements, modele_utilise: provider === 'local' ? 'Local' : 'Groq (Cloud)' }
}
