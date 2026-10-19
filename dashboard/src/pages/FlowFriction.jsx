// pages/FlowFriction.jsx — StorePulse AI
// Developer: Omkar Gurav
import React, { useEffect, useState } from 'react';
import { Zap, RefreshCw, Info } from 'lucide-react';
import { FrictionGauge } from '../components/FrictionGauge';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { API_BASE as API } from '../config';

export default function FlowFriction() {
  const [frictionData, setFrictionData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch_ = async () => {
    try {
      const res = await fetch(`${API}/api/analytics/friction`);
      const json = await res.json();
      setFrictionData(json);
    } catch { }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetch_();
    const iv = setInterval(fetch_, 5000);
    return () => clearInterval(iv);
  }, []);

  const zones = frictionData?.zone_scores ? Object.values(frictionData.zone_scores) : [];
  const store = frictionData?.store_level;

  return (
    <div className="fade-in">
      <div className="disclaimer-box">
        <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          <strong>Prototype metric.</strong> Flow Friction Scores are configurable heuristic estimates —
          not validated industry standards. Weights: Occupancy (35%), Dwell Time (30%), Queue (20%).
          Calibrate thresholds using observed footage before operational decisions.
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <button className="sim-btn" onClick={fetch_}><RefreshCw size={13} /> Refresh</button>
      </div>

      {loading ? (
        <div className="empty-state"><div className="loading-spinner" /></div>
      ) : !frictionData || zones.length === 0 ? (
        <div className="empty-state">
          <Zap size={40} />
          <h3>No Friction Data</h3>
          <p>Flow Friction Scores appear once zone analytics have collected at least 3 samples.</p>
        </div>
      ) : (
        <>
          {/* Store-level gauge */}
          {store && (
            <div className="card" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
              <FrictionGauge score={store.score} alertLevel={store.alert_level} />
              <div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>Store-Level Friction Score</div>
                <div style={{ fontSize: 24, fontWeight: 700, fontFamily: 'Space Grotesk, sans-serif' }}>
                  {store.score.toFixed(1)} <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>avg</span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                  Peak: <strong>{store.peak_score}</strong> · {store.zone_count} zones monitored
                </div>
                <div style={{
                  marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '3px 12px', borderRadius: 8, fontWeight: 700, fontSize: 12,
                  background: store.alert_level === 'CRITICAL' ? 'rgba(239,68,68,0.15)' :
                    store.alert_level === 'HIGH' ? 'rgba(249,115,22,0.15)' :
                    store.alert_level === 'MEDIUM' ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)',
                  color: store.alert_level === 'CRITICAL' ? '#ef4444' :
                    store.alert_level === 'HIGH' ? '#f97316' :
                    store.alert_level === 'MEDIUM' ? '#f59e0b' : '#10b981',
                }}>
                  {store.alert_level === 'NONE' ? '✓ Flow Normal' : `⚠ ${store.alert_level}`}
                </div>
              </div>
            </div>
          )}

          {/* Per-zone cards */}
          <div className="zone-grid" style={{ marginBottom: 20 }}>
            {zones.map(z => (
              <div key={z.zone_id} className="card" style={{ padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{z.zone_name}</span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 6,
                    background: z.alert_level === 'CRITICAL' ? 'rgba(239,68,68,0.15)' :
                      z.alert_level === 'HIGH' ? 'rgba(249,115,22,0.15)' :
                      z.alert_level === 'MEDIUM' ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)',
                    color: z.alert_level === 'CRITICAL' ? '#ef4444' :
                      z.alert_level === 'HIGH' ? '#f97316' :
                      z.alert_level === 'MEDIUM' ? '#f59e0b' : '#10b981',
                  }}>
                    {z.alert_level}
                  </span>
                </div>

                <FrictionGauge score={z.score} alertLevel={z.alert_level} />

                {/* Component breakdown */}
                <div style={{ marginTop: 12 }}>
                  {[
                    { label: 'Occupancy', val: z.components.occupancy_score, color: '#6366f1' },
                    { label: 'Dwell Time', val: z.components.dwell_score, color: '#06b6d4' },
                    { label: 'Queue', val: z.components.queue_score, color: '#f59e0b' },
                  ].map(c => (
                    <div key={c.label} style={{ marginBottom: 6 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3, color: 'var(--text-muted)' }}>
                        <span>{c.label}</span><span>{c.val.toFixed(0)}</span>
                      </div>
                      <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${c.val}%`, background: c.color, borderRadius: 2, transition: 'width 0.5s' }} />
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>{z.explanation}</div>
                {z.recommendation !== 'No action needed. Zone is operating normally.' && (
                  <div style={{
                    marginTop: 8, padding: '6px 10px', background: 'rgba(99,102,241,0.08)',
                    borderRadius: 6, fontSize: 11, color: 'var(--brand-primary)', borderLeft: '2px solid var(--brand-primary)'
                  }}>
                    💡 {z.recommendation}
                  </div>
                )}
                <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text-muted)' }}>
                  Confidence: {z.data_confidence}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
