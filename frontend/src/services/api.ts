const API_BASE = '/api';

export interface HealthResponse {
  status: string;
  db_loaded: boolean;
}

export interface SchemaColumn {
  name: string;
  type: string;
}

export interface SchemaTable {
  name: string;
  columns: SchemaColumn[];
}

export interface SchemaResponse {
  tables: SchemaTable[];
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

export async function getSchema(): Promise<SchemaResponse> {
  const res = await fetch(`${API_BASE}/db/schema`);
  if (!res.ok) {
    throw new Error(`Schema fetch failed: ${res.status}`);
  }
  return res.json();
}

export function streamQuery(
  question: string,
  signal?: AbortSignal,
): Promise<Response> {
  return fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    signal,
  });
}
