import { useState, useEffect, useRef } from 'react';

export function useWebSocket(url) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('connecting');
  const wsRef = useRef(null);
  const timeoutRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    function connect() {
      if (!isMounted) return;
      setStatus('connecting');

      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) {
            ws.close();
            return;
          }
          setStatus('connected');
          console.log('[WebSocket] Connected');
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const parsed = JSON.parse(event.data);
            setData(parsed);
          } catch (err) {
            console.error('[WebSocket] Failed to parse message', err);
          }
        };

        ws.onclose = (event) => {
          if (!isMounted) return;
          setStatus('disconnected');
          console.log('[WebSocket] Disconnected, reconnecting in 2s...');
          timeoutRef.current = setTimeout(connect, 2000);
        };

        ws.onerror = (err) => {
          if (!isMounted) return;
          console.error('[WebSocket] Error', err);
          ws.close();
        };
      } catch (err) {
        if (!isMounted) return;
        setStatus('disconnected');
        timeoutRef.current = setTimeout(connect, 2000);
      }
    }

    connect();

    return () => {
      isMounted = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url]);

  return { data, status };
}
