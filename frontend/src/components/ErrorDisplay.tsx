import './ErrorDisplay.css';

interface Props {
  error: string;
  retryCount: number;
  onReset: () => void;
}

export default function ErrorDisplay({ error, retryCount, onReset }: Props) {
  return (
    <section className="error-display card fade-in">
      <div className="error-display-header">
        <span className="card-header">错误</span>
        {retryCount > 0 && retryCount <= 3 && (
          <span className="error-display-retry">已重试 {retryCount}/3 次</span>
        )}
      </div>
      <p className="error-display-message">{error}</p>
      <button className="btn btn-primary" onClick={onReset}>
        重新提问
      </button>
    </section>
  );
}
