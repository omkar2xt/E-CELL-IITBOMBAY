// pages/Settings.jsx — StorePulse AI
// Settings & Privacy configuration
// Developer: Omkar Gurav
import React, { useState } from 'react';
import { Shield, Settings, AlertTriangle } from 'lucide-react';

const API = 'http://localhost:8000';

export default function SettingsPage() {
  const [demographicsEnabled, setDemographicsEnabled] = useState(false);
  const [queueThreshold, setQueueThreshold] = useState(3);
  const [retentionHours, setRetentionHours] = useState(1);
  const [saved, setSaved] = useState('');

  const save = () => {
    // In a production system these would be sent to the backend
    setSaved('Settings saved (applies to next session)');
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
    if (!window.confirm('Reset all zone analytics data? This cannot be undone.')) return;
    try {
      await fetch(`${API}/api/zones/reset`, { method: 'POST' });
      setSaved('✓ Zone analytics reset');
      setTimeout(() => setSaved(''), 3000);
    } catch { setSaved('⚠ Could not reach backend'); setTimeout(() => setSaved(''), 3000); }
  };

  return (
    <div className="fade-in" style={{ maxWidth: 700 }}>
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
