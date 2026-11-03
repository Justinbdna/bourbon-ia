import { useState, useEffect } from 'react'

function getModelTypeBadge(modelObj) {
  if (!modelObj) {
    return {
      icon: '⚠️',
      text: 'Aucun modèle détecté. Vérifiez que votre serveur local (LM Studio / Ollama) est démarré.',
      colorClass: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800'
    }
  }

  const id = typeof modelObj === 'string' ? modelObj : modelObj.id;
  if (!id) return null;
  
  const isReasoning = /gemma|qwq|reasoning/i.test(id)
  
  let params = 0;
  const paramMatch = id.match(/(\d+(?:\.\d+)?)b/i);
  if (paramMatch) params = parseFloat(paramMatch[1]);
  
  let bits = 8;
  const quantStr = (typeof modelObj === 'object' && modelObj.quantization) ? modelObj.quantization : id;
  const quantMatch = quantStr.match(/q(\d+)/i);
  if (quantMatch) bits = parseInt(quantMatch[1], 10);
  
  let estimatedVram = params > 0 ? (params * bits / 8) + 1.5 : 0;
  if (typeof modelObj === 'object' && modelObj.size_bytes) {
    estimatedVram = (modelObj.size_bytes / 1073741824) + 1.5;
  }
  
  const isVoluminous = estimatedVram > 14 || /32b|70b/i.test(id);
  const isLightweight8GB = /llama-?3\.?2-?3b|qwen-?2\.?5-?(?:3b|7b)|gemma-?3-?4b/i.test(id) || (estimatedVram > 0 && estimatedVram <= 5);
  const isRecommended = isLightweight8GB || (estimatedVram > 0 && estimatedVram < 10) || /llama-?3\.?1-?8b|mistral-?7b/i.test(id);

  if (isLightweight8GB) {
    return {
      icon: '⚡',
      text: 'Mode Léger (8 Go RAM) — Inférence ultra-rapide (~2 à 4,5 Go RAM), idéal pour ordinateur portable.',
      colorClass: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800'
    }
  } else if (isReasoning) {
    return { 
      icon: '🟡', 
      text: 'Modèle Reasoning — Mode analyse approfondie optimisé.', 
      colorClass: 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800' 
    }
  } else if (isVoluminous) {
    return {
      icon: '🔵',
      text: "Modèle Volumineux — Assurez-vous d'avoir plus de 12 Go de VRAM sur votre GPU.",
      colorClass: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800'
    }
  } else if (isRecommended) {
    return { 
      icon: '⭐', 
      text: 'Modèle Recommandé — Inférence rapide (< 15s) et empreinte VRAM faible (~5-8 Go).', 
      colorClass: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800' 
    }
  } else {
    return { 
      icon: '🔵', 
      text: 'Modèle Personnalisé — Traitement standard.', 
      colorClass: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800' 
    }
  }
}

