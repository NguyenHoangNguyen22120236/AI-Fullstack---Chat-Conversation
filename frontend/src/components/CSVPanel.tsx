// src/components/CSVPanel.tsx
import React, { useState } from 'react';
import { csvSummary, csvStats, csvMissing, csvHistogram } from '../api';
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis, ResponsiveContainer } from 'recharts';

type Props = { datasetId: number | null };

export default function CSVPanel({ datasetId }: Props) {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<any | null>(null);
  const [stats, setStats] = useState<any | null>(null);
  const [missing, setMissing] = useState<{ column: string; missing: number } | null>(null);
  const [histCol, setHistCol] = useState('');
  const [hist, setHist] = useState<{ counts: number[]; edges: number[] } | null>(null);
  const disabled = !datasetId || loading;

  async function onSummary() {
    if (!datasetId) return;
    setLoading(true);
    try {
      const res = await csvSummary(datasetId);
      setSummary(res);
      setStats(null); setMissing(null); setHist(null);
    } finally { setLoading(false); }
  }
  async function onStats() {
    if (!datasetId) return;
    setLoading(true);
    try {
      const res = await csvStats(datasetId);
      setStats(res);
      setSummary(null); setMissing(null); setHist(null);
    } finally { setLoading(false); }
  }
  async function onMissing() {
    if (!datasetId) return;
    setLoading(true);
    try {
      const res = await csvMissing(datasetId);
      setMissing(res);
      setSummary(null); setStats(null); setHist(null);
    } finally { setLoading(false); }
  }
  async function onHist() {
    if (!datasetId || !histCol.trim()) return;
    setLoading(true);
    try {
      const res = await csvHistogram(datasetId, histCol.trim(), 20);
      setHist(res);
      setSummary(null); setStats(null); setMissing(null);
    } finally { setLoading(false); }
  }

  const histData =
    hist?.counts?.map((c, i) => {
      const left = hist?.edges?.[i];
      const right = hist?.edges?.[i + 1];
      return { bin: `${left?.toFixed?.(2)}–${right?.toFixed?.(2)}`, count: c };
    }) ?? [];

  return (
    <div style={{ border: '1px solid #eee', borderRadius: 10, padding: 12, marginTop: 12 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <button disabled={disabled} onClick={onSummary}>Summary</button>
        <button disabled={disabled} onClick={onStats}>Stats (numeric)</button>
        <button disabled={disabled} onClick={onMissing}>Most Missing</button>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            placeholder="histogram column (e.g. price)"
            value={histCol}
            onChange={(e) => setHistCol(e.target.value)}
          />
          <button disabled={!datasetId || loading || !histCol.trim()} onClick={onHist}>Histogram</button>
        </div>
        {loading && <span>Loading…</span>}
      </div>

      {/* Summary */}
      {summary && (
        <div style={{ marginTop: 10 }}>
          <h4>Dataset Summary</h4>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(summary, null, 2)}</pre>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div style={{ marginTop: 10 }}>
          <h4>Basic Stats (numeric)</h4>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(stats, null, 2)}</pre>
        </div>
      )}

      {/* Missing */}
      {missing && (
        <div style={{ marginTop: 10 }}>
          <h4>Most Missing</h4>
          <div>
            Column <b>{missing.column}</b> has <b>{missing.missing}</b> missing values.
          </div>
        </div>
      )}

      {/* Histogram */}
      {hist && (
        <div style={{ marginTop: 10 }}>
          <h4>Histogram: {histCol}</h4>
          {histData.length === 0 ? (
            <div>No data</div>
          ) : (
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={histData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bin" interval={Math.max(0, Math.floor(histData.length / 8))} angle={-20} textAnchor="end" height={60}/>
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
