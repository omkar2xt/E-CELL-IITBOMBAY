// pages/MovementFlow.jsx — StorePulse AI
// Live Observed Zone Transitions & Transition Probability Matrix
// Developer: Omkar Gurav
import React, { useEffect, useState } from 'react';
import { Navigation, ArrowRight, RefreshCw, BarChart2, AlertCircle, CheckCircle } from 'lucide-react';

const API = 'http://localhost:8000';

const DEFAULT_ZONES = ['entrance', 'grocery', 'electronics', 'promo', 'checkout'];

export default function MovementFlow() {
  const [data, setData] = useState({
    transitions: [],
    matrix: {},
    zone_outflow: {},
    total_transitions: 0,
    data_sufficient: false,
    confidence: 'LOW',
    disclaimer: '',
  });
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API}/api/zones/transitions`);
      const json = await res.json();
      setData({
        transitions: json.transitions || [],
        matrix: json.matrix || {},
        zone_outflow: json.zone_outflow || {},
        total_transitions: json.total_transitions || 0,
        data_sufficient: json.data_sufficient ?? false,
        confidence: json.confidence || 'LOW',
        disclaimer: json.disclaimer || '',
      });
    } catch { }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 5000);
    return () => clearInterval(iv);
  }, []);

  const transitions = data.transitions;
  const maxCount = transitions.length ? Math.max(...transitions.map(t => t.count), 1) : 1;

  // Extract all unique zones from matrix + transitions + default
  const allZonesSet = new Set(DEFAULT_ZONES);
  transitions.forEach(t => {
    if (t.from_zone) allZonesSet.add(t.from_zone);
    if (t.to_zone) allZonesSet.add(t.to_zone);
  });
  Object.keys(data.matrix || {}).forEach(z => allZonesSet.add(z));
  const zonesList = Array.from(allZonesSet);

  return (
    <div className="fade-in">
      <div className="disclaimer-box">
        <Navigation size={14} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          <strong>[MEASURED REAL OBSERVED EVENTS]</strong> Movement paths use anonymous temporary tracking IDs only.
          No individual movement histories or identities are persisted.
          Transition counts and probabilities are aggregated from live zone entries/exits.
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600,
            background: data.data_sufficient ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
            border: `1px solid ${data.data_sufficient ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
            color: data.data_sufficient ? '#10b981' : '#f59e0b',
          }}>
            {data.data_sufficient ? <CheckCircle size={13} /> : <AlertCircle size={13} />}
            <span>
              {data.data_sufficient
                ? `Data Sufficient (${data.total_transitions} events recorded, Confidence: ${data.confidence})`
                : `Insufficient Sample (${data.total_transitions}/5 events — Collecting real-world movement)`}
            </span>
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Total Recorded Transitions: <strong>{data.total_transitions}</strong>
          </span>
        </div>
        <button className="sim-btn" onClick={fetchData}><RefreshCw size={13} /> Refresh</button>
      </div>

      {loading ? (
        <div className="empty-state"><div className="loading-spinner" /></div>
      ) : transitions.length === 0 ? (
        <div className="empty-state">
          <Navigation size={40} />
          <h3>No Live Movement Transitions Recorded</h3>
          <p>Zone-to-zone transitions appear here once visitors with temporary track IDs cross between store zones.</p>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
            Note: StorePulse AI never fabricates visitor journeys. Only verified sequence transitions are recorded.
          </span>
        </div>
      ) : (
        <>
          {/* Transition Probability Matrix Grid / Heatmap */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <div>
                <span className="card-title">Observed Transition Probability Matrix</span>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  Grid of Origin (rows) → Destination (columns). Values show transition count & conditional probability P(dest | origin).
                </div>
              </div>
              <span style={{
                fontSize: 10, padding: '2px 8px', borderRadius: 4,
                background: 'rgba(99,102,241,0.15)', color: '#6366f1', fontWeight: 600
              }}>
                [MEASURED LIVE DATA]
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="comparison-table" style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={{ background: 'rgba(0,0,0,0.3)' }}>Origin \ Destination</th>
                    {zonesList.map(z => (
                      <th key={z} style={{ textTransform: 'capitalize', textAlign: 'center' }}>{z}</th>
                    ))}
                    <th style={{ textAlign: 'center', background: 'rgba(255,255,255,0.02)' }}>Total Outflow</th>
                  </tr>
                </thead>
                <tbody>
                  {zonesList.map(orig => {
                    const origTotal = data.zone_outflow?.[orig] || 0;
                    return (
                      <tr key={orig}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                          {orig}
                        </td>
                        {zonesList.map(dest => {
                          const count = data.matrix?.[orig]?.[dest] || 0;
                          const prob = origTotal > 0 ? (count / origTotal) : 0;
                          const bgIntensity = prob > 0 ? Math.min(0.7, 0.1 + prob * 0.6) : 0;

                          return (
                            <td key={dest} style={{
                              textAlign: 'center',
                              background: prob > 0 ? `rgba(99, 102, 241, ${bgIntensity})` : 'transparent',
                              color: prob > 0 ? '#fff' : 'var(--text-muted)',
                              fontWeight: prob > 0 ? 600 : 400,
                              transition: 'background 0.3s',
                            }}>
                              {count > 0 ? (
                                <div>
                                  <div>{count}</div>
                                  <div style={{ fontSize: 10, opacity: 0.8 }}>{(prob * 100).toFixed(0)}%</div>
                                </div>
                              ) : (
                                <span style={{ opacity: 0.25 }}>—</span>
                              )}
                            </td>
                          );
                        })}
                        <td style={{ textAlign: 'center', fontWeight: 700, color: 'var(--brand-accent)', background: 'rgba(255,255,255,0.02)' }}>
                          {origTotal}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid-2">
            {/* Transition table */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">Zone-to-Zone Route Breakdown</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{transitions.length} routes recorded</span>
              </div>
              <div className="scroll-area" style={{ maxHeight: 380 }}>
                {transitions.map((t, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.04)'
                  }}>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 95, fontWeight: 500, textTransform: 'capitalize' }}>
                      {t.from_zone}
                    </span>
                    <ArrowRight size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 95, fontWeight: 500, textTransform: 'capitalize' }}>
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
                    <div style={{ width: 85, textAlign: 'right' }}>
                      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {t.count}
                      </span>
                      {t.probability !== undefined && (
                        <span style={{ fontSize: 10, color: 'var(--brand-accent)', marginLeft: 4 }}>
                          ({(t.probability * 100).toFixed(0)}%)
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Flow visualization (SVG schematic) */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">Flow Map (Schematic)</span>
                <span style={{ fontSize: 11, color: 'var(--brand-warning)' }}>Top Observed Paths</span>
              </div>
              <div style={{ position: 'relative', height: 320, background: 'rgba(255,255,255,0.02)', borderRadius: 8, overflow: 'hidden' }}>
                <svg width="100%" height="100%" viewBox="0 0 400 280">
                  {/* Store outline */}
                  <rect x="20" y="20" width="360" height="240" rx="8"
                    fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1.5" strokeDasharray="4 4" />

                  {/* Flow lines */}
                  {transitions.slice(0, 10).map((t, i) => {
                    const zones = {
                      entrance: { x: 50, y: 200 },
                      checkout: { x: 70, y: 70 },
                      grocery: { x: 230, y: 190 },
                      electronics: { x: 310, y: 80 },
                      promo: { x: 190, y: 110 },
                    };
                    const from = zones[t.from_zone] || { x: 100, y: 100 };
                    const to = zones[t.to_zone] || { x: 200, y: 200 };
                    const w = Math.max(1, Math.min(5, (t.count / maxCount) * 5));
                    return (
                      <line key={i}
                        x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                        stroke="#6366f1" strokeWidth={w} opacity="0.45"
                        markerEnd="url(#arrowhead)"
                      />
                    );
                  })}

                  {/* Zone bubbles */}
                  {[
                    { id: 'entrance', x: 50, y: 200, label: 'Entrance', color: '#10b981' },
                    { id: 'checkout', x: 70, y: 70, label: 'Checkout', color: '#6366f1' },
                    { id: 'grocery', x: 230, y: 190, label: 'Grocery', color: '#06b6d4' },
                    { id: 'electronics', x: 310, y: 80, label: 'Electronics', color: '#8b5cf6' },
                    { id: 'promo', x: 190, y: 110, label: 'Promo', color: '#f59e0b' },
                  ].map(zone => {
                    const topTrans = transitions.filter(t => t.from_zone === zone.id || t.to_zone === zone.id);
                    const total = topTrans.reduce((s, t) => s + t.count, 0);
                    const r = 20 + Math.min(18, total * 2);
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

                  <defs>
                    <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
                      <polygon points="0 0, 6 2, 0 4" fill="#6366f1" opacity="0.6" />
                    </marker>
                  </defs>
                </svg>
                <div style={{ position: 'absolute', bottom: 8, right: 8, fontSize: 10, color: 'var(--text-muted)' }}>
                  Schematic node coordinates illustrative only
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
