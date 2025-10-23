import './TypingBubble.scss';

export function TypingBubble() {
  return (
    <div className="message-row left">
      <div className="bubble bubble--assistant typing">
        <div className="typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  );
}
