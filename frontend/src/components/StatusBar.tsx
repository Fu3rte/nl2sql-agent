import type { AgentPhase } from '../types';
import './StatusBar.css';

interface Props {
  phase: AgentPhase;
  retryCount: number;
}

interface StepDef {
  phase: AgentPhase;
  label: string;
}

const STEPS: StepDef[] = [
  { phase: 'analyzing', label: '分析' },
  { phase: 'generating', label: '生成 SQL' },
  { phase: 'executing', label: '执行' },
  { phase: 'translating', label: '翻译' },
  { phase: 'done', label: '完成' },
];

const PHASE_ORDER: Record<AgentPhase, number> = {
  idle: -1,
  analyzing: 0,
  generating: 1,
  executing: 2,
  translating: 3,
  retrying: 1, // visually highlights "生成 SQL" step
  done: 4,
  error: -1,
};

export default function StatusBar({ phase, retryCount }: Props) {
  if (phase === 'idle' || phase === 'done' || phase === 'error') {
    return null;
  }

  const currentIdx = PHASE_ORDER[phase];

  return (
    <div className="status-bar fade-in">
      {STEPS.map((step, i) => {
        let cls = 'status-step';
        if (i < currentIdx) cls += ' status-step--done';
        else if (i === currentIdx) cls += ' status-step--active';

        return (
          <div key={step.phase} className={cls}>
            <span className="status-step-dot">
              {i < currentIdx ? '\u2713' : i + 1}
            </span>
            <span className="status-step-label">
              {step.label}
              {phase === 'retrying' && step.phase === 'generating' && retryCount > 0
                ? ` (重试 ${retryCount}/3)`
                : ''}
            </span>
            {i < STEPS.length - 1 && <span className="status-step-line" />}
          </div>
        );
      })}
    </div>
  );
}
