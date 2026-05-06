/** Agent 执行阶段（对应后端 LangGraph 节点） */
export type AgentPhase =
  | 'idle'
  | 'analyzing'
  | 'generating'
  | 'executing'
  | 'translating'
  | 'retrying'
  | 'done'
  | 'error';

/** SSE 推送的单条事件 */
export interface AgentEvent {
  phase: AgentPhase;
  question?: string | null;
  sql?: string | null;
  columns?: string[] | null;
  rows?: Record<string, unknown>[] | null;
  answer?: string | null;
  error?: string | null;
  retry_count?: number;
  is_chitchat?: boolean;
}

/** 查询状态 */
export interface QueryState {
  phase: AgentPhase;
  question: string;
  sql: string | null;
  columns: string[] | null;
  rows: Record<string, unknown>[] | null;
  answer: string | null;
  error: string | null;
  retryCount: number;
  isChitchat: boolean;
}

/** Reducer 动作 */
export type QueryAction =
  | { type: 'START'; question: string }
  | { type: 'PHASE_UPDATE'; event: AgentEvent }
  | { type: 'RESET' }
  | { type: 'ERROR'; error: string };
