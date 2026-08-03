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
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
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
  const startTime = performance.now()
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

  const baseRules = "TU DOIS RENVOYER UNIQUEMENT UN TABLEAU JSON BRUT. AUCUN FORMATAGE MARKDOWN. AUCUNE BALISE.\nRÈGLE ABSOLUE : N'utilise JAMAIS les statuts 'Identique' ou 'Doublon'. Ces statuts sont gérés en amont par le système. Tu dois uniquement détecter les 'Discussion commune' ou 'Isolé'.\n\n"
  
  const currentModel = provider === 'local' ? (aiSettings.localModel || '') : (aiSettings.groqModel || '')
  const isModelReasoning = /gemma|qwq|reasoning/i.test(currentModel)
  
  const preamble = isModelReasoning 
    ? "PENSÉE ULTRA-COURTE : Limitez votre raisonnement interne à 2 phrases maximum avant de générer le tableau JSON.\n\n"
    : ""
  
  const systemPrompt = isReasoningMode
    ? preamble + baseRules + "Tu es un expert. Prends le temps de réfléchir. À la TOUTE FIN, génère un tableau JSON pur respectant EXACTEMENT ce format : [{\"id\": \"id_de_lamendement\", \"statut\": \"Discussion commune\" | \"Isolé\", \"justification\": \"...\", \"alerte_couleur\": \"vert\" | \"orange\" | \"gris\"}]"
    : preamble + baseRules + "TU ES UN AUTOMATE. Renvoie UNIQUEMENT un tableau JSON pur respectant EXACTEMENT ce format : [{\"id\": \"id_de_lamendement\", \"statut\": \"Discussion commune\" | \"Isolé\", \"justification\": \"...\", \"alerte_couleur\": \"vert\" | \"orange\" | \"gris\"}]"

  const activeTemperature = isModelReasoning ? 0.2 : 0.1

  let localUrl = (aiSettings.localUrl || 'http://localhost:1234/v1').trim()
  localUrl = localUrl.replace(/\/+$/, '').replace(/\/[vV]1$/, '')
  const endpoint = provider === 'local' ? `${localUrl}/v1/chat/completions` : `${API_BASE_URL}/api/analyze_batch`

  // Preflight local
  if (provider === 'local') {
    try {
      const preflight = await fetch(`${localUrl}/v1/models`, {
        method: 'GET',
        headers: { 'ngrok-skip-browser-warning': 'true' },
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

  // GROUP BY ARTICLE
  const articlesMap = new Map()
  toClassifyByLLM.forEach(am => {
    const art = am.article || "Inconnu"
    if (!articlesMap.has(art)) articlesMap.set(art, [])
    articlesMap.get(art).push(am)
  })

  let consecutiveFailures = 0
  const resultats = []

  for (const [article, batch] of articlesMap.entries()) {
    if (abortRef.current || signal?.aborted) {
      avertissements.push("🛑 Classement annulé par l'utilisateur.")
      break
    }

    if (consecutiveFailures >= 2) {
      batch.forEach(am => {
        processedCount++
        const res = { id: am.id || am.numero, statut: 'Erreur', justification: 'Interrompu : trop d\'échecs.', alerte_couleur: 'rouge', rang: processedCount }
        resultats.push(res)
        onProgress(res, processedCount, amendements.length, avertissements)
      })
      continue
    }

    let userPrompt = `Voici les amendements pour l'article ${article} :\n\n`
    batch.forEach(am => {
       const expose = isReasoningMode && am.expose_sommaire ? `\nEXPOSE: ${am.expose_sommaire}` : ''
       userPrompt += `ID: ${am.id || am.numero}\nDISPOSITIF: ${am.dispositif}${expose}\n\n`
    })

    try {
      let parsedArray = []

      if (provider === 'local') {
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
          signal,
          body: JSON.stringify({
            model: aiSettings.localModel || 'local-model',
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: userPrompt }
            ],
            temperature: activeTemperature
          })
        })
        if (!res.ok) throw new Error(`API a répondu ${res.status}`)
        const jsonRes = await res.json()
        const contenu = jsonRes.choices[0].message.content.trim()
        const jsonStr = cleanJsonPayload(contenu)
        parsedArray = JSON.parse(jsonStr)
      } else {
        const payload = {
          user_prompt: userPrompt,
          provider: 'groq',
          model: aiSettings.groqModel || 'llama3-8b-8192',
          api_key: aiSettings.apiKey || null,
          system_prompt: systemPrompt
        }
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
          signal,
          body: JSON.stringify(payload)
        })
        if (!res.ok) throw new Error(`Erreur Backend ${res.status}`)
        const data = await res.json()
        if (Array.isArray(data)) {
           parsedArray = data
        } else if (data && typeof data === 'object' && !Array.isArray(data)) {
           parsedArray = [data]
        } else {
           throw new Error("Réponse API invalide")
        }
      }

      if (!Array.isArray(parsedArray)) {
          throw new Error("Le résultat n'est pas un tableau")
      }

      // Traiter les résultats
      batch.forEach(am => {
        processedCount++
        const amId = String(am.id || am.numero)
        const parsed = parsedArray.find(p => String(p.id) === amId) || {}

        const statut = parsed.statut || 'Isolé'
        const alerte_couleur = parsed.alerte_couleur || (statut === 'Identique' ? 'orange' : 'vert')
        
        const finalRes = {
          id: amId,
          statut,
          justification: parsed.justification || '',
          alerte_couleur,
          rang: processedCount
        }
        
        if (finalRes.statut === 'Identique') {
           finalRes.groupe = { type: 'identiques', groupe_id: 'grp-identiques-llm' }
        } else if (finalRes.statut === 'Discussion commune' || finalRes.statut === 'Incompatible') {
           finalRes.groupe = { type: 'discussion_commune', groupe_id: 'grp-discussion_commune-1' }
        }

        resultats.push(finalRes)
        onProgress(finalRes, processedCount, amendements.length, avertissements)
      })
      
      consecutiveFailures = 0

    } catch (err) {
      if (err.name === 'AbortError') {
        avertissements.push("🛑 Classement annulé par l'utilisateur.")
        break
      }
      console.error('Erreur IA Batch:', err)
      consecutiveFailures++
      batch.forEach(am => {
        processedCount++
        const errorRes = {
          id: am.id || am.numero,
          statut: 'Erreur IA',
          justification: err.message || 'Échec de traitement.',
          alerte_couleur: 'rouge',
          rang: processedCount
        }
        resultats.push(errorRes)
        onProgress(errorRes, processedCount, amendements.length, avertissements)
      })
    }

    try {
      await cancellableDelay(provider === 'local' ? 0 : 3000, signal)
    } catch (e) {
      if (e.name === 'AbortError') {
        avertissements.push("🛑 Classement annulé par l'utilisateur.")
        break
      }
    }
  }

  const endTime = performance.now()
  const totalTime = ((endTime - startTime) / 1000).toFixed(2)
  console.log(`⏱️ [Bourbon.IA] Temps total de traitement IA : ${totalTime} secondes.`)
  avertissements.push(`⏱️ Traitement IA terminé en ${totalTime} secondes.`)

  return {
    classement: [...preClassified, ...resultats],
    avertissements,
    modele_utilise: provider === 'local' ? 'Modèle Local Souverain' : 'Groq Cloud (Démo)'
  }
}
