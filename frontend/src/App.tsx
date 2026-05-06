import { useEffect, useState, useContext } from 'react';
import { QueryProvider, QueryContext } from './context/QueryContext';
import { checkHealth } from './services/api';
import { useSSE } from './hooks/useSSE';
import QueryInput from './components/QueryInput';
import StatusBar from './components/StatusBar';
import SqlDisplay from './components/SqlDisplay';
import ResultTable from './components/ResultTable';
import AnswerCard from './components/AnswerCard';
import ErrorDisplay from './components/ErrorDisplay';

function useQueryContext() {
  const ctx = useContext(QueryContext);
  if (!ctx) throw new Error('QueryContext not found');
  return ctx;
}

function AppContent() {
  const { state, dispatch } = useQueryContext();
  const { connect, disconnect } = useSSE(dispatch);
  const [dbStatus, setDbStatus] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth()
      .then((res) => setDbStatus(res.db_loaded))
      .catch(() => setDbStatus(false));
  }, []);

  // Abort in-progress SSE on unmount
  useEffect(() => {
    return () => disconnect();
  }, [disconnect]);

  const handleSubmit = (question: string) => {
    disconnect();
    connect(question);
  };

  const handleReset = () => {
    disconnect();
    dispatch({ type: 'RESET' });
  };

  const isProcessing =
    state.phase !== 'idle' && state.phase !== 'done' && state.phase !== 'error';

  return (
    <div className="app">
      <header className="app-header">
        <h1>NL2SQL Agent</h1>
        <p>
          {dbStatus === null && 'Checking backend...'}
          {dbStatus === true && 'Ask questions about your data in natural language'}
          {dbStatus === false && 'Backend not connected. Please start the server.'}
        </p>
      </header>

      <main className="app-main">
        <QueryInput onSubmit={handleSubmit} disabled={isProcessing} />

        <StatusBar phase={state.phase} retryCount={state.retryCount} />

        {state.sql && !state.isChitchat && <SqlDisplay sql={state.sql} />}

        {state.columns && state.rows && !state.isChitchat && (
          <ResultTable columns={state.columns} rows={state.rows} />
        )}

        {state.answer && (
          <AnswerCard answer={state.answer} isChitchat={state.isChitchat} />
        )}

        {state.phase === 'error' && (
          <ErrorDisplay
            error={state.error || 'Unknown error'}
            retryCount={state.retryCount}
            onReset={handleReset}
          />
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryProvider>
      <AppContent />
    </QueryProvider>
  );
}
