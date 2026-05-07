import { useState, useEffect } from 'react';

export function useQueueHistory(currentQueueCount, maxItems = 60) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    // Only add to history if currentQueueCount is valid number
    if (currentQueueCount !== undefined && currentQueueCount !== null) {
      setHistory(prev => {
        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
        
        const newItem = { time: timeStr, count: currentQueueCount };
        const next = [...prev, newItem];
        if (next.length > maxItems) {
          return next.slice(next.length - maxItems);
        }
        return next;
      });
    }
  }, [currentQueueCount, maxItems]);

  return history;
}
