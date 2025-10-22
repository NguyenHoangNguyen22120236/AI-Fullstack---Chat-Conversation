import { useEffect, useMemo, useRef, useState } from 'react';
import { postChat, type ChatMessage, type ToolOutputs, fetchSessions, fetchSessionMessages, type SessionSummary } from './api';
import { MessageBubble } from './components/MessageBubble';
import './styles/app.scss';
import { ErrorBanner } from './components/ErrorBanner';

function randomSession() {
  return Math.random().toString(36).slice(2, 10);
}


const MAX_FILE_MB = 20; // tune this
const ALLOWED_EXT = ['.png', '.jpg', '.jpeg', '.csv'];



function isValidCsvUrl(u: string) {
  try {
    const url = new URL(u);
    return /\.csv(\?|#|$)/i.test(url.pathname);
  } catch {
    return false;
  }
}

export default function App() {
  const [sessionId, setSessionId] = useState<string>(() => randomSession());
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolForLastAssistant, setToolForLastAssistant] = useState<ToolOutputs | undefined>();

  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null); // image OR csv
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [csvUrl, setCsvUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const canSend = useMemo(() => input.trim().length > 0 || file || csvUrl.trim().length > 0, [input, file, csvUrl]);

  const [error, setError] = useState<string>('');

  function showError(msg: string) {
    setError(msg);
    setTimeout(() => setError(''), 6000);
  }

  // load sessions for sidebar
  async function refreshSessions() {
    const res = await fetchSessions();
    setSessions(res.sessions);
  }

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // load messages when selecting sessionId (if it already exists in DB)
  async function loadSessionMessages(id: string) {
    try {
      const res = await fetchSessionMessages(id);
      const msgs: ChatMessage[] = res.messages.map(m => ({
        id: m.id, role: m.role, content: m.content, created_at: m.created_at, attachments: m.attachments
      }));
      setMessages(msgs);
      setToolForLastAssistant(undefined);
    } catch {
      setMessages([]); // local new session (no messages yet)
    }
  }

  useEffect(() => { refreshSessions(); }, []);
  useEffect(() => { loadSessionMessages(sessionId); }, [sessionId]);

  async function handleSend() {
    if (!canSend || loading) return;
    if (csvUrl && !isValidCsvUrl(csvUrl)) {
      showError('CSV URL looks invalid. Please paste a link that ends with .csv (e.g., a raw GitHub CSV).');
      return;
    }

    const userMsg: ChatMessage = { role: 'user', content: input || (file ? `[Attached: ${file.name}]` : csvUrl), ts: Date.now() };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await postChat({ session_id: sessionId, message: userMsg.content, file, csv_url: csvUrl || null });

      const assistantMsg: ChatMessage = { role: 'assistant', content: res.assistant_message, ts: Date.now() };
      setMessages((m) => {
        const next = [...m, assistantMsg];

        // gắn attachments cho user vừa gửi
        if (res.user_message?.attachments?.length) {
          const idxUser = next.length - 2; // phần tử trước assistant
          next[idxUser] = {
            ...next[idxUser],
            attachments: res.user_message.attachments,
          };
        }

        // gắn attachments cho assistant
        if (res.assistant_message_meta?.attachments?.length) {
          const idxAsst = next.length - 1;
          next[idxAsst] = {
            ...next[idxAsst],
            attachments: res.assistant_message_meta.attachments,
          };
        }
        return next;
      });

      setToolForLastAssistant(res.tool_outputs);
      refreshSessions();
    } catch (e: any) {
      showError(e?.message || 'Unexpected error.');
      setMessages((m) => [...m, { role: 'assistant', content: `❌ ${e.message}`, ts: Date.now() }]);
      setToolForLastAssistant(undefined);
    } finally {
      setLoading(false);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  function onPickFile(f: File | null) {
    if (!f) {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      return setFile(null);
    }
    const name = f.name.toLowerCase();
    const ext = ALLOWED_EXT.find(e => name.endsWith(e));
    const isImage = name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg');
    const isCsv = name.endsWith('.csv');

    if (!ext) {
      showError('Only .csv, .jpg, .jpeg, .png files are allowed.');
      return;
    }
    const sizeMb = f.size / (1024 * 1024);
    if (sizeMb > MAX_FILE_MB) {
      showError(`File is too large (${sizeMb.toFixed(1)} MB). Max allowed is ${MAX_FILE_MB} MB.`);
      return;
    }

    if (!(isImage || isCsv)) {
      alert('Only PNG/JPG/CSV are supported.');
      return;
    }

    // revoke old preview
    if (previewUrl) URL.revokeObjectURL(previewUrl);

    if (isImage) {
      const url = URL.createObjectURL(f);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
    setFile(f);
  }

  return (
    <div>
      <header className="chat-header">
        <div className="chat-container" style={{paddingTop: '12px', paddingBottom: '12px', display: 'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div className="title">AI Chat — single /chat endpoint</div>
          <div className="session">Session: {sessionId}</div>
        </div>
      </header>

      <div style={{paddingTop: '10px'}}>
        <ErrorBanner text={error} onClose={() => setError('')} />
      </div>

      <div className="chat-container" style={{display:'grid', gridTemplateColumns:'260px 1fr', gap:'16px'}}>
        <aside className="sidebar">
          <div className="sidebar__head">
            <div className="title">Conversations</div>
            <div className="actions">
              <button
                className="btn btn--primary"
                onClick={() => { const id = randomSession(); setSessionId(id); setMessages([]); setToolForLastAssistant(undefined); }}
              >
                + New
              </button>
            </div>
          </div>

          <ul className="conv-list">
            {sessions.length === 0 && (
              <li style={{color:'#6b7280', fontSize:12, padding:'6px 2px'}}>No conversations yet.</li>
            )}
            {sessions.map(s => (
              <li key={s.id}>
                <button
                  className={`conv-item ${s.id === sessionId ? 'is-active' : ''}`}
                  onClick={() => setSessionId(s.id)}
                  title={s.id}
                >
                  <div className="conv-title">{s.title || 'Untitled session'}</div>
                  <div className="conv-meta">
                    <span className="badge">{s.message_count}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <main>
          <div className="messages">
            {messages.length === 0 && (
              <div style={{textAlign:'center', color:'#6b7280', margin:'4rem 0'}}>
                Ask me anything. Attach an <b>image</b> or a <b>CSV</b>, or paste a <b>CSV URL</b>.
              </div>
            )}
            {messages.map((m, idx) => (
              <div key={m.id ?? idx}>
                <MessageBubble m={m} tool={idx === messages.length - 1 ? toolForLastAssistant : undefined} />
                {/* attachments preview */}
                {m.attachments && m.attachments.length > 0 && (
                  <div className="ml-4 mt-1 mb-3 text-xs text-gray-600">
                    {m.attachments.map(att => (
                      <div key={att.id} className="mb-1">
                        {att.kind !== 'csv' && att.public_url ? (
                          <img src={`${import.meta.env.VITE_API_BASE}${att.public_url}`} alt={att.original_name || att.kind} style={{maxWidth:'360px', borderRadius:8, border:'1px solid #e5e7eb'}} />
                        ) : (
                          <a href={`${import.meta.env.VITE_API_BASE}${att.public_url}`} target="_blank" rel="noreferrer" className="underline">{att.original_name || att.path}</a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </main>
      </div>

      {/* INPUT BAR */}
      <div className="input-bar">
        <div className="inner">
          <div className="row">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }}}
              placeholder="Type your message…"
              className="text-input"
            />
            <button
              onClick={handleSend}
              disabled={!canSend || loading}
              className={`send-btn ${!canSend || loading ? 'disabled' : ''}`}
            >
              {loading ? 'Sending…' : 'Send'}
            </button>
          </div>

          <div className="attachments">
            <div className="file-upload">
              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,.csv"
                onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
              />
              <span className="note">Only .csv, .jpg, .jpeg, .png files are allowed. Max {MAX_FILE_MB} MB.</span>
            </div>

            <div className="flex items-center gap-2">
              <span style={{ color: '#6b7280' }}>CSV URL:</span>
              <input
                value={csvUrl}
                onChange={(e) => setCsvUrl(e.target.value)}
                placeholder="https://raw.githubusercontent.com/.../data.csv"
                className="csv-url"
              />
            </div>

            {file && (
              <div className="preview">
                {previewUrl ? (
                  <>
                    <img src={previewUrl} alt="preview" className="preview__img" />
                    <span className="preview__name">{file.name}</span>
                    <button
                      type="button"
                      className="preview__remove"
                      onClick={() => {
                        if (previewUrl) URL.revokeObjectURL(previewUrl);
                        setPreviewUrl(null);
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                      aria-label="Remove attachment"
                      title="Remove attachment"
                    >
                      ×
                    </button>
                  </>
                ) : (
                  <>
                    <span className="file-badge">{file.name}</span>
                    <button
                      type="button"
                      className="preview__remove"
                      onClick={() => {
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                      aria-label="Remove attachment"
                      title="Remove attachment"
                    >
                      ×
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}