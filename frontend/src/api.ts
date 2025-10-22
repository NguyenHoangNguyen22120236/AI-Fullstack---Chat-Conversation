// src/api.ts
export const API = import.meta.env.VITE_API_BASE as string;

function jsonFetch<T>(input: RequestInfo, init?: RequestInit) {
  return fetch(input, init).then(async (r) => {
    if (!r.ok) throw new Error(await r.text());
    return r.json() as Promise<T>;
  });
}

export type HistoryItem = {
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  attachment_type?: 'image' | 'csv' | null;
  attachment_ref?: string | null;
};

export async function createSession(title = 'New Chat') {
  return jsonFetch<{ session_id: number }>(`${API}/chat/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
}

export async function getHistory(session_id: number) {
  const u = new URL(`${API}/chat/history`);
  u.searchParams.set('session_id', String(session_id));
  return jsonFetch<HistoryItem[]>(u.toString());
}

export async function sendChat(session_id: number, user_text: string) {
  const u = new URL(`${API}/chat/send`);
  u.searchParams.set('session_id', String(session_id));
  u.searchParams.set('user_text', user_text);
  return jsonFetch<{ reply: string }>(u.toString(), { method: 'POST' });
}

export async function uploadImage(session_id: number, file: File) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('session_id', String(session_id));
  return jsonFetch<{ image_path: string }>(`${API}/image/upload`, {
    method: 'POST',
    body: fd,
  });
}

export async function askImage(session_id: number, image_path: string, question: string) {
  const u = new URL(`${API}/image/ask`);
  u.searchParams.set('session_id', String(session_id));
  u.searchParams.set('image_path', image_path);
  u.searchParams.set('question', question);
  return jsonFetch<{ answer: string }>(u.toString(), { method: 'POST' });
}

export async function uploadCSV(file: File) {
  const fd = new FormData();
  fd.append('file', file);
  return jsonFetch<{ dataset_id: number; preview: any }>(`${API}/csv/upload`, {
    method: 'POST',
    body: fd,
  });
}

export async function csvFromUrl(url: string) {
  return jsonFetch<{ dataset_id: number; preview: any }>(`${API}/csv/from-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
}

export const csvSummary   = (id: number) => jsonFetch<any>(`${API}/csv/${id}/summary`);
export const csvStats     = (id: number) => jsonFetch<any>(`${API}/csv/${id}/stats`);
export const csvMissing   = (id: number) => jsonFetch<{ column: string; missing: number }>(`${API}/csv/${id}/missing`);
export const csvHistogram = (id: number, column: string, bins = 20) =>
  jsonFetch<{ counts: number[]; edges: number[] }>(`${API}/csv/${id}/histogram?column=${encodeURIComponent(column)}&bins=${bins}`);

export function resolveAttachmentUrl(p?: string | null) {
  if (!p) return '';
  // Assumes backend serves /uploads/** statically from the same base
  // Example: app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
  if (p.startsWith('uploads/')) return `${API}/${p}`;
  return `${API}/${p.replace(/^\//, '')}`;
}