function formatModelName(id) {
  if (!id) return ''
  const parts = id.split('/')
  const baseName = parts[parts.length - 1]
  let formatted = baseName.replace(/[-_]/g, ' ')
  return formatted.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

export default function AISettingsModal({ isOpen, onClose, onSave, currentSettings }) {
  const [provider, setProvider] = useState(currentSettings?.provider || 'groq_auto')
  const [apiKey, setApiKey] = useState(currentSettings?.apiKey || '')
  const [localUrl, setLocalUrl] = useState(currentSettings?.localUrl || 'http://localhost:1234/v1')
  const [localModel, setLocalModel] = useState(currentSettings?.localModel || '')
  const [groqModel, setGroqModel] = useState((currentSettings?.groqModel && currentSettings.groqModel !== 'llama-3.3-70b-versatile') ? currentSettings.groqModel : 'openai/gpt-oss-20b')
  
  const [modelsList, setModelsList] = useState([])
  const [isFetchingModels, setIsFetchingModels] = useState(false)
  const [pingStatus, setPingStatus] = useState(null)

  useEffect(() => {
    if (isOpen) {
      setProvider(currentSettings?.provider || 'groq_auto')
      setApiKey(currentSettings?.apiKey || '')
      setLocalUrl(currentSettings?.localUrl || 'http://localhost:1234/v1')
      setLocalModel(currentSettings?.localModel || '')
      setGroqModel((currentSettings?.groqModel && currentSettings.groqModel !== 'llama-3.3-70b-versatile') ? currentSettings.groqModel : 'openai/gpt-oss-20b')
      setPingStatus(null)
    }
  }, [isOpen, currentSettings])

  useEffect(() => {
    if (!isOpen) return
    let isMounted = true

    const fetchModels = async () => {
      if (provider === 'groq_auto') {
        if (isMounted) {
          // Modèle réellement utilisé en mode démo (cf. src/api/classify.js)
          setModelsList([{ id: 'openai/gpt-oss-20b' }])
          setIsFetchingModels(false)
        }
        return
      }

      if (isMounted) setIsFetchingModels(true)
      try {
        let headers = { 'ngrok-skip-browser-warning': 'true' }
        if (provider === 'groq') {
          if (!apiKey) {
            if (isMounted) { setModelsList([]); setIsFetchingModels(false); }
            return
          }
          headers['Authorization'] = `Bearer ${apiKey}`
        }

        let data = null;
        if (provider === 'local') {
          const baseUrl = localUrl.replace(/\/+$/, '').replace(/\/[vV]1$/, '');
          const isHttpsPage = typeof window !== 'undefined' && window.location?.protocol === 'https:';
          if (isHttpsPage && /^http:\/\//i.test(baseUrl)) {
            if (isMounted) {
              setModelsList([]);
              setIsFetchingModels(false);
            }
            return;
          }
          try {
            const resV0 = await fetch(`${baseUrl}/api/v0/models`, { method: 'GET', headers })
            if (resV0.ok) data = await resV0.json()
          } catch {
            // ignore v0 failure
          }
          if (!data || !Array.isArray(data.data)) {
            const resV1 = await fetch(`${baseUrl}/v1/models`, { method: 'GET', headers })
            if (resV1.ok) data = await resV1.json()
          }
        } else {
          const res = await fetch('https://api.groq.com/openai/v1/models', { method: 'GET', headers })
          if (res.ok) data = await res.json()
        }
        
        if (isMounted && data && Array.isArray(data.data)) {
          const filteredModels = data.data.filter(
            m => m.type !== 'embeddings' && !/embed|nomic|rerank|whisper|orpheus|guard|safeguard|tts|vision-preview/i.test(m.id)
          )
          setModelsList(filteredModels)
          if (provider === 'local' && !localModel && filteredModels.length > 0) setLocalModel(filteredModels[0].id)
          if (provider === 'groq' && filteredModels.length > 0 && (!groqModel || !filteredModels.some(m => m.id === groqModel))) {
            const preferred = ['openai/gpt-oss-20b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-120b']
            const best = preferred.find(p => filteredModels.some(m => m.id === p)) || filteredModels[0].id
            setGroqModel(best)
          }
        } else if (isMounted) {
          setModelsList([])
        }
      } catch {
        if (isMounted) setModelsList([])
      }
      if (isMounted) setIsFetchingModels(false)
    }

    const timer = setTimeout(() => {
      fetchModels()
    }, 500)
    
    return () => {
      isMounted = false
      clearTimeout(timer)
    }
  }, [isOpen, provider, localUrl, apiKey])

  if (!isOpen) return null

  const handleSave = async () => {
    const cleanKey = apiKey.trim()
    const effectiveProvider = (provider === 'groq_auto' && cleanKey) ? 'groq' : provider
    const payloadToSave = {
      provider: effectiveProvider,
      apiKey: cleanKey,
      localUrl,
      localModel: localModel || 'local-model',
      groqModel: (groqModel && groqModel !== 'llama-3.3-70b-versatile') ? groqModel : 'openai/gpt-oss-20b'
    }

    if (effectiveProvider === 'local' || effectiveProvider === 'groq') {
      try {
        setPingStatus({ type: 'loading', message: 'Test de connexion et chargement du modèle...' })

        if (effectiveProvider === 'local') {
          const baseUrl = localUrl.replace(/\/+$/, '').replace(/\/[vV]1$/, '')
          const isHttpsPage = typeof window !== 'undefined' && window.location?.protocol === 'https:'
          if (isHttpsPage && /^http:\/\//i.test(baseUrl)) {
            onSave(payloadToSave)
            onClose()
            return
          }
          try {
            const unloadEndpoint = `${baseUrl}/v1/models/unload`
            await fetch(unloadEndpoint, { 
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' }
            })
          } catch (e) {
            console.warn("Échec du déchargement du modèle", e)
          }
        }

        if (effectiveProvider === 'groq') {
          const res = await fetch('https://api.groq.com/openai/v1/models', {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${cleanKey}`,
              'Content-Type': 'application/json',
            }
          })
          if (!res.ok) {
            if (res.status === 401 || res.status === 403) {
              throw new Error('AUTH_ERROR')
            }
            throw new Error('Status ' + res.status)
          }
        } else {
          const chatEndpoint = `${localUrl.replace(/\/+$/, '').replace(/\/[vV]1$/, '')}/v1/chat/completions`
          const res = await fetch(chatEndpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({
              model: localModel || 'local-model',
              messages: [{ role: 'user', content: 'ping' }],
              max_tokens: 1
            })
          })
          if (!res.ok) {
            throw new Error('Status ' + res.status)
          }
        }

        // Sauvegarde immédiate dès validation pour éviter toute perte si la modale est fermée
        onSave(payloadToSave)
        setPingStatus({ type: 'success', message: '🟢 Modèle chargé et connecté' })
        setTimeout(() => {
          setPingStatus(null)
          onClose()
        }, 600)
        return
      } catch (err) {
        if (err?.message === 'AUTH_ERROR') {
          setPingStatus({ type: 'error', message: '⚠️ Clé API Groq invalide ou expirée.' })
          setTimeout(() => setPingStatus(null), 4000)
          return
        }
        // Si une clé personnelle valide (gsk_...) est saisie mais que le navigateur bloque l'appel direct (CORS / bloqueur),
        // on sauvegarde quand même la clé pour qu'elle soit transmise au backend FastAPI.
        if (effectiveProvider === 'groq' && cleanKey) {
          onSave(payloadToSave)
          setPingStatus({ type: 'success', message: '🟢 Clé API enregistrée (relais serveur activé)' })
          setTimeout(() => {
            setPingStatus(null)
            onClose()
          }, 600)
          return
        }
        setPingStatus({
          type: 'error',
          message: '⚠️ Échec du chargement : Mémoire VRAM insuffisante ou modèle indisponible sur le serveur hôte.'
        })
        setTimeout(() => setPingStatus(null), 4000)
        return
      }
    }
    
    onSave(payloadToSave)
    onClose()
  }

  const selectedLocalModelObj = modelsList.find(m => m.id === localModel) || localModel
  const modelBadgeLocal = provider === 'local' ? 
    ((!isFetchingModels && modelsList.length === 0) ? getModelTypeBadge(null) : getModelTypeBadge(selectedLocalModelObj)) : null

  const selectedGroqModelObj = modelsList.find(m => m.id === groqModel) || groqModel
  const modelBadgeGroq = provider === 'groq' ? getModelTypeBadge(selectedGroqModelObj) : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-3 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      <div className="bg-white dark:bg-surface text-ink-900 dark:text-plume border border-ink-200 dark:border-ink-700 rounded-xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-200 dark:border-ink-700 bg-slate-50/50 dark:bg-obsidienne flex justify-between items-center">
          <h2 id="settings-title" className="text-lg font-bold text-slate-900 dark:text-plume">⚙️ Réglages IA</h2>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-700 dark:text-ink-400 dark:hover:text-plume transition-colors" aria-label="Fermer">
            ✕
          </button>
        </div>
        
        <div className="p-5 sm:p-6 space-y-6 overflow-y-auto">
          {/* Sélecteur de fournisseur pleine largeur */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <button
              onClick={() => setProvider('groq_auto')}
              className={`w-full py-2.5 px-3 rounded-lg border font-medium text-xs sm:text-sm text-center transition-colors ${
                provider === 'groq_auto' 
                  ? 'bg-slate-100 border-slate-500 text-slate-900 dark:bg-slate-900/50 dark:border-slate-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              ☁️ Groq (Démo)
            </button>
            <button
              onClick={() => { setProvider('groq'); setPingStatus(null); }}
              className={`w-full py-2.5 px-3 rounded-lg border font-medium text-xs sm:text-sm text-center transition-colors ${
                provider === 'groq' 
                  ? 'bg-slate-100 border-slate-500 text-slate-900 dark:bg-slate-900/50 dark:border-slate-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              🔑 Clé API
            </button>
            <button
              onClick={() => { setProvider('local'); setPingStatus(null); }}
              className={`w-full py-2.5 px-3 rounded-lg border font-medium text-xs sm:text-sm text-center transition-colors ${
                provider === 'local'
                  ? 'bg-slate-100 border-slate-500 text-slate-900 dark:bg-slate-900/50 dark:border-slate-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              💻 IA Locale
            </button>
          </div>

          {/* Grille responsive 2 colonnes */}
          {provider === 'groq_auto' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              <div className="space-y-4">
                <div className="flex items-start gap-3 bg-slate-50/50 dark:bg-obsidienne/50 p-4 rounded-lg border border-slate-200 dark:border-slate-800/50">
                  <span className="text-xl">🔒</span>
                  <div className="text-xs sm:text-sm text-slate-800 dark:text-plume/80 leading-relaxed">
                    <strong className="block mb-1 text-slate-900 dark:text-white">Mode Automatique :</strong>
                    L'application utilise une clé API pré-configurée pour la démonstration web. Vous n'avez aucune configuration requise !
                    <div className="mt-2 text-xs text-slate-600 dark:text-slate-400">
                      Vos requêtes sont sécurisées. Aucune donnée n'est conservée sur des serveurs tiers.
                    </div>
                  </div>
                </div>
                
                <div className="flex items-start gap-3 bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg border border-amber-200 dark:border-amber-800/50">
                  <span className="text-xl">⚠️</span>
                  <div className="text-xs sm:text-sm text-amber-900 dark:text-amber-200 leading-relaxed">
                    <strong className="block mb-1">Attention aux quotas :</strong>
                    En cas de forte affluence simultanée, cette API partagée peut atteindre les limites de requêtes (rate-limit).
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-obsidienne space-y-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                    Modèle Démo Actif
                  </span>
                  <div className="text-sm font-mono font-semibold text-slate-900 dark:text-white">
                    openai/gpt-oss-20b
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    Modèle open-source optimisé hébergé sur le cloud Groq. Offre un temps de réponse inférieur à 2 secondes par amendement.
                  </p>
                  <div className="p-2 rounded border border-emerald-300 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                    <span>⚡</span>
                    <span>Ultra-rapide — Aucune configuration requise</span>
                  </div>
                </div>

                <div className="p-4 rounded-lg border border-blue-200 dark:border-blue-900/40 bg-blue-50/40 dark:bg-blue-950/20 text-xs text-blue-900 dark:text-blue-300 space-y-1">
                  <span className="font-semibold block">Souveraineté totale ?</span>
                  <p>
                    Basculez sur l&apos;onglet <strong>💻 IA Locale</strong> pour faire tourner vos amendements en circuit fermé sur votre machine, sans aucune fuite de données vers l&apos;extérieur.
                  </p>
                </div>
              </div>
            </div>
          )}

          {provider === 'groq' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                    Clé API Personnelle
                  </label>
                  <input 
                    type="password"
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    placeholder="gsk_..."
                    className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none font-mono text-xs"
                  />
                  <p className="text-xs text-ink-700 dark:text-ink-300">
                    Utilisez votre propre clé Groq pour lever toute contrainte de quota public.
                  </p>
                </div>

                {pingStatus && (
                  <div className={`p-3 rounded-md text-xs font-medium ${pingStatus.type === 'success' ? 'bg-green-100 text-green-800 border border-green-300' : pingStatus.type === 'error' ? 'bg-red-100 text-red-800 border border-red-300' : 'bg-blue-100 text-blue-800 border border-blue-300'}`}>
                    {pingStatus.message}
                  </div>
                )}

                <div className="flex items-start gap-2 bg-slate-50/50 dark:bg-obsidienne/50 p-3 rounded-md border border-slate-100 dark:border-slate-800/50">
                  <span className="text-sm">🔒</span>
                  <p className="text-xs text-slate-800 dark:text-plume/80 leading-relaxed">
                    <strong>Sécurité :</strong> Votre clé est uniquement sauvegardée localement dans votre navigateur de manière chiffrée.
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                    Modèle Groq
                  </label>
                  {isFetchingModels ? (
                    <p className="text-xs text-ink-500">Chargement des modèles...</p>
                  ) : modelsList.length > 0 ? (
                    <select
                      value={groqModel}
                      onChange={e => setGroqModel(e.target.value)}
                      className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none text-xs"
                    >
                      {modelsList.map(m => (
                        <option key={m.id} value={m.id}>{formatModelName(m.id)}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={groqModel}
                      onChange={e => setGroqModel(e.target.value)}
                      placeholder="openai/gpt-oss-20b"
                      className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none font-mono text-xs"
                    />
                  )}
                  {modelBadgeGroq && (
                    <div className={`p-2.5 mt-2 rounded-md border text-xs flex gap-2 items-start ${modelBadgeGroq.colorClass}`}>
                      <span>{modelBadgeGroq.icon}</span>
                      <span>{modelBadgeGroq.text}</span>
                    </div>
                  )}
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-obsidienne text-xs text-slate-600 dark:text-slate-400 space-y-1.5">
                  <span className="font-semibold text-slate-800 dark:text-white block">Accélération matérielle</span>
                  <p>
                    L'architecture Groq LPU permet d'obtenir des temps d'inférence très rapides même sur des volumes importants d'amendements.
                  </p>
                </div>
              </div>
            </div>
          )}

          {provider === 'local' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              {/* Colonne gauche : URL & Réseau */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                    Endpoint API Locale
                  </label>
                  <input 
                    type="text"
                    value={localUrl}
                    onChange={e => setLocalUrl(e.target.value)}
                    placeholder="http://localhost:1234/v1"
                    className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none font-mono text-xs"
                  />
                </div>

                <div className="text-xs text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800/50 p-3 rounded-lg space-y-2 border border-neutral-200 dark:border-neutral-700/50">
                  <p>💡 <strong>Navigateur recommandé :</strong> Google Chrome ou Edge (basés sur Chromium).</p>
                  <p className="text-amber-700 dark:text-amber-400/90">
                    ⚠️ <strong>CORS / Sécurité :</strong> Si l&apos;application est hébergée en HTTPS, votre endpoint local doit être sécurisé (ex: tunnel Ngrok HTTPS) ou accessible sans blocage d&apos;origine croisée.
                  </p>
                </div>

                {pingStatus && (
                  <div className={`p-3 rounded-md text-xs font-medium ${pingStatus.type === 'success' ? 'bg-green-100 text-green-800 border border-green-300' : pingStatus.type === 'error' ? 'bg-red-100 text-red-800 border border-red-300' : 'bg-blue-100 text-blue-800 border border-blue-300'}`}>
                    {pingStatus.message}
                  </div>
                )}

                <div className="bg-slate-50 dark:bg-obsidienne rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 text-xs text-ink-700 dark:text-ink-300 space-y-1.5">
                  <h3 className="font-semibold text-slate-900 dark:text-plume">Tutoriel Rapide (Air-Gapped)</h3>
                  <ol className="space-y-1 list-decimal list-inside text-[11px] leading-relaxed">
                    <li>Démarrer <strong>LM Studio</strong> ou <strong>Ollama</strong>.</li>
                    <li>Activer impérativement l&apos;option <strong>CORS</strong> dans le serveur local.</li>
                    <li>Copier l&apos;URL locale (<code className="bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded font-mono">http://localhost:1234/v1</code>).</li>
                  </ol>
                </div>
              </div>

              {/* Colonne droite : Modèle & Préréglages */}
              <div className="space-y-4">
                <div className="p-3.5 rounded-lg border border-emerald-200 dark:border-emerald-800/60 bg-emerald-50/70 dark:bg-emerald-950/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-300">
                      ⚡ Mode Léger (8 Go RAM)
                    </span>
                    <span className="text-[10px] text-emerald-700 dark:text-emerald-400">
                      KV-cache &lt; 2048
                    </span>
                  </div>
                  <p className="text-[11px] text-emerald-900/80 dark:text-emerald-200/80">
                    Modèles quantifiés (Q4) optimisés pour MacBook / PC 8 Go RAM :
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-0.5">
                    {[
                      { id: 'llama3.2:3b', label: 'llama3.2:3b', desc: '~2,0 Go RAM — ultra-rapide' },
                      { id: 'qwen2.5:3b', label: 'qwen2.5:3b', desc: '~2,2 Go RAM — français' },
                      { id: 'qwen2.5:7b-instruct-q4_K_M', label: 'qwen2.5:7b-q4', desc: '~4,5 Go RAM — précis' },
                      { id: 'gemma3:4b', label: 'gemma3:4b', desc: '~2,6 Go RAM — équilibré' },
                    ].map(preset => (
                      <button
                        key={preset.id}
                        type="button"
                        onClick={() => setLocalModel(preset.id)}
                        className={`text-left px-2 py-1.5 rounded border text-xs transition-colors ${
                          localModel === preset.id
                            ? 'bg-emerald-600 text-white border-emerald-700 font-semibold shadow-sm'
                            : 'bg-white/90 dark:bg-surface border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 hover:bg-emerald-100 dark:hover:bg-emerald-900/40'
                        }`}
                      >
                        <div className="font-mono text-[11px] truncate">{preset.label}</div>
                        <div className={`text-[10px] ${localModel === preset.id ? 'text-emerald-100' : 'text-emerald-700 dark:text-emerald-400'}`}>
                          {preset.desc}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                    Modèle IA Local
                  </label>
                  {isFetchingModels ? (
                    <p className="text-xs text-ink-500">Recherche des modèles sur l&apos;hôte local...</p>
                  ) : modelsList.length > 0 ? (
                    <select
                      value={localModel}
                      onChange={e => setLocalModel(e.target.value)}
                      className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none text-xs"
                    >
                      {!modelsList.some(m => m.id === localModel) && localModel && (
                        <option value={localModel}>{localModel}</option>
                      )}
                      {modelsList.map(m => (
                        <option key={m.id} value={m.id}>{formatModelName(m.id)}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={localModel}
                      onChange={e => setLocalModel(e.target.value)}
                      placeholder="Ex: llama3.2:3b, qwen2.5:3b, gemma3:4b..."
                      className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none font-mono text-xs"
                    />
                  )}
                  {modelBadgeLocal && (
                    <div className={`p-2.5 mt-2 rounded-md border text-xs flex gap-2 items-start ${modelBadgeLocal.colorClass}`}>
                      <span>{modelBadgeLocal.icon}</span>
                      <span>{modelBadgeLocal.text}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-ink-200 dark:border-ink-700 bg-gray-50 dark:bg-surface flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-ink-600 dark:text-ink-300 hover:text-ink-900 dark:hover:text-plume transition-colors">
            Annuler
          </button>
          <button 
            onClick={handleSave} 
            disabled={pingStatus?.type === 'loading'}
            className="px-4 py-2 bg-slate-900 hover:bg-black text-white text-sm font-medium rounded-md shadow-sm transition-colors disabled:opacity-50"
          >
            {pingStatus?.type === 'loading' ? 'Test en cours...' : 'Enregistrer'}
          </button>
        </div>
      </div>
    </div>
  )
}
