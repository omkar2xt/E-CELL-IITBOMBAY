// pages/ScenarioComparison.jsx — StorePulse AI
// Baseline vs. Proposed layout comparison
// Developer: Omkar Gurav
import React, { useState, useEffect } from 'react';
import { BarChart3, RefreshCw, Info, Play } from 'lucide-react';
import { API_BASE as API } from '../config';

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
          {/* Empirical Transition Data Banner */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10,
            padding: '10px 16px', marginBottom: 20, borderRadius: 8,
            background: result.used_empirical_transitions ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
            border: `1px solid ${result.used_empirical_transitions ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: result.used_empirical_transitions ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
              <BarChart3 size={16} />
              <span>
                {result.used_empirical_transitions
                  ? `Empirical Zone Transitions Applied: ${result.transition_summary?.total_transitions} recorded events (${result.transition_summary?.routes_count} active routes, Confidence: ${result.transition_summary?.confidence})`
                  : 'Heuristic Baseline Weights: Insufficient live visitor transition data (< 5 events). Using category prior demand distribution.'}
              </span>
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Model: <strong>{result.model}</strong>
            </span>
          </div>

          {/* Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Baseline Scenario</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                {result.baseline?.layout_name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 2 }}>
                Space utilization: <strong style={{ color: 'var(--text-primary)' }}>{result.baseline?.metrics.space_utilization_pct}%</strong><br />
                Layout elements: <strong style={{ color: 'var(--text-primary)' }}>{result.baseline?.metrics.element_count}</strong><br />
                Avg walking distance: <strong style={{ color: 'var(--text-primary)' }}>{result.baseline?.metrics.avg_weighted_walking_distance} px</strong><br />
                Route conflict score: <strong style={{ color: 'var(--text-primary)' }}>{result.baseline?.metrics.route_conflict_score}</strong><br />
                Bottleneck Risk Index: <strong style={{ color: (result.baseline?.metrics.bottleneck_risk_index || 0) > 40 ? '#ef4444' : '#10b981' }}>
                  {result.baseline?.metrics.bottleneck_risk_index ?? '—'}/100
                </strong>
              </div>
            </div>
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>Proposed Scenario (Simulated)</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
                {result.proposed?.layout_name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 2 }}>
                Space utilization: <strong style={{ color: 'var(--text-primary)' }}>{result.proposed?.metrics.space_utilization_pct}%</strong><br />
                Layout elements: <strong style={{ color: 'var(--text-primary)' }}>{result.proposed?.metrics.element_count}</strong><br />
                Avg walking distance: <strong style={{ color: 'var(--text-primary)' }}>{result.proposed?.metrics.avg_weighted_walking_distance} px</strong><br />
                Route conflict score: <strong style={{ color: 'var(--text-primary)' }}>{result.proposed?.metrics.route_conflict_score}</strong><br />
                Bottleneck Risk Index: <strong style={{ color: (result.proposed?.metrics.bottleneck_risk_index || 0) > 40 ? '#ef4444' : '#10b981' }}>
                  {result.proposed?.metrics.bottleneck_risk_index ?? '—'}/100
                </strong>
              </div>
            </div>
          </div>

          {/* Zone-by-Zone Congestion & Dwell Risk Cards */}
          {result.zone_comparisons && result.zone_comparisons.length > 0 && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-header">
                <div>
                  <span className="card-title">Zone-by-Zone Congestion & Dwell Impact</span>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    Heuristic estimates of walkable aisle clearance, congestion classification, and expected dwell alteration
                  </div>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                {result.zone_comparisons.map(z => {
                  const riskColors = {
                    LOW: '#10b981',
                    MEDIUM: '#f59e0b',
                    HIGH: '#f97316',
                    CRITICAL: '#ef4444',
                  };
                  return (
                    <div key={z.zone_id} style={{
                      padding: 12, borderRadius: 8,
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex', flexDirection: 'column', gap: 6,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                          {z.zone_name}
                        </span>
                        <DirectionBadge dir={z.risk_change} />
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)' }}>
                        <span>Aisle Clearance:</span>
                        <span>
                          {z.baseline_clearance_pct}% → <strong>{z.proposed_clearance_pct}%</strong>
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Predicted Risk:</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ color: 'var(--text-muted)' }}>{z.baseline_risk}</span>
                          <span style={{ color: 'var(--text-muted)' }}>→</span>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
                            background: `${riskColors[z.proposed_risk] || '#94a3b8'}22`,
                            color: riskColors[z.proposed_risk] || '#94a3b8',
                            border: `1px solid ${riskColors[z.proposed_risk] || '#94a3b8'}44`,
                          }}>
                            {z.proposed_risk}
                          </span>
                        </div>
                      </div>

                      <div style={{
                        marginTop: 4, padding: '6px 8px', borderRadius: 6,
                        background: 'rgba(0,0,0,0.2)', fontSize: 11,
                        color: z.risk_change === 'WORSE' ? '#fca5a5' : z.risk_change === 'BETTER' ? '#a7f3d0' : 'var(--text-muted)',
                        lineHeight: 1.4,
                      }}>
                        {z.estimated_dwell_impact}
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                        <span>Confidence: {z.confidence}</span>
                        <span style={{ fontStyle: 'italic' }}>Heuristic Estimate</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Comparison table */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Metric Comparison Report</span>
              <span style={{ fontSize: 11, color: 'var(--brand-warning)' }}>
                [HEURISTIC ESTIMATE] vs [OBSERVED REAL]
              </span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Baseline</th>
                    <th>Proposed (Estimated)</th>
                    <th>Absolute Change</th>
                    <th>% Change</th>
                    <th>Direction</th>
                    <th>Data Source</th>
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
                      <td style={{ color: row.pct_diff?.includes('N/A') ? 'var(--text-muted)' : 'var(--text-secondary)' }}>
                        {row.pct_diff}
                      </td>
                      <td><DirectionBadge dir={row.direction} /></td>
                      <td>
                        <span style={{
                          fontSize: 10, padding: '2px 6px', borderRadius: 4,
                          background: row.source === 'real_measurement' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.1)',
                          color: row.source === 'real_measurement' ? '#10b981' : '#f59e0b',
                        }}>
                          {row.source === 'real_measurement' ? 'Measured Real' : 'Estimate'}
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
            <div className="card-title" style={{ marginBottom: 8 }}>Model Assumptions & Constraints</div>
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
