// pages/MovementFlow.jsx — StorePulse AI
// Developer: Omkar Gurav
import React, { useEffect, useState } from 'react';
import { Navigation, ArrowRight, RefreshCw } from 'lucide-react';

const API = 'http://localhost:8000';

export default function MovementFlow() {
  const [transitions, setTransitions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API}/api/zones/transitions`);
      const json = await res.json();
      setTransitions(json.transitions || []);
    } catch { }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 5000);
    return () => clearInterval(iv);
  }, []);

  const maxCount = transitions.length ? Math.max(...transitions.map(t => t.count), 1) : 1;

  return (
    <div className="fade-in">
      <div className="disclaimer-box">
        <Navigation size={14} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          Movement paths use anonymous temporary tracking IDs only.
          No individual movement histories are persisted.
          Zone transitions are aggregated counts only.
          Pixel displacement is shown — not real-world distance unless camera calibration is configured.
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <button className="sim-btn" onClick={fetchData}><RefreshCw size={13} /> Refresh</button>
      </div>

      {loading ? (
        <div className="empty-state"><div className="loading-spinner" /></div>
      ) : transitions.length === 0 ? (
        <div className="empty-state">
          <Navigation size={40} />
          <h3>No Movement Data Yet</h3>
          <p>Zone-to-zone transitions appear here once customers are detected moving between zones.</p>
        </div>
      ) : (
        <div className="grid-2">
          {/* Transition table */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Zone-to-Zone Transitions</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{transitions.length} routes</span>
            </div>
            <div className="scroll-area" style={{ maxHeight: 380 }}>
              {transitions.map((t, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.04)'
                }}>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 110, fontWeight: 500 }}>
                    {t.from_zone}
                  </span>
                  <ArrowRight size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 110, fontWeight: 500 }}>
                    {t.to_zone}
                  </span>
                  <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(t.count / maxCount) * 100}%`,
                      background: 'linear-gradient(90deg,#6366f1,#06b6d4)',
                      borderRadius: 3,
                      transition: 'width 0.5s',
                    }} />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', width: 30, textAlign: 'right' }}>
                    {t.count}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Flow visualization (SVG schematic) */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Flow Map (Schematic)</span>
              <span style={{ fontSize: 11, color: 'var(--brand-warning)' }}>Heuristic representation</span>
            </div>
            <div style={{ position: 'relative', height: 300, background: 'rgba(255,255,255,0.02)', borderRadius: 8, overflow: 'hidden' }}>
              <svg width="100%" height="100%" viewBox="0 0 400 280">
                {/* Store outline */}
                <rect x="20" y="20" width="360" height="240" rx="8"
                  fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1.5" strokeDasharray="4 4" />

                {/* Zone bubbles — simplified layout */}
                {[
                  { id: 'entrance', x: 40, y: 190, label: 'Entrance', color: '#10b981' },
                  { id: 'checkout', x: 70, y: 70, label: 'Checkout', color: '#6366f1' },
                  { id: 'grocery', x: 230, y: 180, label: 'Grocery', color: '#06b6d4' },
                  { id: 'electronics', x: 300, y: 70, label: 'Electronics', color: '#8b5cf6' },
                  { id: 'promo', x: 185, y: 110, label: 'Promo', color: '#f59e0b' },
                ].map(zone => {
                  const topTrans = transitions.filter(t => t.from_zone === zone.id || t.to_zone === zone.id);
                  const total = topTrans.reduce((s, t) => s + t.count, 0);
                  const r = 20 + Math.min(20, total);
                  return (
                    <g key={zone.id}>
                      <circle cx={zone.x} cy={zone.y} r={r}
                        fill={`${zone.color}22`} stroke={zone.color} strokeWidth="1.5" />
                      <text x={zone.x} y={zone.y - r - 5} textAnchor="middle"
                        fill={zone.color} fontSize="9" fontWeight="600">
                        {zone.label}
                      </text>
                      {total > 0 && (
                        <text x={zone.x} y={zone.y + 4} textAnchor="middle"
                          fill="white" fontSize="11" fontWeight="700">
                          {total}
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Flow lines */}
                {transitions.slice(0, 8).map((t, i) => {
                  const zones = {
                    entrance: { x: 40, y: 190 },
                    checkout: { x: 70, y: 70 },
                    grocery: { x: 230, y: 180 },
                    electronics: { x: 300, y: 70 },
                    promo: { x: 185, y: 110 },
                  };
                  const from = zones[t.from_zone];
                  const to = zones[t.to_zone];
                  if (!from || !to) return null;
                  const w = Math.max(1, Math.min(5, (t.count / maxCount) * 5));
                  return (
                    <line key={i}
                      x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                      stroke="#6366f1" strokeWidth={w} opacity="0.4"
                      markerEnd="url(#arrowhead)"
                    />
                  );
                })}

                <defs>
                  <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
                    <polygon points="0 0, 6 2, 0 4" fill="#6366f1" opacity="0.6" />
                  </marker>
                </defs>
              </svg>
              <div style={{ position: 'absolute', bottom: 8, right: 8, fontSize: 10, color: 'var(--text-muted)' }}>
                Zone positions are illustrative only
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
