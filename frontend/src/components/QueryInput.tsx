import { useState } from 'react';

interface Props {
  onSubmit: (question: string) => void;
  disabled: boolean;
}

const EXAMPLE_QUESTIONS = [
  '上个月销售额最高的三个产品是什么',
  '哪些客户的订单总数超过 10 单',
  '退货率最高的品类是哪个',
];

export default function QueryInput({ onSubmit, disabled }: Props) {
  const [value, setValue] = useState('');

  const trimmed = value.trim();

  const handleSubmit = () => {
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <section className="query-input-section">
      <div className="query-input-wrapper">
        <textarea
          className="query-input-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的问题，例如「上个月销售额最高的三个产品是什么」"
          rows={2}
          disabled={disabled}
        />
        <button
          className="btn btn-primary query-input-btn"
          onClick={handleSubmit}
          disabled={disabled || !trimmed}
        >
          {disabled ? '查询中...' : '查询'}
        </button>
      </div>

      <div className="query-input-examples">
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            className="query-input-example-chip"
            onClick={() => {
              if (!disabled) {
                setValue(q);
              }
            }}
            disabled={disabled}
          >
            {q}
          </button>
        ))}
      </div>
    </section>
  );
}
