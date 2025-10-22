// src/components/CSVLoader.tsx
import React, { useRef, useState } from 'react';
import { csvFromUrl, uploadCSV } from '../api';

type Props = {
  onLoaded: (datasetId: number, preview: any) => void;
};

export default function CSVLoader({ onLoaded }: Props) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const res = await uploadCSV(file);
      onLoaded(res.dataset_id, res.preview);
      if (fileRef.current) fileRef.current.value = '';
    } catch (e: any) {
      alert(e.message || 'CSV upload failed');
    } finally { setBusy(false); }
  }

  async function onFetchUrl() {
    if (!url.trim()) return;
    setBusy(true);
    try {
      const res = await csvFromUrl(url.trim());
      onLoaded(res.dataset_id, res.preview);
      setUrl('');
    } catch (e: any) {
      alert(e.message || 'CSV fetch failed');
    } finally { setBusy(false); }
  }

  return (
    <div style={{ border: '1px dashed #bbb', borderRadius: 10, padding: 12, marginTop: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>CSV Data</div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={onUpload} />
        <span>or URL:</span>
        <input
          style={{ minWidth: 320 }}
          placeholder="https://raw.githubusercontent.com/.../file.csv"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button disabled={busy || !url.trim()} onClick={onFetchUrl}>
          {busy ? 'Loading…' : 'Load CSV'}
        </button>
      </div>
    </div>
  );
}
