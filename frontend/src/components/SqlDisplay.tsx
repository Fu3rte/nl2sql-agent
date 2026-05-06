import { useEffect, useRef, useState } from 'react';
import hljs from 'highlight.js/lib/core';
import sql from 'highlight.js/lib/languages/sql';
import './SqlDisplay.css';

hljs.registerLanguage('sql', sql);

interface Props {
  sql: string;
}

export default function SqlDisplay({ sql: code }: Props) {
  const codeRef = useRef<HTMLElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (codeRef.current) {
      hljs.highlightElement(codeRef.current);
    }
  }, [code]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available — silently ignore
    }
  };

  return (
    <section className="sql-display card fade-in">
      <div className="sql-display-header">
        <span className="card-header">SQL</span>
        <button className="btn sql-copy-btn" onClick={handleCopy}>
          {copied ? '已复制' : '复制'}
        </button>
      </div>
      <pre className="sql-code-block">
        <code ref={codeRef} className="language-sql">
          {code}
        </code>
      </pre>
    </section>
  );
}
