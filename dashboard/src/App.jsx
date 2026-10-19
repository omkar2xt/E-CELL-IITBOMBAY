// App.jsx — StorePulse AI
// Product: StorePulse AI — Intelligent Retail Flow & What-If Layout Simulator
// Developer: Omkar Gurav
import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Overview from './pages/Overview';
import LiveAnalytics from './pages/LiveAnalytics';
import ZoneAnalytics from './pages/ZoneAnalytics';
import MovementFlow from './pages/MovementFlow';
import Heatmaps from './pages/Heatmaps';
import QueueMonitoring from './pages/QueueMonitoring';
import FlowFriction from './pages/FlowFriction';
import WhatIfSimulator from './pages/WhatIfSimulator';
import ScenarioComparison from './pages/ScenarioComparison';
import SettingsPage from './pages/Settings';
import AlertLogs from './pages/AlertLogs';
import { useWebSocket } from './hooks/useWebSocket';
import { useQueueHistory } from './hooks/useQueueHistory';
import { WS_URL, API_BASE } from './config';
import './index.css';

const PAGE_TITLES = {
  '/':           'Overview',
  '/live':       'Live Analytics',
  '/zones':      'Zone Analytics',
  '/movement':   'Movement Flow',
  '/heatmaps':   'Heatmaps',
  '/queue':      'Queue Monitoring',
  '/friction':   'Flow Friction',
  '/alerts':     'Alert Evidence Logs',
  '/simulator':  'What-If Simulator',
  '/comparison': 'Scenario Comparison',
  '/settings':   'Settings & Privacy',
};

function PageHeader({ path, wsStatus, data, onToggleMode }) {
  const title = Object.entries(PAGE_TITLES).find(([p]) => path === p)?.[1] || 'StorePulse AI';

  return (
    <div className="page-header">
      <h2>{title}</h2>
      <div className="header-right">
        {data && (
          <button
            onClick={onToggleMode}
            className="mode-toggle-pill"
            title="Click to toggle between Demo Simulation and CCTV Video"
            style={{
              background: data.is_demo ? 'rgba(245,158,11,0.15)' : 'rgba(99,102,241,0.15)',
              color: data.is_demo ? '#fbbf24' : '#818cf8',
              border: `1px solid ${data.is_demo ? 'rgba(245,158,11,0.35)' : 'rgba(99,102,241,0.35)'}`,
              borderRadius: '20px',
              padding: '4px 12px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}>
            {data.is_demo ? '⚡ DEMO SIMULATION' : '📹 CCTV VIDEO'}
          </button>
        )}
        {data && !data.is_demo && (
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            FPS: {data.fps?.toFixed(1) ?? '—'} · Frame #{data.frame_id}
          </span>
        )}
        <div className={`status-pill ${wsStatus}`}>
          <span className="status-dot" />
          {wsStatus === 'connected' ? 'LIVE' : wsStatus.toUpperCase()}
        </div>
      </div>
    </div>
  );
}

function AppInner() {
  const { data, status: wsStatus } = useWebSocket(WS_URL);
  const queueHistory = useQueueHistory(data?.queue_count);
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const update = () => setPath(window.location.pathname);
    window.addEventListener('popstate', update);
    return () => window.removeEventListener('popstate', update);
  }, []);

  const handleToggleMode = async () => {
    try {
      const target = data?.is_demo ? 'video' : 'demo';
      await fetch(`${API_BASE}/api/pipeline/source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: target }),
      });
    } catch (err) {
      console.error('[Pipeline] Toggle mode error', err);
    }
  };

  return (
    <div className="app-shell">
      <Sidebar wsStatus={wsStatus} queueAlert={data?.queue_alert} />
      <div className="main-area">
        <PageHeader path={path} wsStatus={wsStatus} data={data} onToggleMode={handleToggleMode} />
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Overview data={data} queueHistory={queueHistory} wsStatus={wsStatus} />} />
            <Route path="/live" element={<LiveAnalytics data={data} queueHistory={queueHistory} />} />
            <Route path="/zones" element={<ZoneAnalytics wsData={data} />} />
            <Route path="/movement" element={<MovementFlow />} />
            <Route path="/heatmaps" element={<Heatmaps wsStatus={wsStatus} />} />
            <Route path="/queue" element={<QueueMonitoring data={data} queueHistory={queueHistory} />} />
            <Route path="/friction" element={<FlowFriction />} />
            <Route path="/alerts" element={<AlertLogs wsStatus={wsStatus} />} />
            <Route path="/simulator" element={<WhatIfSimulator />} />
            <Route path="/comparison" element={<ScenarioComparison />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}
