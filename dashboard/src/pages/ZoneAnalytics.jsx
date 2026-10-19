// pages/ZoneAnalytics.jsx — StorePulse AI
// Developer: Omkar Gurav
import React, { useEffect, useState } from 'react';
import { MapPin, RefreshCw } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { API_BASE as API } from '../config';

function formatDwell(s) {
  if (s < 60) return `${s.toFixed(0)}s`;
  return `${(s / 60).toFixed(1)}m`;
}

export default function ZoneAnalytics({ wsData }) {
  const [zoneStats, setZoneStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [lastFetch, setLastFetch] = useState(null);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API}/api/zones/stats`);
      const json = await res.json();
      setZoneStats(json.zone_stats || {});
      setLastFetch(new Date().toLocaleTimeString());
    } catch {
      // fall back to WebSocket data
      if (wsData?.zone_stats) setZoneStats(wsData.zone_stats);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  // Use live WS data if available
  useEffect(() => {
    if (wsData?.zone_stats && Object.keys(wsData.zone_stats).length > 0) {
      setZoneStats(wsData.zone_stats);
    }
  }, [wsData]);

  const zones = Object.values(zoneStats);

  const dwellChartData = zones.map(z => ({
    name: z.zone_name,
    avg: z.avg_dwell_seconds,
    max: z.max_dwell_seconds,
    median: z.median_dwell_seconds,
  }));

  const activeBottlenecks = zones.filter(z => z.bottleneck?.is_bottleneck || z.bottleneck?.severity === 'CRITICAL' || z.bottleneck?.severity === 'HIGH');

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {lastFetch ? `Updated: ${lastFetch}` : 'Fetching...'}
          </div>
          {wsData?.is_demo && <span className="demo-badge">SIMULATION MODE</span>}
        </div>
        <button className="sim-btn" onClick={fetchStats}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {activeBottlenecks.length > 0 && (
        <div className="alert-banner" style={{ marginBottom: 20 }}>
          <div>
            <strong>⚠ ACTIVE BOTTLENECK DETECTED ({activeBottlenecks.length} {activeBottlenecks.length === 1 ? 'zone' : 'zones'}):</strong>
            {activeBottlenecks.map(b => (
              <div key={b.zone_id} style={{ marginTop: 4, fontSize: 12 }}>
                • <strong>{b.zone_name}</strong> [{b.bottleneck.severity}]: {b.bottleneck.evidence?.join('; ') || 'Sustained congestion'} — <em>{b.bottleneck.recommendation}</em>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <div className="empty-state"><div className="loading-spinner" /></div>
      ) : zones.length === 0 ? (
        <div className="empty-state">
          <MapPin size={40} />
          <h3>No Zone Data</h3>
          <p>Zone analytics will appear once the pipeline is running and detecting people.</p>
        </div>
      ) : (
        <>
          <div className="zone-grid" style={{ marginBottom: 24 }}>
            {zones.map(z => {
              const b = z.bottleneck || {};
              const isBottleneck = b.is_bottleneck || b.severity === 'CRITICAL';
              return (
                <div key={z.zone_id} className={`zone-card ${isBottleneck ? 'congested' : z.congestion_status === 'HIGH' ? 'warning' : ''}`}>
                  <div className="zone-header">
                    <span className="zone-name">{z.zone_name}</span>
                    <span className={`congestion-badge ${isBottleneck ? 'CRITICAL' : z.congestion_status}`}>
                      {isBottleneck ? 'BOTTLENECK' : z.congestion_status}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                    <span>{z.zone_type.toUpperCase()}</span>
                    <span>{z.unique_visitors || z.total_entries} unique visitors</span>
                  </div>

                  <div className="zone-occupancy-bar">
                    <div
                      className={`zone-occupancy-fill ${z.congestion_pct >= 75 ? 'critical' : z.congestion_pct >= 50 ? 'high' : ''}`}
                      style={{ width: `${Math.min(100, z.congestion_pct)}%` }}
                    />
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
                    {z.current_occupancy} / {z.capacity} people ({z.congestion_pct}% capacity)
                  </div>

                  <div className="zone-stats">
                    <div className="zone-stat">
                      <span className="zone-stat-label">Active Dwell</span>
                      <span className="zone-stat-value">{formatDwell(z.active_avg_dwell_seconds || 0)}</span>
                    </div>
                    <div className="zone-stat">
                      <span className="zone-stat-label">Completed Avg</span>
                      <span className="zone-stat-value">{formatDwell(z.avg_dwell_seconds || 0)}</span>
                    </div>
                    <div className="zone-stat">
                      <span className="zone-stat-label">Median Dwell</span>
                      <span className="zone-stat-value">{formatDwell(z.median_dwell_seconds || 0)}</span>
                    </div>
                    <div className="zone-stat">
                      <span className="zone-stat-label">Total Visits</span>
                      <span className="zone-stat-value">{z.total_entries}</span>
                    </div>
                  </div>

                  {b.is_bottleneck && b.evidence && b.evidence.length > 0 && (
                    <div style={{
                      marginTop: 10, padding: '6px 8px',
                      background: 'rgba(239,68,68,0.12)', borderRadius: 6,
                      fontSize: 11, color: '#fca5a5'
                    }}>
                      <div style={{ fontWeight: 700 }}>⚠ Bottleneck Evidence:</div>
                      <div>{b.evidence.join(' · ')}</div>
                      {b.recommendation && (
                        <div style={{ marginTop: 4, color: '#fed7aa', fontStyle: 'italic' }}>
                          Action: {b.recommendation}
                        </div>
                      )}
                    </div>
                  )}

                  {!b.is_bottleneck && z.dwell_alert && (
                    <div style={{
                      marginTop: 8, padding: '4px 8px',
                      background: 'rgba(245,158,11,0.12)', borderRadius: 6,
                      fontSize: 11, color: '#fcd34d', fontWeight: 600
                    }}>
                      ⚠ Dwell time exceeds {z.dwell_alert_seconds || 120}s threshold
                    </div>
                  )}
                </div>
              );
            })}
          </div>


          {/* Dwell time comparison chart */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Dwell Time Comparison (seconds)</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Based on {zones.reduce((s, z) => s + z.sample_count, 0)} completed visits
              </span>
            </div>
            <div style={{ height: 220 }}>
              <ResponsiveContainer>
                <BarChart data={dwellChartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Bar dataKey="avg" name="Avg Dwell (s)" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="median" name="Median (s)" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="max" name="Max (s)" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="info-box" style={{ marginTop: 16 }}>
            <strong>Note:</strong> Dwell times reflect time observed within camera view only.
            Activity outside the observed area cannot be inferred.
            Statistics shown are based on {zones.reduce((s, z) => s + z.sample_count, 0)} completed zone visits.
            Samples &lt;3 per zone are insufficient for reliable median calculation.
          </div>
        </>
      )}
    </div>
  );
}
