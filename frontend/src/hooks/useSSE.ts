import { useState, useRef, useCallback } from 'react';
import type { Dispatch } from 'react';
import type { QueryAction } from '../types';
import { streamQuery } from '../services/api';

export function useSSE(dispatch: Dispatch<QueryAction>) {
  const [isConnected, setIsConnected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const connect = useCallback(
    (question: string) => {
      const controller = new AbortController();
      abortRef.current = controller;

      dispatch({ type: 'START', question });
      setIsConnected(true);

      const decoder = new TextDecoder();
      let buffer = '';

      streamQuery(question, controller.signal)
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
          }
          const reader = response.body?.getReader();
          if (!reader) throw new Error('No response body');

          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });

              // SSE events are separated by \n\n
              const parts = buffer.split('\n\n');
              // Last part may be incomplete — keep in buffer
              buffer = parts.pop() || '';

              for (const part of parts) {
                const trimmed = part.trim();
                if (!trimmed) continue;

                // Find data: line in the event block
                const lines = trimmed.split('\n');
                for (const line of lines) {
                  if (line.startsWith('data:')) {
                    const jsonStr = line.slice(5).trim();
                    if (!jsonStr) continue;
                    try {
                      const event = JSON.parse(jsonStr);
                      dispatch({ type: 'PHASE_UPDATE', event });
                    } catch {
                      // Skip malformed JSON lines
                    }
                  }
                }
              }
            }
          } finally {
            reader.releaseLock();
            setIsConnected(false);
          }
        })
        .catch((err: Error) => {
          if (err.name !== 'AbortError') {
            dispatch({
              type: 'ERROR',
              error: err.message || 'Network error',
            });
          }
          setIsConnected(false);
        });
    },
    [dispatch],
  );

  const disconnect = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsConnected(false);
  }, []);

  return { connect, disconnect, isConnected };
}
