// pages/AlertLogs.jsx — StorePulse AI
// Developer: Omkar Gurav
// Alert Evidence & Event Management System with High-Resolution Snapshot Modal

import React, { useState, useEffect, useCallback } from 'react';
import {
  Bell, AlertTriangle, CheckCircle, ShieldAlert, Clock,
  Filter, Eye, Check, X, RefreshCw, Trash2, Camera, Database,
  ExternalLink, ChevronRight, Layers, Sparkles
} from 'lucide-react';
import { API_BASE, WS_URL } from '../config';

const SEVERITY_COLORS = {
  CRITICAL: { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', text: '#f87171' },
  HIGH:     { bg: 'rgba(249, 115, 22, 0.15)', border: '#f97316', text: '#fb923c' },
  MEDIUM:   { bg: 'rgba(234, 179, 8, 0.15)', border: '#eab308', text: '#fde047' },
  LOW:      { bg: 'rgba(59, 130, 246, 0.15)', border: '#3b82f6', text: '#60a5fa' },
};

export default function AlertLogs({ wsStatus }) {
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [activeTab, setActiveTab] = useState('all'); // all, active, critical, with_evidence
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [filterType, setFilterType] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterMode, setFilterMode] = useState('ALL');
  const [updatingId, setUpdatingId] = useState(null);

  // Fetch summary metrics
  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/alerts/summary?hours=24`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (e) {
      console.warn('[AlertLogs] Failed to fetch summary:', e);
    }
  }, []);

  // Fetch alerts list
  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      let url = `${API_BASE}/api/alerts?limit=50`;
      if (filterSeverity !== 'ALL') url += `&severity=${filterSeverity}`;
      if (filterType !== 'ALL') url += `&alert_type=${filterType}`;
      if (filterStatus !== 'ALL') url += `&status=${filterStatus}`;
      if (filterMode !== 'ALL') url += `&source_mode=${filterMode}`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch (e) {
      console.error('[AlertLogs] Error fetching alerts:', e);
    } finally {
      setLoading(false);
    }
  }, [filterSeverity, filterType, filterStatus, filterMode]);

  useEffect(() => {
    fetchAlerts();
    fetchSummary();
  }, [fetchAlerts, fetchSummary]);

  // Listen to WebSocket for real-time alert events
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'alert_triggered') {
          setAlerts(prev => [msg.alert, ...prev.filter(a => a.id !== msg.alert.id)]);
          fetchSummary();
        } else if (msg.type === 'alert_snapshot_ready') {
          setAlerts(prev => prev.map(a => {
            if (a.id === msg.alert_id) {
              return {
                ...a,
                snapshot_status: msg.snapshot.status,
                snapshots: [msg.snapshot]
              };
            }
            return a;
          }));
          if (selectedAlert && selectedAlert.id === msg.alert_id) {
            setSelectedAlert(prev => ({
              ...prev,
              snapshot_status: msg.snapshot.status,
              snapshots: [msg.snapshot]
            }));
          }
          fetchSummary();
        } else if (msg.type === 'alert_status_updated' || msg.type === 'alert_resolved') {
          setAlerts(prev => prev.map(a => {
            if (a.id === msg.alert_id) {
              return { ...a, status: msg.new_status || 'resolved' };
            }
            return a;
          }));
          fetchSummary();
        }
      } catch (e) {}
    };
    return () => ws.close();
  }, [fetchSummary, selectedAlert]);

  // Update alert status action
  const handleUpdateStatus = async (alertId, newStatus, reason = "Dashboard operator action") => {
    try {
      setUpdatingId(alertId);
      const res = await fetch(`${API_BASE}/api/alerts/${alertId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, reason })
      });
      if (res.ok) {
        const updated = await res.json();
        setAlerts(prev => prev.map(a => a.id === alertId ? updated : a));
        if (selectedAlert && selectedAlert.id === alertId) {
          setSelectedAlert(updated);
        }
        fetchSummary();
      }
    } catch (e) {
      console.error('[AlertLogs] Failed to update status:', e);
    } finally {
      setUpdatingId(null);
    }
  };

  // Retention cleanup action
  const handleCleanup = async () => {
    if (!window.confirm("Purge alerts and snapshots older than 30 days?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/alerts/cleanup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ retention_days: 30 })
      });
      if (res.ok) {
        const resData = await res.json();
        alert(`Retention cleanup complete: ${resData.deleted_alerts} alerts and ${resData.deleted_snapshots} snapshots purged.`);
        fetchAlerts();
        fetchSummary();
      }
    } catch (e) {
      alert("Cleanup failed: " + e.message);
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return '—';
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + 
           ' (' + date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ')';
  };

  return (
    <div className="page-container animate-fade-in">
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            Alert Evidence & Event Management
          </h1>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
            Real-time threshold violations, queue spikes, and persistent computer vision evidence
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={() => { fetchAlerts(); fetchSummary(); }}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px' }}>
            <RefreshCw size={15} /> Refresh
          </button>
          <button
            onClick={handleCleanup}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', color: '#f87171' }}>
            <Trash2 size={15} /> Purge Retention
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid-auto" style={{ marginBottom: 20 }}>
          <div className="stat-card">
            <div className="stat-label">Active Alerts</div>
            <div className="stat-value" style={{ color: summary.active_alerts > 0 ? '#ef4444' : '#10b981' }}>
              {summary.active_alerts}
            </div>
            <div className="stat-sub">Require staff intervention</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Critical Severity (24h)</div>
            <div className="stat-value" style={{ color: '#f87171' }}>
              {summary.by_severity?.CRITICAL || 0}
            </div>
            <div className="stat-sub">Severe queue / congestion</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Total Events (24h)</div>
            <div className="stat-value" style={{ color: 'var(--brand-accent)' }}>
              {summary.total_alerts}
            </div>
            <div className="stat-sub">Tracked across all zones</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Evidence Storage</div>
            <div className="stat-value" style={{ color: '#38bdf8' }}>
              {summary.storage?.total_snapshots || 0}
            </div>
            <div className="stat-sub">{summary.storage?.total_size_mb || 0} MB captured on disk</div>
          </div>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="card" style={{ padding: '14px 18px', marginBottom: 20 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: 13, fontWeight: 600 }}>
            <Filter size={16} /> Filters:
          </div>

          {/* Severity Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Severity:</span>
            <select
              value={filterSeverity}
              onChange={e => setFilterSeverity(e.target.value)}
              className="select-input"
              style={{ padding: '5px 10px', fontSize: 12 }}>
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Status:</span>
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              className="select-input"
              style={{ padding: '5px 10px', fontSize: 12 }}>
              <option value="ALL">All Statuses</option>
              <option value="active">Active</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </select>
          </div>

          {/* Alert Type Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Type:</span>
            <select
              value={filterType}
              onChange={e => setFilterType(e.target.value)}
              className="select-input"
              style={{ padding: '5px 10px', fontSize: 12 }}>
              <option value="ALL">All Event Types</option>
              <option value="queue_threshold_exceeded">Queue Threshold</option>
              <option value="bottleneck_detected">Bottleneck Detected</option>
              <option value="excessive_dwell_time">Excessive Dwell</option>
              <option value="zone_capacity_exceeded">Capacity Exceeded</option>
            </select>
          </div>

          {/* Source Mode Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Source:</span>
            <select
              value={filterMode}
              onChange={e => setFilterMode(e.target.value)}
              className="select-input"
              style={{ padding: '5px 10px', fontSize: 12 }}>
              <option value="ALL">All Sources</option>
              <option value="live">Live Camera</option>
              <option value="demo">Demo Simulation</option>
            </select>
          </div>

          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
            Showing {alerts.length} events
          </div>
        </div>
      </div>

      {/* Alerts Table / List */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div className="empty-state" style={{ padding: 60 }}>
            <div className="loading-spinner" />
            <div style={{ marginTop: 14, color: 'var(--text-muted)' }}>Loading alert history...</div>
          </div>
        ) : alerts.length === 0 ? (
          <div className="empty-state" style={{ padding: 60 }}>
            <CheckCircle size={44} style={{ color: '#10b981', opacity: 0.8 }} />
            <div style={{ fontSize: 16, fontWeight: 600, marginTop: 12, color: 'var(--text-primary)' }}>
              No Alerts Triggered
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4, maxWidth: 360, textAlign: 'center' }}>
              All retail zones and queues are currently operating within nominal parameters.
            </div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>EVIDENCE</th>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>SEVERITY</th>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>ALERT TYPE</th>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>ZONE</th>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>METRIC / THRESHOLD</th>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>TIMESTAMP</th>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>STATUS</th>
                  <th style={{ padding: '12px 16px', fontSize: 11, color: 'var(--text-muted)' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map(a => {
                  const sevStyle = SEVERITY_COLORS[a.severity] || SEVERITY_COLORS.MEDIUM;
                  const hasSnap = a.snapshot_status === 'saved';

                  return (
                    <tr
                      key={a.id}
                      style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.15s' }}
                      className="table-row-hover">
                      {/* Evidence Thumbnail */}
                      <td style={{ padding: '10px 16px', width: 90 }}>
                        {hasSnap ? (
                          <div
                            onClick={() => setSelectedAlert(a)}
                            style={{
                              width: 72,
                              height: 44,
                              borderRadius: 6,
                              overflow: 'hidden',
                              cursor: 'pointer',
                              position: 'relative',
                              border: '1px solid var(--border-subtle)',
                              background: '#000'
                            }}>
                            <img
                              src={`${API_BASE}/api/alerts/${a.id}/snapshot?thumb=true`}
                              alt="Evidence thumbnail"
                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                            <div style={{
                              position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.3)',
                              display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                              <Eye size={14} color="white" />
                            </div>
                          </div>
                        ) : a.snapshot_status === 'pending' ? (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Processing...</div>
                        ) : (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', opacity: 0.5 }}>No image</div>
                        )}
                      </td>

                      {/* Severity Pill */}
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '3px 8px',
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          background: sevStyle.bg,
                          color: sevStyle.text,
                          border: `1px solid ${sevStyle.border}`
                        }}>
                          {a.severity}
                        </span>
                      </td>

                      {/* Alert Type */}
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                          {a.alert_type.replace(/_/g, ' ').toUpperCase()}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, maxWidth: 260 }}>
                          {a.message}
                        </div>
                      </td>

                      {/* Zone & Mode */}
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)' }}>
                            {a.zone_id ? a.zone_id.toUpperCase() : 'STOREWIDE'}
                          </span>
                          <span style={{
                            fontSize: 10,
                            padding: '2px 6px',
                            borderRadius: 4,
                            width: 'fit-content',
                            background: a.source_mode === 'demo' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                            color: a.source_mode === 'demo' ? '#f59e0b' : '#10b981',
                            fontWeight: 600
                          }}>
                            {a.source_mode === 'demo' ? 'DEMO DATA' : 'LIVE CCTV'}
                          </span>
                        </div>
                      </td>

                      {/* Metric / Threshold */}
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                          {a.metric_name}: <span style={{ color: '#ef4444' }}>{a.metric_value}</span>
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                          Threshold: {a.threshold_value}
                        </div>
                      </td>

                      {/* Timestamp */}
                      <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {formatTimestamp(a.triggered_at)}
                      </td>

                      {/* Status */}
                      <td style={{ padding: '12px 16px' }}>
                        <span className={`status-pill ${a.status === 'active' ? 'congested' : a.status === 'resolved' ? 'connected' : 'warning'}`}
                          style={{ fontSize: 11 }}>
                          <span className="status-dot" />
                          {a.status.toUpperCase()}
                        </span>
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', gap: 6 }}>
                          {hasSnap && (
                            <button
                              onClick={() => setSelectedAlert(a)}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: 11 }}
                              title="Inspect Snapshot Evidence">
                              <Eye size={13} /> View
                            </button>
                          )}

                          {a.status === 'active' && (
                            <button
                              disabled={updatingId === a.id}
                              onClick={() => handleUpdateStatus(a.id, 'acknowledged')}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: 11, color: '#38bdf8' }}
                              title="Acknowledge Alert">
                              Ack
                            </button>
                          )}

                          {a.status !== 'resolved' && (
                            <button
                              disabled={updatingId === a.id}
                              onClick={() => handleUpdateStatus(a.id, 'resolved')}
                              className="btn btn-secondary"
                              style={{ padding: '5px 10px', fontSize: 11, color: '#10b981' }}
                              title="Mark Resolved">
                              <Check size={13} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* High-Resolution Evidence Modal */}
      {selectedAlert && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20
        }}>
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 16,
            width: '100%',
            maxWidth: 960,
            maxHeight: '92vh',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 25px 50px -12px rgba(0,0,0,0.7)'
          }}>
            {/* Modal Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                  background: SEVERITY_COLORS[selectedAlert.severity]?.bg,
                  color: SEVERITY_COLORS[selectedAlert.severity]?.text,
                  border: `1px solid ${SEVERITY_COLORS[selectedAlert.severity]?.border}`
                }}>
                  {selectedAlert.severity}
                </span>
                <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
                  {selectedAlert.alert_type.replace(/_/g, ' ').toUpperCase()} EVIDENCE
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  ID: {selectedAlert.id.slice(0, 8)}...
                </span>
              </div>

              <button
                onClick={() => setSelectedAlert(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }}>
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Full Image Display */}
              <div style={{
                position: 'relative',
                borderRadius: 12,
                overflow: 'hidden',
                background: '#000',
                border: '1px solid var(--border-subtle)',
                minHeight: 380,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <img
                  src={`${API_BASE}/api/alerts/${selectedAlert.id}/snapshot`}
                  alt="High-resolution alert evidence"
                  style={{ width: '100%', maxHeight: 460, objectFit: 'contain' }}
                  onError={e => {
                    e.target.style.display = 'none';
                    const ph = document.getElementById('modal-img-error');
                    if (ph) ph.style.display = 'flex';
                  }}
                />
                <div id="modal-img-error" style={{ display: 'none', flexDirection: 'column', alignItems: 'center', gap: 8, padding: 30 }}>
                  <Camera size={36} color="#64748b" />
                  <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Snapshot image not available</span>
                </div>
                <div style={{
                  position: 'absolute', bottom: 10, right: 10,
                  background: 'rgba(0,0,0,0.7)', padding: '4px 10px', borderRadius: 6,
                  fontSize: 11, color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)'
                }}>
                  Captured at {formatTimestamp(selectedAlert.triggered_at)}
                </div>
              </div>

              {/* Operational Recommendation Banner */}
              {selectedAlert.metadata?.recommendation && (
                <div style={{
                  padding: '12px 16px', borderRadius: 10,
                  background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)',
                  display: 'flex', alignItems: 'center', gap: 10
                }}>
                  <Sparkles size={18} color="#38bdf8" />
                  <div style={{ fontSize: 13, color: '#e0f2fe' }}>
                    <strong>Action Recommended:</strong> {selectedAlert.metadata.recommendation}
                  </div>
                </div>
              )}

              {/* Detailed Metadata Grid */}
              <div className="grid-2">
                <div style={{ background: 'var(--bg-base)', padding: 14, borderRadius: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                    Event Telemetry
                  </div>
                  <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div><strong>Zone:</strong> {selectedAlert.zone_id || 'Storewide'}</div>
                    <div><strong>Metric:</strong> {selectedAlert.metric_name} = <span style={{ color: '#ef4444' }}>{selectedAlert.metric_value}</span></div>
                    <div><strong>Configured Threshold:</strong> {selectedAlert.threshold_value}</div>
                    <div><strong>Source Mode:</strong> {selectedAlert.source_mode === 'demo' ? 'Synthetic Demo Flow' : 'Real CCTV Video'}</div>
                    <div><strong>Fingerprint:</strong> <code>{selectedAlert.fingerprint}</code></div>
                  </div>
                </div>

                <div style={{ background: 'var(--bg-base)', padding: 14, borderRadius: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                    Evidence Integrity & Storage
                  </div>
                  <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div><strong>Capture Status:</strong> {selectedAlert.snapshot_status.toUpperCase()}</div>
                    {selectedAlert.snapshots?.[0] && (
                      <>
                        <div><strong>File Size:</strong> {(selectedAlert.snapshots[0].file_size_bytes / 1024).toFixed(1)} KB</div>
                        <div><strong>Resolution:</strong> {selectedAlert.snapshots[0].image_width} × {selectedAlert.snapshots[0].image_height} px</div>
                        <div><strong>SHA-256 Checksum:</strong> <span style={{ fontSize: 10, color: '#94a3b8' }}>{selectedAlert.snapshots[0].checksum?.slice(0, 24)}...</span></div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer / Status Management */}
            <div style={{
              padding: '14px 20px',
              borderTop: '1px solid var(--border-subtle)',
              background: 'rgba(0,0,0,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Current Status: <strong style={{ color: 'var(--text-primary)' }}>{selectedAlert.status.toUpperCase()}</strong>
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  disabled={updatingId === selectedAlert.id}
                  onClick={() => handleUpdateStatus(selectedAlert.id, 'acknowledged')}
                  className="btn btn-secondary"
                  style={{ fontSize: 12 }}>
                  Acknowledge
                </button>
                <button
                  disabled={updatingId === selectedAlert.id}
                  onClick={() => handleUpdateStatus(selectedAlert.id, 'resolved')}
                  className="btn btn-primary"
                  style={{ fontSize: 12 }}>
                  Mark Resolved
                </button>
                <button
                  disabled={updatingId === selectedAlert.id}
                  onClick={() => handleUpdateStatus(selectedAlert.id, 'dismissed')}
                  className="btn btn-secondary"
                  style={{ fontSize: 12, color: '#94a3b8' }}>
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
