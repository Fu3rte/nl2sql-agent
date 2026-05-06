import { createContext, useReducer, type Dispatch, type ReactNode } from 'react';
import type { AgentPhase, QueryState, QueryAction } from '../types';

// Phase ordering: higher = further along the pipeline
const PHASE_ORDER: Record<AgentPhase, number> = {
  idle: 0,
  analyzing: 1,
  generating: 2,
  executing: 3,
  translating: 4,
  done: 5,
  error: 6,
  retrying: 7,
};

export const initialState: QueryState = {
  phase: 'idle',
  question: '',
  sql: null,
  columns: null,
  rows: null,
  answer: null,
  error: null,
  retryCount: 0,
  isChitchat: false,
};

function queryReducer(state: QueryState, action: QueryAction): QueryState {
  switch (action.type) {
    case 'START':
      return {
        ...initialState,
        phase: 'analyzing',
        question: action.question,
      };

    case 'PHASE_UPDATE': {
      const { event } = action;
      const nextPhase = event.phase;

      // Skip if the new phase is an illegal backwards transition
      // (except: retrying→generating is a valid loop; reset always allowed)
      const currentOrder = PHASE_ORDER[state.phase];
      const nextOrder = PHASE_ORDER[nextPhase];

      if (
        nextOrder < currentOrder &&
        !(state.phase === 'retrying' && nextPhase === 'generating') &&
        nextPhase !== 'error' // error can arrive from any state
      ) {
        return state;
      }

      return {
        ...state,
        phase: nextPhase,
        question: event.question ?? state.question,
        sql: event.sql !== undefined ? event.sql : state.sql,
        columns: event.columns !== undefined ? event.columns : state.columns,
        rows: event.rows !== undefined ? event.rows : state.rows,
        answer: event.answer !== undefined ? event.answer : state.answer,
        error: event.error !== undefined ? event.error : state.error,
        retryCount: event.retry_count ?? state.retryCount,
        isChitchat: event.is_chitchat ?? state.isChitchat,
      };
    }

    case 'ERROR':
      return {
        ...state,
        phase: 'error',
        error: action.error,
      };

    case 'RESET':
      return initialState;

    default:
      return state;
  }
}

interface QueryContextValue {
  state: QueryState;
  dispatch: Dispatch<QueryAction>;
}

export const QueryContext = createContext<QueryContextValue | null>(null);

export function QueryProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(queryReducer, initialState);
  return (
    <QueryContext.Provider value={{ state, dispatch }}>
      {children}
    </QueryContext.Provider>
  );
}
