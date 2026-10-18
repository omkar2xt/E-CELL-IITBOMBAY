// pages/ScenarioComparison.jsx — StorePulse AI
// Baseline vs. Proposed layout comparison
// Developer: Omkar Gurav
import React, { useState, useEffect } from 'react';
import { BarChart3, RefreshCw, Info, Play } from 'lucide-react';

const API = 'http://localhost:8000';

function DirectionBadge({ dir }) {
  const cls = { BETTER: 'BETTER', WORSE: 'WORSE', SAME: 'SAME', 'N/A': 'NA' };
  const icons = { BETTER: '▲', WORSE: '▼', SAME: '—', 'N/A': '?' };
  return (
    <span className={`dir-badge ${cls[dir] || 'NA'}`}>
      {icons[dir] || '?'} {dir}
    </span>
  );
}

export default function ScenarioComparison() {
  const [layouts, setLayouts] = useState([]);
  const [baselineId, setBaselineId] = useState('baseline');
  const [proposedId, setProposedId] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchLayouts();
  }, []);

  const fetchLayouts = async () => {
    try {
      const res = await fetch(`${API}/api/layouts/`);
      const json = await res.json();
      const all = json.layouts || [];
      setLayouts(all);
      const proposed = all.find(l => !l.is_baseline);
      if (proposed) setProposedId(proposed.id);
      const base = all.find(l => l.is_baseline);
      if (base) setBaselineId(base.id);
    } catch { }
  };

  const runSimulation = async () => {
    if (!baselineId || !proposedId) {
      setError('Select both a baseline and a proposed layout');
      return;
    }
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await fetch(`${API}/api/layouts/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseline_id: baselineId, proposed_id: proposedId }),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || 'Simulation failed');
      } else {
        const json = await res.json();
        setResult(json);
      }
    } catch {
      setError('Cannot reach backend. Is the server running?');
    } finally { setLoading(false); }
  };

  return (
    <div className="fade-in">
      <div className="disclaimer-box">
        <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          <strong>Heuristic estimates only.</strong> All comparison values are calculated from geometric layout analysis,
          not validated customer behavior prediction. Each metric shows data source and confidence level.
          Where real measurements exist, they are clearly labeled.
        </span>
      </div>

      {/* Layout selection */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Select Scenarios</span>
          <button className="sim-btn" onClick={fetchLayouts}><RefreshCw size={12} /> Refresh</button>
        </div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Baseline Layout</div>
            <select
              className="input-field"
              value={baselineId}
              onChange={e => setBaselineId(e.target.value)}
              style={{ width: 220 }}
            >
              <option value="">Select baseline...</option>
              {layouts.map(l => <option key={l.id} value={l.id}>{l.name} {l.is_baseline ? '(baseline)' : ''}</option>)}
            </select>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Proposed Layout</div>
            <select
              className="input-field"
              value={proposedId}
              onChange={e => setProposedId(e.target.value)}
              style={{ width: 220 }}
            >
              <option value="">Select proposed...</option>
              {layouts.filter(l => l.id !== baselineId).map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <button className="sim-btn primary" onClick={runSimulation} disabled={loading || !baselineId || !proposedId}>
            <Play size={13} /> {loading ? 'Simulating...' : 'Run Simulation'}
          </button>
        </div>
        {error && <div style={{ marginTop: 10, fontSize: 12, color: '#ef4444' }}>{error}</div>}
        {layouts.length === 0 && (
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)' }}>
            No layouts found. Create and save layouts in the <strong>What-If Simulator</strong> first.
          </div>
        )}
      </div>

      {result && (
        <>
          {/* Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Baseline</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                {result.baseline?.layout_name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8 }}>
                Space used: {result.baseline?.metrics.space_utilization_pct}%<br />
                Elements: {result.baseline?.metrics.element_count}<br />
                Avg walking dist: {result.baseline?.metrics.avg_weighted_walking_distance}<br />
                Conflict score: {result.baseline?.metrics.route_conflict_score}
              </div>
            </div>
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Proposed</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                {result.proposed?.layout_name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8 }}>
                Space used: {result.proposed?.metrics.space_utilization_pct}%<br />
                Elements: {result.proposed?.metrics.element_count}<br />
                Avg walking dist: {result.proposed?.metrics.avg_weighted_walking_distance}<br />
                Conflict score: {result.proposed?.metrics.route_conflict_score}
              </div>
            </div>
          </div>

          {/* Comparison table */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Comparison Report</span>
              <span style={{ fontSize: 11, color: 'var(--brand-warning)' }}>
                Source: {result.model}
              </span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Baseline</th>
                    <th>Proposed (Estimated)</th>
                    <th>Change</th>
                    <th>% Change</th>
                    <th>Direction</th>
                    <th>Source</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.comparison || []).map((row, i) => (
                    <tr key={i}>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{row.metric}</td>
                      <td>{row.baseline}</td>
                      <td>{row.proposed}</td>
                      <td style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{row.absolute_diff}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{row.pct_diff}</td>
                      <td><DirectionBadge dir={row.direction} /></td>
                      <td>
                        <span style={{
                          fontSize: 10, padding: '2px 6px', borderRadius: 4,
                          background: row.source === 'real_measurement' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.1)',
                          color: row.source === 'real_measurement' ? '#10b981' : '#f59e0b',
                        }}>
                          {row.source === 'real_measurement' ? 'Measured' : 'Estimate'}
                        </span>
                      </td>
                      <td style={{ color: row.confidence === 'HIGH' ? '#10b981' : row.confidence === 'MEDIUM' ? '#f59e0b' : '#94a3b8', fontSize: 12 }}>
                        {row.confidence}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Assumptions */}
          <div style={{ marginTop: 16 }}>
            <div className="card-title" style={{ marginBottom: 8 }}>Model Assumptions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {(result.assumptions || []).map((a, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 8 }}>
                  <span style={{ color: 'var(--brand-primary)', flexShrink: 0 }}>•</span> {a}
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
            Generated: {new Date(result.generated_at * 1000).toLocaleString()}
          </div>
        </>
      )}
    </div>
  );
}
