// Sidebar.jsx — StorePulse AI
// Developer: Omkar Gurav
import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Radio, MapPin, Navigation, Flame,
  ShoppingCart, Zap, Layout, BarChart3, Settings,
  Activity
} from 'lucide-react';

const navItems = [
  { section: 'Monitor' },
  { to: '/', icon: LayoutDashboard, label: 'Overview', exact: true },
  { to: '/live', icon: Radio, label: 'Live Analytics' },
  { to: '/zones', icon: MapPin, label: 'Zone Analytics' },
  { to: '/movement', icon: Navigation, label: 'Movement Flow' },
  { to: '/heatmaps', icon: Flame, label: 'Heatmaps' },
  { to: '/queue', icon: ShoppingCart, label: 'Queue Monitoring' },
  { to: '/friction', icon: Zap, label: 'Flow Friction' },
  { section: 'Simulator' },
  { to: '/simulator', icon: Layout, label: 'What-If Simulator' },
  { to: '/comparison', icon: BarChart3, label: 'Scenario Compare' },
  { section: 'System' },
  { to: '/settings', icon: Settings, label: 'Settings & Privacy' },
];

export default function Sidebar({ wsStatus, queueAlert }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">
          <Activity size={20} color="white" />
        </div>
        <h1>StorePulse AI</h1>
        <div className="logo-sub">Retail Intelligence</div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item, idx) => {
          if (item.section) {
            return <div key={idx} className="nav-section-label">{item.section}</div>;
          }
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <Icon size={16} className="nav-icon" />
              <span>{item.label}</span>
              {item.to === '/queue' && queueAlert && (
                <span className="nav-badge">!</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div style={{ marginBottom: 4 }}>
          <strong>Omkar Gurav</strong>
        </div>
        <div style={{ fontSize: 10, marginBottom: 2 }}>
          WS: <span style={{ color: wsStatus === 'connected' ? '#10b981' : '#ef4444' }}>
            {wsStatus}
          </span>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>v1.0.0</div>
      </div>
    </aside>
  );
}
