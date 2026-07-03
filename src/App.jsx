import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

// Styles globaux pour le Markdown
const markdownStyles = `
  .markdown-body ul { list-style-type: disc; padding-left: 1.5rem; margin: 0.5rem 0; }
  .markdown-body ol { list-style-type: decimal; padding-left: 1.5rem; margin: 0.5rem 0; }
  .markdown-body li { margin-bottom: 0.25rem; }
  .markdown-body strong { font-weight: bold; color: #fff; }
  .markdown-body p { margin-bottom: 0.75rem; }
`;

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Bonjour ! Je suis Bourbon.IA, votre assistant législatif 100% local. Prêt à mouliner de l\'amendement (sans jamais envoyer vos données à OpenAI). Que souhaitez-vous analyser ?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
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

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    setSelectedFiles(prev => [...prev, ...files]);

    for (const file of files) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        setAttachedContent(prev => prev + `\n\n--- Fichier : ${file.name} ---\n${evt.target.result}`);
      };
      reader.readAsText(file);
    }
  };

  const removeAttachment = () => {
    setSelectedFiles([]);
    setAttachedContent('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const envoyerMessage = async () => {
    const messageTexte = input.trim();
    if (!messageTexte && !attachedContent) return;

    // Ajouter le message utilisateur à l'historique
    const userMessage = {
      role: 'user',
      content: messageTexte || '(Documents joints pour analyse)',
      attachment: selectedFiles.length > 0 ? selectedFiles.map(f => f.name).join(', ') : null,
    };
    // Ajouter une bulle vide pour l'assistant
    setMessages(prev => [...prev, userMessage, { role: 'assistant', content: '' }]);
    setInput('');
    setLoading(true); // Ce loading affichera "Recherche et rédaction en cours..."

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

      // Lecture du flux SSE
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let fullContent = "";

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '').trim();
              if (dataStr === '[DONE]') {
                done = true;
                break;
              }
              try {
                const dataObj = JSON.parse(dataStr);
                fullContent += dataObj.content;
                
                // Dès qu'on a du contenu, on peut cacher le loading state global
                if (fullContent.length > 0) setLoading(false);

                // Mettre à jour le dernier message (copie propre pour React)
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastIndex = newMessages.length - 1;
                  newMessages[lastIndex] = { ...newMessages[lastIndex], content: fullContent };
                  return newMessages;
                });
              } catch (e) {}
            }
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => {
          const newMsg = [...prev];
          newMsg[newMsg.length - 1].content += '\n\n🛑 Analyse interrompue.';
          return newMsg;
        });
      } else {
        setMessages(prev => {
          const newMsg = [...prev];
          newMsg[newMsg.length - 1].content = `❌ Erreur : ${err.message}. Vérifiez que le serveur FastAPI et LM Studio sont actifs.`;
          return newMsg;
        });
      }
    } finally {
      setLoading(false);
      removeAttachment();
      abortControllerRef.current = null;
    }
  };

  const renderAssistantMessage = (text) => {
    if (!text.includes('<think>')) return <div className="markdown-body"><ReactMarkdown>{text}</ReactMarkdown></div>;
    const parts = text.split('<think>');
    const beforeThink = parts[0];
    const rest = parts[1];
    
    if (rest.includes('</think>')) {
      const [thinkContent, afterThink] = rest.split('</think>');
      return (
        <div className="markdown-body">
          <ReactMarkdown>{beforeThink}</ReactMarkdown>
          <div style={S.thinkBlock}>{thinkContent}</div>
          <ReactMarkdown>{afterThink}</ReactMarkdown>
        </div>
      );
    } else {
      return (
        <div className="markdown-body">
          <ReactMarkdown>{beforeThink}</ReactMarkdown>
          <div style={S.thinkBlock}>{rest}</div>
        </div>
      );
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
    typingDot: (delay) => ({ width: '6px', height: '6px', backgroundColor: '#a1a1aa', borderRadius: '50%', animation: 'pulse 1.4s infinite ease-in-out both', animationDelay: `${delay}s` }),
    thinkBlock: {
      color: '#a1a1aa',
      fontStyle: 'italic',
      borderLeft: '3px solid #3f3f46',
      paddingLeft: '12px',
      margin: '12px 0',
      fontSize: '0.9em',
      whiteSpace: 'pre-wrap',
      backgroundColor: '#18181b',
      padding: '8px 12px',
      borderRadius: '4px'
    },
    spinner: {
      width: '12px',
      height: '12px',
      border: '2px solid #52525b',
      borderTopColor: '#a1a1aa',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite'
    },

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
      <style>{markdownStyles}</style>
      
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
                {msg.role === 'assistant' ? renderAssistantMessage(msg.content) : <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>}
              </div>
            </div>
          ))}

          {/* Indicateur de frappe */}
          {loading && (
            <div style={S.typingRow}>
              <span style={{ fontSize: '0.85em', color: '#a1a1aa' }}>Recherche en cours...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Fichiers joints preview */}
        {selectedFiles.length > 0 && (
          <div style={S.attachmentPreview}>
            <span>📎</span>
            <span style={S.attachmentName}>
              {selectedFiles.map(f => f.name).join(', ')} ({selectedFiles.length} fichier{selectedFiles.length > 1 ? 's' : ''})
            </span>
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
              multiple
              style={{ display: 'none' }}
              onChange={handleFileSelect}
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
                <option value="mac_qwen">🧠 Qwen 3.5 9B : Précis pour l'extraction de données.</option>
                <option value="mac_gemma">💎 Gemma 4 E2B : Modèle léger et instantané.</option>
              </optgroup>
              <optgroup label="🚀 Réseau Privé (PC Gamer - Deep Research)">
                <option value="pc_mistral_7b">⚡ Mistral 7B Instruct : Idéal pour les résumés rapides.</option>
                <option value="pc_mistral_14b">💡 Ministral 14B Reasoning : Raisonnement et logique avancée.</option>
                <option value="pc_gemma_12b">💎 Gemma 4 12B : Équilibre et précision.</option>
                <option value="pc_qwen_35b">👑 Qwen 3.6 35B : Expertise absolue (⭐ RECOMMANDÉ).</option>
                <option value="pc_qwq_32b">🧐 QwQ 32B : Recherche ultra-approfondie.</option>
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
