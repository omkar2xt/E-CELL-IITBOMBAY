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
import { useWebSocket } from './hooks/useWebSocket';
import { useQueueHistory } from './hooks/useQueueHistory';
import { WS_URL } from './config';
import './index.css';

const PAGE_TITLES = {
  '/':           'Overview',
  '/live':       'Live Analytics',
  '/zones':      'Zone Analytics',
  '/movement':   'Movement Flow',
  '/heatmaps':   'Heatmaps',
  '/queue':      'Queue Monitoring',
  '/friction':   'Flow Friction',
  '/simulator':  'What-If Simulator',
  '/comparison': 'Scenario Comparison',
  '/settings':   'Settings & Privacy',
};

function PageHeader({ path, wsStatus, data }) {
  const title = Object.entries(PAGE_TITLES).find(([p]) => path === p)?.[1] || 'StorePulse AI';

  return (
    <div className="page-header">
      <h2>{title}</h2>
      <div className="header-right">
        {data?.is_demo && (
          <span className="demo-badge">DEMO MODE</span>
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

  return (
    <div className="app-shell">
      <Sidebar wsStatus={wsStatus} queueAlert={data?.queue_alert} />
      <div className="main-area">
        <PageHeader path={path} wsStatus={wsStatus} data={data} />
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Overview data={data} queueHistory={queueHistory} wsStatus={wsStatus} />} />
            <Route path="/live" element={<LiveAnalytics data={data} queueHistory={queueHistory} />} />
            <Route path="/zones" element={<ZoneAnalytics wsData={data} />} />
            <Route path="/movement" element={<MovementFlow />} />
            <Route path="/heatmaps" element={<Heatmaps wsStatus={wsStatus} />} />
            <Route path="/queue" element={<QueueMonitoring data={data} queueHistory={queueHistory} />} />
            <Route path="/friction" element={<FlowFriction />} />
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
