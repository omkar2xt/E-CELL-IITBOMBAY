import React, { useState, useEffect } from 'react';

export function LiveFeed({ streamUrl, fallbackText }) {
  const [hasError, setHasError] = useState(false);
  const [timestamp, setTimestamp] = useState(Date.now());

  // Force image reload periodically if it gets stuck
  useEffect(() => {
    const interval = setInterval(() => {
      setTimestamp(Date.now());
    }, 60000); // refresh URL every 60s to prevent caching stucks
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="live-feed">
      <div className="live-feed-header">
        <div className="live-feed-title">
          <span className="live-dot pulse"></span>
          Camera 1 (Main Entrance)
        </div>
      </div>
      
      <div className="live-feed-content">
        {!hasError ? (
          <img 
            src={`${streamUrl}?t=${timestamp}`} 
            alt="Live Feed" 
            onError={() => setHasError(true)}
            className="stream-image"
          />
        ) : (
          <div className="stream-fallback">
            <p>{fallbackText || "Stream unavailable. Is the backend running?"}</p>
            <button onClick={() => { setHasError(false); setTimestamp(Date.now()); }}>
              Retry Connection
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
