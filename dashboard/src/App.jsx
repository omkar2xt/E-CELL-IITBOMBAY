import React from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useQueueHistory } from './hooks/useQueueHistory';
import { StatCard } from './components/StatCard';
import { QueueChart } from './components/QueueChart';
import { DemoPanel } from './components/DemoPanel';
import { LiveFeed } from './components/LiveFeed';
import { Users, LogIn, LogOut, Activity, AlertTriangle } from 'lucide-react';
import './index.css';

const WS_URL = 'ws://localhost:8000/ws';
const STREAM_URL = 'http://localhost:8000/snapshot';

function App() {
  const { data, status } = useWebSocket(WS_URL);
  const queueHistory = useQueueHistory(data?.queue_count);

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-title">
          <h1>Retail Analytics</h1>
          <div className={`status-badge ${status}`}>
            <span className="status-dot"></span>
            {status === 'connected' ? 'LIVE' : status.toUpperCase()}
          </div>
        </div>
        <div className="header-meta">
          {data && <span>FPS: {data.fps.toFixed(1)}</span>}
        </div>
      </header>

      {/* Alert Banner */}
      {data?.queue_alert && (
        <div className="alert-banner pulse-bg">
          <AlertTriangle size={24} />
          <span>
            <strong>QUEUE ALERT!</strong> Checkout queue exceeded threshold ({data.queue_count} people). Please open another register!
          </span>
        </div>
      )}

      {/* Main Content */}
      <main className="dashboard-main">
        {/* Left Column: Video & Demographics */}
        <div className="col-left">
          <LiveFeed streamUrl={STREAM_URL} />
          
          <div className="metrics-grid">
            <StatCard 
              title="Total In" 
              value={data?.count_in || 0} 
              icon={LogIn} 
            />
            <StatCard 
              title="Total Out" 
              value={data?.count_out || 0} 
              icon={LogOut} 
            />
            <StatCard 
              title="Occupancy" 
              value={data?.occupancy || 0} 
              subtitle="Current inside"
              icon={Users} 
            />
            <StatCard 
              title="Cashier Queue" 
              value={data?.queue_count || 0} 
              alert={data?.queue_alert}
              icon={Activity} 
            />
          </div>
        </div>

        {/* Right Column: Charts & Data */}
        <div className="col-right">
          <QueueChart data={queueHistory} />
          {data?.demographics && <DemoPanel demographics={data.demographics} />}
        </div>
      </main>
    </div>
  );
}

export default App;
