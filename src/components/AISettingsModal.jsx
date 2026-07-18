import { useState, useEffect } from 'react'

export default function AISettingsModal({ isOpen, onClose, onSave, currentSettings }) {
  const [provider, setProvider] = useState(currentSettings?.provider || 'groq')
  const [apiKey, setApiKey] = useState(currentSettings?.apiKey || '')
  const [localUrl, setLocalUrl] = useState(currentSettings?.localUrl || 'http://localhost:1234/v1')

  useEffect(() => {
    if (isOpen) {
      setProvider(currentSettings?.provider || 'groq')
      setApiKey(currentSettings?.apiKey || '')
      setLocalUrl(currentSettings?.localUrl || 'http://localhost:1234/v1')
    }
  }, [isOpen, currentSettings])

  if (!isOpen) return null

  const handleSave = () => {
    onSave({ provider, apiKey, localUrl })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-surface border border-ink-200 dark:border-ink-700 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-ink-200 dark:border-ink-700 bg-marine-50/50 dark:bg-obsidienne flex justify-between items-center">
          <h2 className="text-lg font-bold text-marine-900 dark:text-plume">⚙️ Réglages IA</h2>
          <button onClick={onClose} className="text-ink-500 hover:text-ink-700 dark:text-ink-400 dark:hover:text-plume transition-colors">
            ✕
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="flex gap-4">
            <button
              onClick={() => setProvider('groq')}
              className={`flex-1 py-2 px-4 rounded-md border font-medium transition-colors ${
                provider === 'groq' 
                  ? 'bg-marine-100 border-marine-500 text-marine-900 dark:bg-marine-900/50 dark:border-marine-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              ☁️ API Cloud
            </button>
            <button
              onClick={() => setProvider('local')}
              className={`flex-1 py-2 px-4 rounded-md border font-medium transition-colors ${
                provider === 'local'
                  ? 'bg-marine-100 border-marine-500 text-marine-900 dark:bg-marine-900/50 dark:border-marine-400 dark:text-plume shadow-sm' 
                  : 'bg-transparent border-ink-300 text-ink-600 hover:bg-ink-50 dark:border-ink-600 dark:text-ink-300 dark:hover:bg-ink-800'
              }`}
            >
              💻 IA Locale
            </button>
          </div>

          {provider === 'groq' ? (
            <div className="space-y-4">
              <div className="space-y-3">
                <label className="block text-sm font-medium text-marine-800 dark:text-plume">
                  Clé API Cloud (Optionnelle pour la démo)
                </label>
                <input 
                  type="password"
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                  placeholder="gsk_..."
                  className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent dark:text-plume focus:ring-2 focus:ring-marine-500 focus:border-marine-500 transition-all outline-none"
                />
                <p className="text-xs text-ink-500 dark:text-ink-400">
                  Une clé API par défaut est gracieusement fournie pour cette démo. Si les quotas sont atteints, vous pouvez utiliser la vôtre (Groq ou compatible).
                </p>
              </div>
              <div className="flex items-start gap-2 bg-marine-50/50 dark:bg-obsidienne/50 p-3 rounded-md border border-marine-100 dark:border-marine-800/50">
                <span className="text-sm">🔒</span>
                <p className="text-xs text-marine-800 dark:text-plume/80 leading-relaxed">
                  <strong>Sécurité :</strong> Votre clé est uniquement sauvegardée localement sur votre navigateur. Elle n'est jamais stockée sur nos serveurs.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="space-y-3">
                <label className="block text-sm font-medium text-marine-800 dark:text-plume">
                  Endpoint API Locale
                </label>
                <input 
                  type="text"
                  value={localUrl}
                  onChange={e => setLocalUrl(e.target.value)}
                  placeholder="http://localhost:1234/v1"
                  className="w-full px-3 py-2 border border-ink-300 dark:border-ink-600 rounded-md bg-transparent dark:text-plume focus:ring-2 focus:ring-marine-500 focus:border-marine-500 transition-all outline-none"
                />
              </div>
              
              <div className="bg-marine-50 dark:bg-obsidienne rounded-lg p-5 border border-marine-200 dark:border-marine-800 shadow-inner">
                <h3 className="text-sm font-semibold text-marine-900 dark:text-plume mb-3">Tutoriel IA Locale</h3>
                <ol className="text-sm text-ink-600 dark:text-ink-300 space-y-2 list-decimal list-inside">
                  <li>Installer <strong>LM Studio</strong>, <strong>Ollama</strong> ou <strong>VLM</strong>.</li>
                  <li>Télécharger un modèle d'IA local (ex: Mistral ou Llama 3).</li>
                  <li>Démarrer le serveur local de l'application.</li>
                  <li>Copier-coller l'adresse IP (ex: <code className="bg-ink-100 dark:bg-ink-800 px-1 py-0.5 rounded text-xs">http://localhost:1234/v1</code>) ci-dessus.</li>
                </ol>
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-ink-200 dark:border-ink-700 bg-gray-50 dark:bg-surface flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-ink-600 dark:text-ink-300 hover:text-ink-900 dark:hover:text-plume transition-colors">
            Annuler
          </button>
          <button onClick={handleSave} className="px-4 py-2 bg-marine-600 hover:bg-marine-500 text-white text-sm font-medium rounded-md shadow-sm transition-colors">
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}
