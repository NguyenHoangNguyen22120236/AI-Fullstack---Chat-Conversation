// src/components/ImageAsk.tsx
import React, { useRef, useState } from 'react';
import { askImage, uploadImage } from '../api';

type Props = {
  sessionId: number;
  onAnswer: (userQ: string, answer: string, imagePath: string) => void;
};

export default function ImageAsk({ sessionId, onAnswer }: Props) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState("What's in this photo?");
  const [busy, setBusy] = useState(false);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    setFile(f ?? null);
  }

  async function onSubmit() {
    if (!file) return;
    setBusy(true);
    try {
      const { image_path } = await uploadImage(sessionId, file);
      const { answer } = await askImage(sessionId, image_path, question);
      onAnswer(question, answer, image_path);
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
    } catch (e: any) {
      alert(e.message || 'Image ask failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ border: '1px dashed #bbb', borderRadius: 10, padding: 12, marginTop: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Image Q&A</div>
      <input ref={fileRef} type="file" accept="image/png,image/jpeg" onChange={onUpload} />
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <input style={{ flex: 1 }} value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button disabled={!file || busy} onClick={onSubmit}>{busy ? 'Asking…' : 'Ask'}</button>
      </div>
    </div>
  );
}
