// pages/Overview.jsx — StorePulse AI
// Author: Omkar Gurav
import React from 'react';
import { Users, LogIn, LogOut, Activity, AlertTriangle, Camera, Zap } from 'lucide-react';
import { StatCard } from '../components/StatCard';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

const STREAM_URL = 'http://localhost:8000/snapshot';

function formatTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function Overview({ data, queueHistory, wsStatus }) {
  const isDemo = data?.is_demo;

  return (
    <div className="fade-in">
      {/* Demo warning */}
      {isDemo && (
        <div className="alert-banner" style={{ borderColor: 'rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.08)', color: '#fbbf24' }}>
          <AlertTriangle size={18} />
          <span>
            <strong>DEMO MODE</strong> — No video source detected. Displaying synthetic data.
            Connect a camera or provide a video file via VIDEO_SOURCE in .env
          </span>
        </div>
      )}

      {/* Queue alert */}
      {data?.queue_alert && (
        <div className="alert-banner">
          <AlertTriangle size={18} />
          <span>
            <strong>QUEUE ALERT!</strong> Checkout queue exceeded threshold ({data.queue_count} people). Open another register immediately.
          </span>
        </div>
      )}

      {/* Stat cards */}
      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', marginBottom: 20 }}>
        <StatCard title="Total IN" value={data?.count_in ?? '—'} icon={LogIn}
          color="linear-gradient(90deg,#6366f1,#8b5cf6)" />
        <StatCard title="Total OUT" value={data?.count_out ?? '—'} icon={LogOut}
          color="linear-gradient(90deg,#06b6d4,#6366f1)" />
        <StatCard title="Occupancy" value={data?.occupancy ?? '—'} icon={Users}
          subtitle="Est. people inside" color="linear-gradient(90deg,#10b981,#06b6d4)" />
        <StatCard title="Queue" value={data?.queue_count ?? '—'} icon={Activity}
          alert={data?.queue_alert} color="linear-gradient(90deg,#f59e0b,#ef4444)" />
        <StatCard title="Tracked" value={data?.tracked_count ?? '—'} icon={Camera}
          subtitle="In current frame" color="linear-gradient(90deg,#8b5cf6,#ec4899)" />
        <StatCard title="FPS" value={data?.fps ? data.fps.toFixed(1) : '—'} icon={Zap}
          color="linear-gradient(90deg,#06b6d4,#10b981)" />
      </div>

      <div className="grid-2">
        {/* Live Feed */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="card-title" style={{ margin: 0 }}>Live Camera Feed</span>
            <div style={{ marginLeft: 'auto' }}
              data-connected={wsStatus === 'connected'}
              className={`status-pill ${wsStatus}`}>
              <span className="status-dot" />
              {wsStatus === 'connected' ? 'LIVE' : wsStatus.toUpperCase()}
            </div>
          </div>
          <div className="live-feed">
            {wsStatus === 'connected' && !isDemo ? (
              <>
                <img src={STREAM_URL} alt="Live camera feed" loading="lazy"
                  onError={e => { e.target.style.display = 'none'; }} />
                <div className="live-feed-overlay">
                  <span className="live-dot" /> LIVE
                </div>
              </>
            ) : (
              <div className="feed-placeholder">
                <Camera size={40} style={{ opacity: 0.2 }} />
                <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
                  {isDemo ? 'Demo Mode — No Video' : 'Connecting...'}
                </div>
                <div style={{ fontSize: 12, textAlign: 'center', maxWidth: 220 }}>
                  {isDemo
                    ? 'Set VIDEO_SOURCE in .env to connect a camera or video file'
                    : 'Waiting for backend connection...'}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Queue History Chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Queue History</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Last 60 readings</span>
          </div>
          {queueHistory?.length > 0 ? (
            <div className="chart-wrapper">
              <ResponsiveContainer>
                <AreaChart data={queueHistory} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                  <defs>
                    <linearGradient id="queueGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#475569' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#475569' }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#94a3b8' }}
                    itemStyle={{ color: '#6366f1' }}
                  />
                  <Area type="monotone" dataKey="queue" stroke="#6366f1" strokeWidth={2}
                    fill="url(#queueGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: 40 }}>
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Collecting data...</div>
            </div>
          )}
        </div>
      </div>

      {/* Zone quick summary */}
      {data?.zone_stats && Object.keys(data.zone_stats).length > 0 && (
        <div style={{ marginTop: 20 }}>
          <div className="card-title" style={{ marginBottom: 12 }}>Zone Quick View</div>
          <div className="zone-grid">
            {Object.values(data.zone_stats).map(z => (
              <div key={z.zone_id} className={`zone-card ${z.congestion_status === 'CRITICAL' ? 'congested' : z.congestion_status === 'HIGH' ? 'warning' : ''}`}>
                <div className="zone-header">
                  <span className="zone-name">{z.zone_name}</span>
                  <span className={`congestion-badge ${z.congestion_status}`}>{z.congestion_status}</span>
                </div>
                <div className="zone-occupancy-bar">
                  <div className={`zone-occupancy-fill ${z.congestion_pct >= 75 ? 'critical' : z.congestion_pct >= 50 ? 'high' : ''}`}
                    style={{ width: `${Math.min(100, z.congestion_pct)}%` }} />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {z.current_occupancy} / {z.capacity} · Dwell: {z.avg_dwell_seconds}s avg
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data && (
        <div style={{ marginTop: 16, fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>
          Last update: {formatTime(data.timestamp)} · Frame #{data.frame_id}
        </div>
      )}
    </div>
  );
}
