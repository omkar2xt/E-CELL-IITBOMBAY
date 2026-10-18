// StatCard.jsx — StorePulse AI
// Developer: Omkar Gurav
import React from 'react';

export function StatCard({ title, value, subtitle, icon: Icon, alert, color, trend }) {
  return (
    <div className={`stat-card${alert ? ' alert' : ''}`}
         style={{ '--accent-gradient': color }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="stat-card-label">{title}</span>
        {Icon && (
          <div className="stat-card-icon">
            <Icon size={16} />
          </div>
        )}
      </div>
      <div className="stat-card-value">{value}</div>
      {subtitle && <div className="stat-card-sub">{subtitle}</div>}
      {trend !== undefined && (
        <div style={{
          fontSize: 11, marginTop: 4,
          color: trend >= 0 ? 'var(--brand-success)' : 'var(--brand-danger)'
        }}>
          {trend >= 0 ? '▲' : '▼'} {Math.abs(trend)}% vs prev
        </div>
      )}
    </div>
  );
}
