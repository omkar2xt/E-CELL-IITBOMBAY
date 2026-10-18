// pages/QueueMonitoring.jsx — StorePulse AI
// Developer: Omkar Gurav
import React from 'react';
import { ShoppingCart, AlertTriangle } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

const THRESHOLD = 3;

export default function QueueMonitoring({ data, queueHistory }) {
  const isAlert = data?.queue_alert;
  const count = data?.queue_count ?? 0;

  const chartData = (queueHistory || []).map((q, i) => ({
    i, queue: q.queue, label: q.label,
  }));

  return (
    <div className="fade-in">
      {isAlert && (
        <div className="alert-banner">
          <AlertTriangle size={20} />
          <div>
            <strong>QUEUE ALERT!</strong> Checkout queue has {count} people — exceeds threshold of {THRESHOLD}.
            <div style={{ fontSize: 11, marginTop: 2 }}>Recommended: Open another register immediately.</div>
          </div>
        </div>
      )}

      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)', marginBottom: 24 }}>
        <div className={`stat-card${isAlert ? ' alert' : ''}`}>
          <span className="stat-card-label">Current Queue</span>
          <div className="stat-card-value" style={{ color: isAlert ? 'var(--brand-danger)' : 'var(--text-primary)' }}>
            {count}
          </div>
          <div className="stat-card-sub">people at checkout</div>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Alert Threshold</span>
          <div className="stat-card-value">{THRESHOLD}</div>
          <div className="stat-card-sub">configurable in Settings</div>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Status</span>
          <div className="stat-card-value" style={{ fontSize: 20, paddingTop: 8 }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              color: isAlert ? 'var(--brand-danger)' : 'var(--brand-success)',
              fontSize: 14, fontWeight: 700
            }}>
              {isAlert ? '⚠ ALERT' : '✓ Normal'}
            </span>
          </div>
        </div>
      </div>

      {/* Queue bar visualization */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Queue Occupancy</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Zone: Checkout</span>
        </div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', padding: '8px 0' }}>
          <div style={{ flex: 1, height: 24, background: 'rgba(255,255,255,0.06)', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${Math.min(100, (count / Math.max(count, THRESHOLD + 2)) * 100)}%`,
              background: isAlert ? 'linear-gradient(90deg,#ef4444,#f97316)' : 'linear-gradient(90deg,#6366f1,#06b6d4)',
              borderRadius: 12,
              transition: 'width 0.5s ease',
              display: 'flex', alignItems: 'center', paddingLeft: 10,
            }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'white' }}>{count}</span>
            </div>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>
            Threshold: {THRESHOLD}
          </div>
        </div>

        {/* Queue people icons */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 16 }}>
          {Array.from({ length: Math.min(count, 20) }).map((_, i) => (
            <div key={i} style={{
              width: 28, height: 28, borderRadius: '50%',
              background: i >= THRESHOLD ? 'rgba(239,68,68,0.3)' : 'rgba(99,102,241,0.3)',
              border: `1.5px solid ${i >= THRESHOLD ? '#ef4444' : '#6366f1'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14,
            }}>
              👤
            </div>
          ))}
          {count > 20 && (
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: 'rgba(255,255,255,0.08)', border: '1.5px solid rgba(255,255,255,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, color: 'var(--text-muted)', fontWeight: 700,
            }}>+{count - 20}</div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Queue History</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Last 60 readings</span>
        </div>
        <div style={{ height: 220 }}>
          <ResponsiveContainer>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="qGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="label" tick={{ fontSize: 9, fill: '#475569' }} />
              <YAxis tick={{ fontSize: 10, fill: '#475569' }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#94a3b8' }} />
              <ReferenceLine y={THRESHOLD} stroke="#ef4444" strokeDasharray="4 4"
                label={{ value: `Alert: ${THRESHOLD}`, fill: '#ef4444', fontSize: 10, position: 'right' }} />
              <Area type="monotone" dataKey="queue" stroke="#6366f1" strokeWidth={2}
                fill="url(#qGrad)" dot={false} name="Queue Count" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
