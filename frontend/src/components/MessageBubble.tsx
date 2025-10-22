// src/components/MessageBubble.tsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import dayjs from 'dayjs';
import { resolveAttachmentUrl } from '../api';

type Props = {
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  attachment_type?: 'image' | 'csv' | null;
  attachment_ref?: string | null;
};

export default function MessageBubble({
  role,
  content,
  created_at,
  attachment_type,
  attachment_ref,
}: Props) {
  const isUser = role === 'user';
  const border = isUser ? '#d1e7ff' : '#eee';
  const bg = isUser ? '#f1f8ff' : '#fafafa';

  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <div
        style={{
          maxWidth: 720,
          border: `1px solid ${border}`,
          background: bg,
          borderRadius: 12,
          padding: '10px 14px',
          margin: '8px 0',
        }}
      >
        <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
          {isUser ? 'You' : 'Assistant'} • {dayjs(created_at).format('YYYY-MM-DD HH:mm:ss')}
        </div>

        {attachment_type === 'image' && attachment_ref && (
          <div style={{ marginBottom: 8 }}>
            <img
              src={resolveAttachmentUrl(attachment_ref)}
              alt="uploaded"
              style={{ maxWidth: '100%', borderRadius: 8, border: '1px solid #eee' }}
            />
          </div>
        )}

        <div style={{ lineHeight: 1.5 }}>
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
