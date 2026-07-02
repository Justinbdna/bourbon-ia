import { useState, useEffect, useRef } from 'react';

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Bienvenue sur Bourbon.IA, votre assistant législatif 100 % local.\n\nJe suis connecté aux sources MCP Tricoteuses et à l\'open data de l\'Assemblée nationale.\n\nVous pouvez me poser une question, coller un texte d\'amendement, ou joindre un fichier JSON pour une analyse approfondie.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [attachedContent, setAttachedContent] = useState('');
  const [selectedModel, setSelectedModel] = useState('pc_mistral_7b');

  // Initialiser la ref pour l'AbortController
  const abortControllerRef = useRef(null);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Scroll automatique vers le dernier message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Injecter les keyframes et le reset CSS
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      *, *::before, *::after { box-sizing: border-box; }
      body { margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
      @keyframes fadeSlideUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
      @keyframes pulse { 0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); } 40% { opacity: 1; transform: scale(1); } }
      textarea:focus { outline: none; }
    `;
    document.head.appendChild(style);
  }, []);

  const handleFileAttach = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAttachedFile(file);
    const reader = new FileReader();
    reader.onload = (evt) => {
      setAttachedContent(evt.target.result);
    };
    reader.readAsText(file);
  };

  const removeAttachment = () => {
    setAttachedFile(null);
    setAttachedContent('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const envoyerMessage = async () => {
    const messageTexte = input.trim();
    if (!messageTexte && !attachedContent) return;

    // Ajouter le message utilisateur à l'historique
    const userMessage = {
      role: 'user',
      content: messageTexte || '(Document joint pour analyse)',
      attachment: attachedFile?.name || null,
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    // Initialiser le contrôleur d'annulation
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortControllerRef.current.signal,
        body: JSON.stringify({
          message: messageTexte || 'Analyse ce document en profondeur.',
          context_text: attachedContent,
          model: selectedModel,
        }),
      });

      if (!response.ok) {
        throw new Error(`Erreur API : ${response.status}`);
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.content }]);
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => [...prev, { role: 'assistant', content: '🛑 Analyse interrompue.' }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: `❌ Erreur : ${err.message}. Vérifiez que le serveur FastAPI et LM Studio sont actifs.` }]);
      }
    } finally {
      setLoading(false);
      removeAttachment();
      abortControllerRef.current = null;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      envoyerMessage();
    }
  };

  // ─── STYLES ──────────────────────────────────────────
  const S = {
    app: { display: 'flex', height: '100vh', backgroundColor: '#0f0f11' },

    // Sidebar
    sidebar: { width: '260px', backgroundColor: '#18181b', borderRight: '1px solid #27272a', display: 'flex', flexDirection: 'column', padding: '1.5rem 1rem' },
    logo: { fontSize: '1.4rem', fontWeight: '700', color: '#f4f4f5', letterSpacing: '-0.03em', marginBottom: '2rem', padding: '0 0.5rem' },
    logoAccent: { color: '#60a5fa' },
    sideSection: { marginBottom: '1.5rem' },
    sideLabel: { fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#52525b', marginBottom: '0.6rem', padding: '0 0.5rem' },
    historyItem: { padding: '0.6rem 0.75rem', borderRadius: '8px', color: '#a1a1aa', fontSize: '0.85rem', cursor: 'pointer', marginBottom: '2px' },
    mcpBadge: { display: 'flex', alignItems: 'center', gap: '8px', padding: '0.5rem 0.75rem', borderRadius: '8px', backgroundColor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.15)', marginBottom: '6px' },
    mcpDot: { width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981', boxShadow: '0 0 6px #10b981', flexShrink: 0 },
    mcpText: { fontSize: '0.78rem', color: '#34d399' },
    sideFooter: { marginTop: 'auto', padding: '0.75rem', borderRadius: '8px', backgroundColor: '#27272a' },
    sideFooterText: { fontSize: '0.7rem', color: '#71717a', margin: 0 },

    // Main
    main: { flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: '#0f0f11' },
    header: { padding: '1rem 2rem', borderBottom: '1px solid #1c1c1f', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
    headerTitle: { color: '#e4e4e7', fontSize: '0.95rem', fontWeight: '500', margin: 0 },
    headerBadge: { backgroundColor: '#1e3a5f', color: '#60a5fa', padding: '4px 12px', borderRadius: '999px', fontSize: '0.7rem', fontWeight: '600' },

    // Messages
    messagesArea: { flex: 1, overflowY: 'auto', padding: '2rem 0' },
    messageRow: (isUser) => ({ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', padding: '0.4rem 2rem', animation: 'fadeSlideUp 0.3s ease-out' }),
    messageBubble: (isUser) => ({
      maxWidth: '680px',
      padding: '1rem 1.25rem',
      borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
      backgroundColor: isUser ? '#2563eb' : '#1c1c1f',
      color: isUser ? '#fff' : '#d4d4d8',
      fontSize: '0.92rem',
      lineHeight: '1.65',
      whiteSpace: 'pre-wrap',
      boxShadow: isUser ? '0 2px 8px rgba(37, 99, 235, 0.3)' : '0 1px 4px rgba(0,0,0,0.3)',
    }),
    attachTag: { display: 'inline-flex', alignItems: 'center', gap: '4px', backgroundColor: 'rgba(255,255,255,0.15)', padding: '3px 8px', borderRadius: '4px', fontSize: '0.75rem', marginBottom: '6px' },

    // Typing indicator
    typingRow: { display: 'flex', justifyContent: 'flex-start', padding: '0.4rem 2rem' },
    typingBubble: { display: 'flex', gap: '5px', alignItems: 'center', padding: '1rem 1.25rem', borderRadius: '18px 18px 18px 4px', backgroundColor: '#1c1c1f' },
    typingDot: (delay) => ({ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#60a5fa', animation: `pulse 1.4s ${delay}s infinite ease-in-out` }),

    // Model selector
    modelSelect: { backgroundColor: '#18181b', color: '#e4e4e7', border: '1px solid #27272a', borderRadius: '8px', padding: '6px 12px', fontSize: '0.82rem', outline: 'none', cursor: 'pointer', fontFamily: 'inherit' },
    modelDesc: { color: '#52525b', fontSize: '0.72rem', margin: 0 },

    // Input area
    inputArea: { padding: '1rem 2rem 0.5rem', borderTop: '1px solid #1c1c1f' },
    inputContainer: { display: 'flex', flexDirection: 'row', alignItems: 'center', gap: '12px', backgroundColor: '#18181b', borderRadius: '16px', padding: '0.75rem 1rem', border: '1px solid #27272a' },
    textarea: { flex: 1, background: 'none', border: 'none', color: '#e4e4e7', fontSize: '0.92rem', resize: 'none', lineHeight: '1.5', maxHeight: '120px', fontFamily: 'inherit' },
    attachBtn: { background: 'none', border: '1px solid #3f3f46', color: '#a1a1aa', padding: '8px 12px', borderRadius: '10px', cursor: 'pointer', fontSize: '0.85rem', whiteSpace: 'nowrap', transition: 'border-color 0.2s' },
    sendBtn: (active) => ({ background: active ? '#2563eb' : '#27272a', color: active ? '#fff' : '#52525b', border: 'none', padding: '8px 18px', borderRadius: '10px', cursor: active ? 'pointer' : 'default', fontWeight: '600', fontSize: '0.9rem', transition: 'background 0.2s' }),
    stopBtn: { background: '#ef4444', color: '#fff', border: 'none', padding: '8px 18px', borderRadius: '10px', cursor: 'pointer', fontWeight: '600', fontSize: '0.9rem', transition: 'background 0.2s' },
    attachmentPreview: { display: 'flex', alignItems: 'center', gap: '8px', padding: '0.5rem 1rem', margin: '0 2rem 0.5rem', backgroundColor: '#1c1c1f', borderRadius: '8px', border: '1px solid #27272a' },
    attachmentName: { flex: 1, color: '#a1a1aa', fontSize: '0.82rem' },
    attachmentRemove: { background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.85rem', padding: '2px 6px' },
  };

  return (
    <div style={S.app}>
      {/* ── SIDEBAR ── */}
      <div style={S.sidebar}>
        <div style={S.logo}>
          Bourbon<span style={S.logoAccent}>.IA</span>
        </div>

        <div style={S.sideSection}>
          <div style={S.sideLabel}>Historique</div>
          <div style={{...S.historyItem, backgroundColor: '#27272a', color: '#e4e4e7'}}>
            💬 Nouvelle conversation
          </div>
        </div>

        <div style={S.sideFooter}>
          <p style={S.sideFooterText}>
            ⚡ Analyse 100% locale<br/>
            Aucune donnée ne quitte votre réseau.
          </p>
        </div>
      </div>

      {/* ── MAIN ── */}
      <div style={S.main}>
        {/* Header */}
        <div style={S.header}>
          <h2 style={S.headerTitle}>Assistant Législatif — Deep Research</h2>
          <span style={S.headerBadge}>100% Local</span>
        </div>

        {/* Messages */}
        <div style={S.messagesArea}>
          {messages.map((msg, idx) => (
            <div key={idx} style={S.messageRow(msg.role === 'user')}>
              <div style={S.messageBubble(msg.role === 'user')}>
                {msg.attachment && (
                  <div style={S.attachTag}>📎 {msg.attachment}</div>
                )}
                {msg.content}
              </div>
            </div>
          ))}

          {/* Indicateur de frappe */}
          {loading && (
            <div style={S.typingRow}>
              <div style={S.typingBubble}>
                <div style={S.typingDot(0)}></div>
                <div style={S.typingDot(0.2)}></div>
                <div style={S.typingDot(0.4)}></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Fichier joint preview */}
        {attachedFile && (
          <div style={S.attachmentPreview}>
            <span>📎</span>
            <span style={S.attachmentName}>{attachedFile.name} ({(attachedFile.size / 1024).toFixed(1)} Ko)</span>
            <button style={S.attachmentRemove} onClick={removeAttachment}>✕</button>
          </div>
        )}

        {/* Zone de saisie */}
        <div style={S.inputArea}>
          <div style={S.inputContainer}>
            <input
              type="file"
              ref={fileInputRef}
              accept=".json,.txt,.pdf,.md"
              style={{ display: 'none' }}
              onChange={handleFileAttach}
            />
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={S.modelSelect}
              title="Choisir le modèle d'analyse"
            >
              <optgroup label="💻 100% Local (Mac - Rapide)">
                <option value="mac_mistral">⚡ Mistral 7B Instruct : Idéal pour les résumés rapides.</option>
                <option value="mac_llama">🦙 Llama 3 8B Instruct : Parfait pour le multitâche.</option>
                <option value="mac_qwen">🧠 Qwen 2.5 7B : Précis pour l'extraction de données.</option>
                <option value="mac_gemma">💎 Gemma 2 2B : Modèle léger et instantané.</option>
              </optgroup>
              <optgroup label="🚀 Réseau Privé (PC Gamer - Deep Research)">
                <option value="pc_mistral_7b">⚡ Mistral 7B Instruct : Idéal pour les résumés rapides.</option>
                <option value="pc_ministral_8b">💡 Ministral 8B Instruct : Raisonnement et logique avancée.</option>
                <option value="pc_gemma_9b">💎 Gemma 2 9B : Équilibre et précision.</option>
                <option value="pc_qwen_32b">👑 Qwen 2.5 32B : Expertise juridique absolue.</option>
                <option value="pc_qwq_32b">🧐 QwQ 32B : Recherche approfondie.</option>
              </optgroup>
            </select>

            <button
              style={S.attachBtn}
              onClick={() => fileInputRef.current?.click()}
              title="Joindre un fichier JSON, TXT ou PDF"
            >
              📎
            </button>
            <textarea
              rows={1}
              style={S.textarea}
              placeholder="Posez votre question sur un amendement, collez un texte juridique..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            {loading ? (
              <button style={S.stopBtn} onClick={handleStop}>
                🛑 Stop
              </button>
            ) : (
              <button
                style={S.sendBtn(input.trim() || attachedContent)}
                onClick={envoyerMessage}
                disabled={!input.trim() && !attachedContent}
              >
                Envoyer
              </button>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div style={S.disclaimer}>
          <p style={S.disclaimerText}>Bourbon.IA peut commettre des erreurs, y compris sur des faits juridiques. Veuillez vérifier les informations importantes.</p>
        </div>
      </div>
    </div>
  );
}

export default App;
