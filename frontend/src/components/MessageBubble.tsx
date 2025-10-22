import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './MessageBubble.scss';
import type { ChatMessage, ToolOutputs } from '../api';

export function MessageBubble({ m, tool }: { m: ChatMessage; tool?: ToolOutputs }) {
  const isUser = m.role === 'user';
  return (
    <div className={`message-row ${isUser ? 'right' : 'left'}`}>
      <div className={`bubble ${isUser ? 'bubble--user' : 'bubble--assistant'}`}>
        {isUser ? (
          <div className="prose prose-sm">{m.content}</div>
        ) : (
          <div className="prose prose-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
          </div>
        )}

        {!isUser && tool && (
          <div className="tool-panel">
            {tool.image_path && (
              <div>
                <div className="section-title">Image referenced</div>
                <div className="italic">(handled on server)</div>
              </div>
            )}
            {tool.histogram_image && !m.content.includes('![Histogram](') && (
              <div>
                <div className="section-title">Histogram generated</div>
                <img
                  src={`${import.meta.env.VITE_API_BASE}/static/${tool.histogram_image.split('uploads/').pop()}`}
                  alt="histogram"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}