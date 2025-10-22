import './ErrorBanner.scss';

export function ErrorBanner({ text, onClose }: { text: string; onClose: () => void }) {
  if (!text) return null;
  return (
    <div className="alert alert--error">
      <div className="alert__title">Something went wrong</div>
      <div className="alert__body">{text}</div>
      <button className="alert__close" onClick={onClose} aria-label="Close error">×</button>
    </div>
  );
}
