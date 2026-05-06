import { useEffect, useState } from 'react';
import { QueryProvider } from './context/QueryContext';
import { checkHealth } from './services/api';

function AppContent() {
  const [dbStatus, setDbStatus] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth()
      .then((res) => setDbStatus(res.db_loaded))
      .catch(() => setDbStatus(false));
  }, []);

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
        {/* Wave 2 components will be assembled here */}
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
