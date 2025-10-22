// src/App.tsx
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  createSession, getHistory, sendChat,
  type HistoryItem, resolveAttachmentUrl,
} from './api';
import MessageBubble from './components/MessageBubble';
import ImageAsk from './components/ImageAsk';
import CSVLoader from './components/CSVLoader';
import CSVPanel from './components/CSVPanel';

export default function App() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);

  // CSV state
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const [csvPreview, setCsvPreview] = useState<any | null>(null);

  const scrollerRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!scrollerRef.current) return;
    scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
  }, [history]);

  // bootstrap a session
  useEffect(() => {
    (async () => {
      const { session_id } = await createSession('My Chat');
      setSessionId(session_id);
      const h = await getHistory(session_id);
      setHistory(h);
    })();
  }, []);

  async function onSend() {
    if (!sessionId || !input.trim()) return;
    setBusy(true);
    try {
      setHistory((h) => [
        ...h,
        { role: 'user', content: input, created_at: new Date().toISOString() },
      ]);
      const { reply } = await sendChat(sessionId, input);
      setHistory((h) => [
        ...h,
        { role: 'assistant', content: reply, created_at: new Date().toISOString() },
      ]);
      setInput('');
    } catch (e: any) {
      alert(e.message || 'Send failed');
    } finally {
      setBusy(false);
    }
  }

  function onImageAnswered(q: string, ans: string, imagePath: string) {
    // show image-question pair in the chat immediately
    setHistory((h) => [
      ...h,
      {
        role: 'user',
        content: `[image question] ${q}`,
        created_at: new Date().toISOString(),
        attachment_type: 'image',
        attachment_ref: imagePath,
      },
      { role: 'assistant', content: ans, created_at: new Date().toISOString() },
    ]);
  }

  function onCSVLoaded(id: number, preview: any) {
    setDatasetId(id);
    setCsvPreview(preview);
  }

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: 16 }}>
      <h2>AI Chat (Multi-turn • Image • CSV)</h2>
      <div style={{ color: '#666', marginBottom: 8 }}>
        Session: <b>{sessionId ?? '...'}</b>
      </div>

      {/* Chat history */}
      <div
        ref={scrollerRef}
        style={{
          border: '1px solid #eee',
          borderRadius: 12,
          minHeight: 320,
          maxHeight: 520,
          overflowY: 'auto',
          padding: 12,
          background: '#fff',
        }}
      >
        {history.map((m, i) => (
          <MessageBubble key={i} {...m} />
        ))}
        {busy && (
          <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>Assistant is typing…</div>
        )}
      </div>

      {/* Input bar */}
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <input
          style={{ flex: 1 }}
          placeholder="Type a message and press Enter…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') onSend(); }}
        />
        <button disabled={!input.trim() || busy || !sessionId} onClick={onSend}>
          Send
        </button>
      </div>

      {/* Image ask */}
      {sessionId && <ImageAsk sessionId={sessionId} onAnswer={onImageAnswered} />}

      {/* CSV loader + actions */}
      <CSVLoader onLoaded={onCSVLoaded} />
      {datasetId && (
        <>
          <div style={{ marginTop: 8, color: '#333' }}>
            <b>Loaded Dataset:</b> #{datasetId}
          </div>
          {csvPreview && (
            <div style={{ marginTop: 6 }}>
              <details>
                <summary>Initial preview</summary>
                <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(csvPreview, null, 2)}</pre>
              </details>
            </div>
          )}
          <CSVPanel datasetId={datasetId} />
        </>
      )}
    </div>
  );
}
