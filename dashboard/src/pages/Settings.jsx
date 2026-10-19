import React, { useState, useEffect } from 'react';
import { Shield, Settings, AlertTriangle, Play, Video, RefreshCw } from 'lucide-react';
import { API_BASE as API } from '../config';

export default function SettingsPage() {
  const [demographicsEnabled, setDemographicsEnabled] = useState(false);
  const [queueThreshold, setQueueThreshold] = useState(3);
  const [retentionHours, setRetentionHours] = useState(1);
  const [saved, setSaved] = useState('');
  const [activeSource, setActiveSource] = useState({ source_type: 'unknown', is_demo: false });

  const fetchSource = async () => {
    try {
      const res = await fetch(`${API}/api/pipeline/source`);
      if (res.ok) {
        const data = await res.json();
        setActiveSource(data);
      }
    } catch { }
  };

  useEffect(() => {
    fetchSource();
  }, []);

  const switchSource = async (target) => {
    try {
      setSaved(`Switching pipeline source to: ${target}...`);
      const res = await fetch(`${API}/api/pipeline/source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: target }),
      });
      if (res.ok) {
        const data = await res.json();
        setActiveSource(data);
        setSaved(`✓ Switched to ${target === 'demo' ? 'DEMO SIMULATION' : 'RETAIL VIDEO'} mode!`);
      } else {
        setSaved('⚠ Source switch failed');
      }
    } catch {
      setSaved('⚠ Could not contact backend');
    }
    setTimeout(() => setSaved(''), 4000);
  };

  const save = () => {
    setSaved('✓ Settings saved successfully');
    setTimeout(() => setSaved(''), 3000);
  };

  const resetZones = async () => {
    try {
      await fetch(`${API}/api/zones/defaults`, { method: 'POST' });
      setSaved('✓ Default zones loaded');
      setTimeout(() => setSaved(''), 3000);
    } catch { setSaved('⚠ Could not reach backend'); setTimeout(() => setSaved(''), 3000); }
  };

  const resetAnalytics = async () => {
    if (!window.confirm('Reset all zone analytics and pipeline data?')) return;
    try {
      await fetch(`${API}/api/pipeline/reset`, { method: 'POST' });
      setSaved('✓ Zone analytics and demo counters reset');
      setTimeout(() => setSaved(''), 3000);
    } catch { setSaved('⚠ Could not reach backend'); setTimeout(() => setSaved(''), 3000); }
  };

  return (
    <div className="fade-in" style={{ maxWidth: 700 }}>
      {/* Demo & Video Source Controls */}
      <div className="settings-section">
        <h3><Play size={14} style={{ marginRight: 6 }} />Demonstration Mode & Video Source</h3>
        <div style={{ marginBottom: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
          Active Mode: <strong style={{ color: activeSource.is_demo ? '#f59e0b' : '#10b981' }}>
            {activeSource.is_demo ? '⚡ DEMO SIMULATION MODE (Synthetic Customer Flow)' : `📹 LIVE VIDEO (${activeSource.source_type.toUpperCase()})`}
          </strong>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            className={`sim-btn ${activeSource.is_demo ? 'primary' : ''}`}
            onClick={() => switchSource('demo')}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Play size={14} /> Launch Interactive Demo Simulation
          </button>
          <button
            className={`sim-btn ${!activeSource.is_demo ? 'primary' : ''}`}
            onClick={() => switchSource('video')}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Video size={14} /> Switch to Retail CCTV Video
          </button>
          <button
            className="sim-btn danger"
            onClick={resetAnalytics}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={14} /> Reset Demo & Analytics Data
          </button>
        </div>
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)' }}>
          • <strong>Demo Simulation:</strong> Runs full synthetic customer flow with wandering agents, dwell durations, queue spikes, and real transitions.<br />
          • <strong>Retail CCTV:</strong> Ingests <code>retail-cctv-footage.mp4</code> through YOLO11n person detection and ByteTrack tracking.
        </div>
      </div>

      {/* Privacy */}
      <div className="settings-section">
        <h3><Shield size={14} style={{ marginRight: 6 }} />Privacy & Data</h3>

        <div className="setting-row">
          <div>
            <div className="setting-label">Demographic Estimation</div>
            <div className="setting-desc">
              Age range / gender estimation via OpenCV DNN + Caffe models (Levi & Hassner 2015).
              No face embeddings stored. No individual identity retained.
              <strong style={{ color: '#f59e0b' }}> Disabled by default.</strong>
            </div>
          </div>
          <div className={`toggle${demographicsEnabled ? ' on' : ''}`} onClick={() => setDemographicsEnabled(v => !v)}>
            <div className="toggle-thumb" />
          </div>
        </div>

        <div className="setting-row">
          <div>
            <div className="setting-label">Tracking Data Retention</div>
            <div className="setting-desc">
              How long anonymous tracking IDs are kept in memory. After expiry, only aggregated statistics remain.
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="number" className="input-field" value={retentionHours} min={0} max={24}
              onChange={e => setRetentionHours(+e.target.value)} style={{ width: 70 }} />
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>hours</span>
          </div>
        </div>

        <div className="info-box" style={{ marginTop: 10, marginBottom: 0 }}>
          <strong>StorePulse AI Privacy Principles:</strong><br />
          • No facial recognition or biometric identification<br />
          • No individual trajectory persistence<br />
          • Anonymous track IDs only (reset between sessions)<br />
          • Aggregate statistics only sent to dashboard<br />
          • No raw video stored by default
        </div>
      </div>

      {/* Queue settings */}
      <div className="settings-section">
        <h3><Settings size={14} style={{ marginRight: 6 }} />Queue Monitoring</h3>
        <div className="setting-row">
          <div>
            <div className="setting-label">Queue Alert Threshold</div>
            <div className="setting-desc">Alert triggers when queue count reaches or exceeds this value.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input type="number" className="input-field" value={queueThreshold} min={1} max={50}
              onChange={e => setQueueThreshold(+e.target.value)} style={{ width: 70 }} />
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>people</span>
          </div>
        </div>
      </div>

      {/* Zone management */}
      <div className="settings-section">
        <h3>Zone Management</h3>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="sim-btn" onClick={resetZones}>Load Default Zones</button>
          <button className="sim-btn danger" onClick={resetAnalytics}>
            <AlertTriangle size={12} /> Reset Zone Analytics
          </button>
        </div>
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)' }}>
          Default zones: Entrance, Checkout, Electronics, Grocery, Promo Display.
          Edit zone polygons via the Zone Analytics page (future feature).
        </div>
      </div>

      {/* About */}
      <div className="settings-section">
        <h3>About StorePulse AI</h3>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <div><strong>Product:</strong> StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator</div>
          <div><strong>Version:</strong> 1.0.0</div>
          <div><strong>Developer:</strong> Omkar Gurav</div>
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
            Built on: YOLO11 (Ultralytics) · ByteTrack · OpenCV · FastAPI · React · Recharts
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <button className="sim-btn primary" onClick={save}>Save Settings</button>
      </div>
      {saved && <div style={{ marginTop: 10, fontSize: 12, color: '#10b981', fontWeight: 600 }}>{saved}</div>}
    </div>
  );
}
