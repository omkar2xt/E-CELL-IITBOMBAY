// pages/Heatmaps.jsx — StorePulse AI
// Developer: Omkar Gurav
import React, { useEffect, useRef, useState } from 'react';
import { Flame } from 'lucide-react';
import { API_BASE } from '../config';

const API = API_BASE;
const STREAM_URL = `${API_BASE}/snapshot`;

function renderHeatmapToCanvas(canvas, data) {
  if (!canvas || !data) return;
  const ctx = canvas.getContext('2d');
  const rows = data.length;
  const cols = data[0]?.length || 0;
  if (!rows || !cols) return;
  const cw = canvas.width / cols;
  const ch = canvas.height / rows;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const v = data[r][c];
      // Map 0-255 to jet colormap
      const t = v / 255;
      let r_ = 0, g = 0, b = 0;
      if (t < 0.125)      { b = 0.5 + t * 4; r_ = 0; g = 0; }
      else if (t < 0.375) { b = 1; g = (t - 0.125) * 4; r_ = 0; }
      else if (t < 0.625) { b = 1 - (t - 0.375) * 4; g = 1; r_ = (t - 0.375) * 4; }
      else if (t < 0.875) { b = 0; g = 1 - (t - 0.625) * 4; r_ = 1; }
      else                { b = 0; g = 0; r_ = 1 - (t - 0.875) * 4; }
      const alpha = v > 10 ? 0.3 + (v / 255) * 0.7 : 0;
      ctx.fillStyle = `rgba(${Math.round(r_*255)},${Math.round(g*255)},${Math.round(b*255)},${alpha.toFixed(2)})`;
      ctx.fillRect(c * cw, r * ch, cw, ch);
    }
  }
}

export default function Heatmaps({ wsStatus }) {
  const canvasRef = useRef(null);
  const [heatData, setHeatData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHeatmap = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/heatmap`);
      const json = await res.json();
      if (json.heatmap) setHeatData(json.heatmap);
    } catch { }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchHeatmap();
    const iv = setInterval(fetchHeatmap, 2000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    renderHeatmapToCanvas(canvasRef.current, heatData);
  }, [heatData]);

  return (
    <div className="fade-in">
      <div className="info-box">
        <strong>About heatmaps:</strong> Gaussian kernel accumulation of foot positions.
        Brighter/redder areas = more time spent by tracked persons.
        The heatmap resets when the pipeline restarts.
        <br />Data source: <strong>real-time tracking</strong> (or demo synthetic if no video).
      </div>

      <div className="grid-2">
        {/* Live MJPEG with heatmap overlay */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
            <span className="card-title" style={{ margin: 0 }}>Live Feed with Heatmap Overlay</span>
          </div>
          <div className="live-feed">
            {wsStatus === 'connected' ? (
              <>
                <img
                  src={STREAM_URL}
                  alt="Heatmap live"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  onError={e => {
                    console.warn('[Feed] Heatmap stream disconnected');
                    e.target.style.display = 'none';
                    const fb = document.getElementById('heatmap-feed-placeholder');
                    if (fb) fb.style.display = 'flex';
                  }}
                />
                <div id="heatmap-feed-placeholder" className="feed-placeholder" style={{ display: 'none' }}>
                  <Flame size={40} style={{ opacity: 0.2 }} />
                  <div>Stream Connecting...</div>
                </div>
                <div className="live-feed-overlay"><span className="live-dot" />LIVE</div>
              </>
            ) : (
              <div className="feed-placeholder">
                <Flame size={40} style={{ opacity: 0.2 }} />
                <div>Connecting to backend...</div>
              </div>
            )}
          </div>
        </div>

        {/* Heatmap data canvas */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Foot Traffic Density Map</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>64×64 grid, jet colormap</span>
          </div>
          <div style={{ position: 'relative' }}>
            {loading ? (
              <div className="empty-state" style={{ height: 240 }}>
                <div className="loading-spinner" />
              </div>
            ) : (
              <canvas
                ref={canvasRef}
                width={512} height={288}
                className="heatmap-canvas"
              />
            )}
            {!heatData && !loading && (
              <div style={{
                position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'var(--text-muted)', fontSize: 13
              }}>
                No heatmap data yet — waiting for tracked persons
              </div>
            )}
          </div>
          {/* Colormap legend */}
          <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Low traffic</span>
            <div style={{
              flex: 1, height: 8, borderRadius: 4,
              background: 'linear-gradient(90deg, #00007f, #0000ff, #00ffff, #00ff00, #ffff00, #ff7f00, #ff0000)'
            }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>High traffic</span>
          </div>
        </div>
      </div>
    </div>
  );
}
