import { useState, useEffect } from 'react'

function getVramWarning(modelName) {
  if (!modelName) return null
  const name = modelName.toLowerCase()
  const match = name.match(/(\d+)b/i)
  if (!match) return null
  const size = parseInt(match[1], 10)

  if (size < 10) {
    return { type: 'vert', icon: '🟢', text: 'Léger & Ultra-Rapide (~6-8 Go VRAM) — Recommandé pour classement en < 15s.', colorClass: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800' }
  } else if (size >= 10 && size <= 16) {
    return { type: 'jaune', icon: '🟡', text: 'Modéré (~8-12 Go VRAM) — Nécessite un GPU dédié. Si l\'analyse est trop rapide et inaccurate, réactivez \'Thinking\' dans LM Studio.', colorClass: 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800' }
  } else {
    return { type: 'rouge', icon: '🔴', text: 'Lourd (20 Go+ VRAM) — Risque de bascule sur la RAM système (CPU) et de forte lenteur si la VRAM est insuffisante.', colorClass: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800' }
  }
}

export default function AISettingsModal({ isOpen, onClose, onSave, currentSettings }) {
  const [provider, setProvider] = useState(currentSettings?.provider || 'groq_auto')
  const [apiKey, setApiKey] = useState(currentSettings?.apiKey || '')
  const [localUrl, setLocalUrl] = useState(currentSettings?.localUrl || 'http://localhost:1234/v1')
  const [localModel, setLocalModel] = useState(currentSettings?.localModel || '')
  const [groqModel, setGroqModel] = useState(currentSettings?.groqModel || '')
  
  const [modelsList, setModelsList] = useState([])
  const [isFetchingModels, setIsFetchingModels] = useState(false)
  const [pingStatus, setPingStatus] = useState(null)

  useEffect(() => {
    if (isOpen) {
      setProvider(currentSettings?.provider || 'groq_auto')
      setApiKey(currentSettings?.apiKey || '')
      setLocalUrl(currentSettings?.localUrl || 'http://localhost:1234/v1')
      setLocalModel(currentSettings?.localModel || '')
      setGroqModel(currentSettings?.groqModel || '')
      setPingStatus(null)
    }
  }, [isOpen, currentSettings])

  useEffect(() => {
    if (!isOpen) return
    let isMounted = true

    const fetchModels = async () => {
      if (provider === 'groq_auto') {
        if (isMounted) {
          setModelsList([{ id: 'llama3-8b-8192' }])
          setIsFetchingModels(false)
        }
        return
      }

      if (isMounted) setIsFetchingModels(true)
      try {
        let endpoint = provider === 'local' 
          ? `${localUrl.replace(/\/+$/, '').replace(/\/[vV]1$/, '')}/v1/models` 
          : 'https://api.groq.com/openai/v1/models'
        
        let headers = { 'ngrok-skip-browser-warning': 'true' }
        if (provider === 'groq') {
          if (!apiKey) {
            if (isMounted) { setModelsList([]); setIsFetchingModels(false); }
            return
          }
          headers['Authorization'] = `Bearer ${apiKey}`
        }

        const res = await fetch(endpoint, { method: 'GET', headers })
        if (!res.ok) throw new Error('Status ' + res.status)
        const data = await res.json()
        
        if (isMounted && data && Array.isArray(data.data)) {
          setModelsList(data.data)
          if (provider === 'local' && !localModel && data.data.length > 0) setLocalModel(data.data[0].id)
          if (provider === 'groq' && !groqModel && data.data.length > 0) setGroqModel(data.data[0].id)
        } else if (isMounted) {
          setModelsList([])
        }
      } catch (err) {
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
    if (provider === 'local' || provider === 'groq') {
      try {
        setPingStatus({ type: 'loading', message: 'Test de connexion et chargement du modèle...' })
        
        let chatEndpoint = provider === 'local' 
          ? `${localUrl.replace(/\/+$/, '').replace(/\/[vV]1$/, '')}/v1/chat/completions` 
          : 'https://api.groq.com/openai/v1/chat/completions'

        let headers = {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        }
        if (provider === 'groq') headers['Authorization'] = `Bearer ${apiKey}`

        const modelToTest = provider === 'local' ? localModel : groqModel

        const res = await fetch(chatEndpoint, { 
          method: 'POST', 
          headers,
          body: JSON.stringify({
            model: modelToTest || 'default',
            messages: [{ role: 'user', content: 'ping' }],
            max_tokens: 1
          })
        })
        
        if (!res.ok) throw new Error('Status ' + res.status)

        setPingStatus({ type: 'success', message: '🟢 Modèle chargé et connecté' })
        setTimeout(() => {
          setPingStatus(null)
          onSave({ provider, apiKey: provider === 'groq_auto' ? '' : apiKey, localUrl, localModel, groqModel })
          onClose()
        }, 1500)
        return
      } catch (err) {
        setPingStatus({ type: 'error', message: '⚠️ Échec du chargement : Mémoire VRAM insuffisante ou modèle indisponible sur le serveur hôte.' })
        setTimeout(() => setPingStatus(null), 4000)
        return
      }
    }
    
    onSave({ provider, apiKey: provider === 'groq_auto' ? '' : apiKey, localUrl, localModel, groqModel })
    onClose()
  }

  const vramWarning = provider === 'local' ? getVramWarning(localModel) : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      <div className="bg-white dark:bg-surface text-ink-900 dark:text-plume border border-ink-200 dark:border-ink-700 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-200 dark:border-ink-700 bg-slate-50/50 dark:bg-obsidienne flex justify-between items-center">
          <h2 id="settings-title" className="text-lg font-bold text-slate-900 dark:text-plume">⚙️ Réglages IA</h2>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-700 dark:text-ink-400 dark:hover:text-plume transition-colors" aria-label="Fermer">
            ✕
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="flex gap-4">
            <button
              onClick={() => setProvider('groq_auto')}
              className={`flex-1 py-2 px-2 rounded-md border font-medium text-sm transition-colors ${
                provider === 'groq_auto' 
                  ? 'bg-slate-100 border-slate-500 text-slate-900 dark:bg-slate-900/50 dark:border-slate-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              ☁️ Groq (Démo non-souveraine)
            </button>
            <button
              onClick={() => { setProvider('groq'); setPingStatus(null); }}
              className={`flex-1 py-2 px-2 rounded-md border font-medium text-sm transition-colors ${
                provider === 'groq' 
                  ? 'bg-slate-100 border-slate-500 text-slate-900 dark:bg-slate-900/50 dark:border-slate-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              🔑 Clé API (Personnalisée)
            </button>
            <button
              onClick={() => { setProvider('local'); setPingStatus(null); }}
              className={`flex-1 py-2 px-2 rounded-md border font-medium text-sm transition-colors ${
                provider === 'local'
                  ? 'bg-slate-100 border-slate-500 text-slate-900 dark:bg-slate-900/50 dark:border-slate-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              💻 IA Locale (Souveraine)
            </button>
          </div>

          {provider === 'groq_auto' && (
            <div className="space-y-4">
              <div className="flex items-start gap-2 bg-slate-50/50 dark:bg-obsidienne/50 p-4 rounded-md border border-slate-200 dark:border-slate-800/50">
                <span className="text-lg">🔒</span>
                <p className="text-sm text-slate-800 dark:text-plume/80 leading-relaxed">
                  <strong>Mode Automatique :</strong> L'application utilise sa propre clé API pré-configurée. Vous n'avez rien à paramétrer !<br/><br/>
                  <span className="text-xs">Vos requêtes sont sécurisées. Aucune donnée n'est stockée sur nos serveurs.</span>
                </p>
              </div>
              
              <div className="flex items-start gap-2 bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-md border border-yellow-200 dark:border-yellow-800/50">
                <span className="text-lg">⚠️</span>
                <p className="text-sm text-yellow-800 dark:text-yellow-200 leading-relaxed">
                  <strong>Attention :</strong> En cas de forte affluence, cette API partagée peut atteindre ses limites de requêtes (rate-limit) et échouer. Pour une fiabilité garantie, utilisez votre propre Clé API ou l'IA Locale.
                </p>
              </div>
            </div>
          )}

          {provider === 'groq' && (
            <div className="space-y-4">
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                  Clé API Personnelle
                </label>
                <input 
                  type="password"
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  placeholder="gsk_..."
                  className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none"
                />
                
                {pingStatus && provider === 'groq' && (
                  <div className={`p-3 mt-2 rounded-md text-sm font-medium ${pingStatus.type === 'success' ? 'bg-green-100 text-green-800 border border-green-300' : pingStatus.type === 'error' ? 'bg-red-100 text-red-800 border border-red-300' : 'bg-blue-100 text-blue-800 border border-blue-300'}`}>
                    {pingStatus.message}
                  </div>
                )}
                
                <p className="text-xs text-ink-700 dark:text-ink-300 mt-2">
                  Si les quotas sont atteints, vous pouvez utiliser la vôtre (Groq ou compatible).
                </p>
                
                {provider === 'groq' && modelsList.length > 0 && (
                  <div className="mt-4 space-y-3">
                    <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                      Modèle
                    </label>
                    <select
                      value={groqModel}
                      onChange={e => setGroqModel(e.target.value)}
                      className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none"
                    >
                      {modelsList.map(m => (
                        <option key={m.id} value={m.id}>{m.id}</option>
                      ))}
                    </select>
                  </div>
                )}
                {provider === 'groq' && isFetchingModels && <p className="text-xs text-ink-500">Chargement des modèles...</p>}
              </div>
              <div className="flex items-start gap-2 bg-slate-50/50 dark:bg-obsidienne/50 p-3 rounded-md border border-slate-100 dark:border-slate-800/50">
                <span className="text-sm">🔒</span>
                <p className="text-xs text-slate-800 dark:text-plume/80 leading-relaxed">
                  <strong>Sécurité :</strong> Votre clé est uniquement sauvegardée localement sur votre navigateur. Elle n'est jamais stockée sur nos serveurs.
                </p>
              </div>
            </div>
          )}
          
          {provider === 'local' && (
            <div className="space-y-5">
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                  Endpoint API Locale
                </label>
                <input 
                  type="text"
                  value={localUrl}
                  onChange={e => setLocalUrl(e.target.value)}
                  placeholder="http://localhost:1234/v1"
                  className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none"
                />
                <div className="text-xs text-neutral-600 dark:text-neutral-400 mt-3 bg-neutral-100 dark:bg-neutral-800/50 p-3 rounded-md space-y-2 border border-neutral-200 dark:border-neutral-700/50">
                  <p>💡 <strong>Navigateur recommandé :</strong> Google Chrome ou Edge (basés sur Chromium).</p>
                  <p className="text-amber-700 dark:text-amber-400/90">⚠️ <strong>Attention Sécurité (CORS) :</strong> Votre adresse locale DOIT obligatoirement commencer par <strong>https://</strong> (utilisez un tunnel sécurisé comme Ngrok pour convertir votre port local http://127.0.0.1:1234).</p>
                </div>
                
                {provider === 'local' && (modelsList.length > 0 || isFetchingModels) && (
                  <div className="mt-4 space-y-3">
                    <label className="block text-sm font-medium text-slate-800 dark:text-plume">
                      Modèle IA
                    </label>
                    {isFetchingModels ? (
                      <p className="text-xs text-ink-500">Recherche des modèles sur l'hôte local...</p>
                    ) : (
                      <>
                        <select
                          value={localModel}
                          onChange={e => setLocalModel(e.target.value)}
                          className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent text-ink-900 dark:text-plume focus:ring-2 focus:ring-slate-500 focus:border-slate-500 transition-all outline-none"
                        >
                          {modelsList.map(m => (
                            <option key={m.id} value={m.id}>{m.id}</option>
                          ))}
                        </select>
                        {vramWarning && (
                          <div className={`p-2 mt-2 rounded-md border text-xs flex gap-2 items-start ${vramWarning.colorClass}`}>
                            <span>{vramWarning.icon}</span>
                            <span>{vramWarning.text}</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>

              {pingStatus && provider === 'local' && (
                <div className={`p-3 rounded-md text-sm font-medium ${pingStatus.type === 'success' ? 'bg-green-100 text-green-800 border border-green-300' : pingStatus.type === 'error' ? 'bg-red-100 text-red-800 border border-red-300' : 'bg-blue-100 text-blue-800 border border-blue-300'}`}>
                  {pingStatus.message}
                </div>
              )}
              
              <div className="bg-slate-50 dark:bg-obsidienne rounded-lg p-5 border border-slate-200 dark:border-slate-800 shadow-inner">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-plume mb-3">Tutoriel IA Locale</h3>
                <ol className="text-sm text-ink-700 dark:text-ink-300 space-y-2 list-decimal list-inside">
                  <li>Installer <strong>LM Studio</strong>, <strong>Ollama</strong> ou <strong>VLM</strong>.</li>
                  <li>Télécharger un modèle d'IA local (ex: Mistral ou Llama 3).</li>
                  <li><strong>ACTIVER IMPÉRATIVEMENT LE CORS</strong> (Cross-Origin Resource Sharing) dans les paramètres du serveur local.</li>
                  <li>Démarrer le serveur local de l'application.</li>
                  <li>Copier-coller l'adresse IP (ex: <code className="bg-ink-100 dark:bg-ink-800 px-1 py-0.5 rounded text-xs">http://localhost:1234/v1</code>) ci-dessus.</li>
                  <li><strong>⚡ Vitesse & Précision :</strong> Pour un classement optimal en 15s, privilégiez un modèle Instruct (Llama 3.1 8B / Mistral 7B). Si vous utilisez Gemma 4, conservez 'Enable Thinking' activé avec une Température de 0.2.</li>
                </ol>
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
