// pages/LiveAnalytics.jsx — StorePulse AI
// Author: Omkar Gurav
import React, { useState } from 'react';
import { Camera, AlertTriangle } from 'lucide-react';
import { StatCard } from '../components/StatCard';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Users, LogIn, LogOut, Activity, Zap } from 'lucide-react';
import { API_BASE } from '../config';

const STREAM_URL = `${API_BASE}/snapshot`;

export default function LiveAnalytics({ data, queueHistory }) {
  const [showFeed, setShowFeed] = useState(true);

  // Build chart data from queue history + tracked count
  const chartData = (queueHistory || []).map((q, i) => ({
    i,
    queue: q.queue,
    label: q.label,
  }));

  return (
    <div className="fade-in">
      {data?.queue_alert && (
        <div className="alert-banner">
          <AlertTriangle size={18} />
          <span><strong>QUEUE ALERT!</strong> {data.queue_count} people in checkout zone.</span>
        </div>
      )}

      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', marginBottom: 20 }}>
        <StatCard title="Total IN" value={data?.count_in ?? '—'} icon={LogIn} />
        <StatCard title="Total OUT" value={data?.count_out ?? '—'} icon={LogOut} />
        <StatCard title="Occupancy" value={data?.occupancy ?? '—'} icon={Users} />
        <StatCard title="Queue" value={data?.queue_count ?? '—'} icon={Activity} alert={data?.queue_alert} />
        <StatCard title="FPS" value={data?.fps?.toFixed(1) ?? '—'} icon={Zap} />
      </div>

      <div className="grid-2">
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="card-title" style={{ margin: 0 }}>Camera Stream</span>
            {data?.is_demo && <span className="demo-badge">DEMO</span>}
            <button
              onClick={() => setShowFeed(f => !f)}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>
              {showFeed ? 'Hide' : 'Show'} Feed
            </button>
          </div>
          {showFeed ? (
            <div className="live-feed">
              <img
                src={STREAM_URL}
                alt="Live Camera Stream"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                onError={e => {
                  console.warn('[Feed] LiveAnalytics stream disconnected');
                  e.target.style.display = 'none';
                  const fb = document.getElementById('live-feed-placeholder');
                  if (fb) fb.style.display = 'flex';
                }}
              />
              <div id="live-feed-placeholder" className="feed-placeholder" style={{ display: 'none' }}>
                <Camera size={40} style={{ opacity: 0.2 }} />
                <div>Stream Connecting...</div>
              </div>
              <div className="live-feed-overlay">
                <span className="live-dot" style={{ background: data?.is_demo ? '#f59e0b' : '#10b981' }} />
                {data?.is_demo ? 'DEMO SIMULATION' : 'LIVE CAMERA'}
              </div>
            </div>
          ) : (
            <div style={{ padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>Feed hidden</div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Queue Trend</span>
          </div>
          <div className="chart-wrapper-lg">
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#475569' }} />
                <YAxis tick={{ fontSize: 10, fill: '#475569' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Line type="monotone" dataKey="queue" stroke="#6366f1" strokeWidth={2} dot={false} name="Queue" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Demographics */}
      {data?.demographics?.enabled && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="card-header">
            <span className="card-title">Demographics</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {data.demographics.sample_count} samples · Privacy: age/gender only, no identity
            </span>
          </div>
          <div className="grid-2">
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Gender Distribution</div>
              {Object.entries(data.demographics.gender_distribution || {}).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 12, width: 60, color: 'var(--text-secondary)' }}>{k}</span>
                  <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${v}%`, background: 'linear-gradient(90deg,#6366f1,#8b5cf6)', borderRadius: 3, transition: 'width 0.4s' }} />
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', width: 40 }}>{v?.toFixed(0)}%</span>
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Age Distribution</div>
              {Object.entries(data.demographics.age_distribution || {}).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 12, width: 60, color: 'var(--text-secondary)' }}>{k}</span>
                  <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${v}%`, background: 'linear-gradient(90deg,#06b6d4,#6366f1)', borderRadius: 3, transition: 'width 0.4s' }} />
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', width: 40 }}>{v?.toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
