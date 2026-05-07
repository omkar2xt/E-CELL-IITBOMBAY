import { useState, useEffect, useRef } from 'react';

export function useWebSocket(url) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('connecting');
  const wsRef = useRef(null);

  useEffect(() => {
    function connect() {
      setStatus('connecting');
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        setStatus('connected');
        console.log('[WebSocket] Connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch (err) {
          console.error('[WebSocket] Failed to parse message', err);
        }
      };
      
      ws.onclose = () => {
        setStatus('disconnected');
        console.log('[WebSocket] Disconnected, reconnecting in 2s...');
        setTimeout(connect, 2000);
      };
      
      ws.onerror = (err) => {
        console.error('[WebSocket] Error', err);
        ws.close();
      };
      
      wsRef.current = ws;
    }
    
    connect();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  return { data, status };
}
