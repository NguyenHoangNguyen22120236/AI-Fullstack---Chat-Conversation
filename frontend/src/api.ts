export type ToolOutputs = {
  image_path?: string;
  csv_rows?: number;
  csv_cols?: number;
  basic_stats?: Record<string, unknown>;
  missing_values?: Record<string, number>;
  histogram_image?: string;
};

export type AttachmentKind = 'image' | 'csv' | 'plot';

export type Attachment = {
  id: number;
  kind: AttachmentKind;
  path: string;
  original_name?: string | null;
  mime?: string | null;
  public_url?: string | null;
};

export type ChatMessage = {
  id?: number; // when loaded from DB
  role: 'user' | 'assistant';
  content: string;
  ts?: number;
  created_at?: string;
  attachments?: Attachment[]; // when loaded via /sessions/{id}/messages
};

export type AttachmentInfo = {
  id: number;
  kind: AttachmentKind;
  path: string;
  original_name?: string | null;
  mime?: string | null;
  public_url?: string | null;
};

export type ChatResponse = {
  session_id: string;
  assistant_message: string;
  tool_outputs: ToolOutputs;
  message_id: number;

  user_message?: {
    id: number;
    attachments: AttachmentInfo[];
  };

  assistant_message_meta?: {
    id: number;
    attachments: AttachmentInfo[];
  };
};

export type SessionSummary = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  last_message: string;
  message_count: number;
};

export type SessionListResponse = { sessions: SessionSummary[]; offset: number; limit: number };

export type SessionMessagesResponse = {
  session: { id: string; title: string | null; created_at: string; updated_at: string };
  messages: Array<{
    id: number;
    role: 'user' | 'assistant';
    content: string;
    tool_outputs?: ToolOutputs;
    created_at: string;
    attachments: Attachment[];
  }>;
};

const API_BASE = import.meta.env.VITE_API_BASE as string;

export async function postChat(
  payload: { session_id: string; message: string; file?: File | null; csv_url?: string | null }
): Promise<ChatResponse> {
  const fd = new FormData();
  fd.append('session_id', payload.session_id);
  fd.append('message', payload.message);
  if (payload.file) fd.append('file', payload.file);
  if (payload.csv_url) fd.append('csv_url', payload.csv_url);

  const res = await fetch(`${API_BASE}/chat`, { method: 'POST', body: fd });

  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      msg = (data?.detail as string) ?? JSON.stringify(data);
    } catch {
      msg = await res.text();
    }
    throw new Error(msg || `Request failed (${res.status})`);
  }
  return res.json();
}


export async function fetchSessions(limit = 50, offset = 0): Promise<SessionListResponse> {
  const res = await fetch(`${API_BASE}/sessions?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Fetch sessions failed (${res.status})`);
  return res.json();
}

export async function fetchSessionMessages(session_id: string): Promise<SessionMessagesResponse> {
  const res = await fetch(`${API_BASE}/sessions/${session_id}/messages`);
  if (!res.ok) throw new Error(`Fetch messages failed (${res.status})`);
  return res.json();
}