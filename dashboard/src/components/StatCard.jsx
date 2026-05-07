import React from 'react';

export function StatCard({ title, value, subtitle, alert, icon: Icon }) {
  return (
    <div className={`stat-card ${alert ? 'alert' : ''}`}>
      <div className="stat-card-header">
        <h3 className="stat-card-title">{title}</h3>
        {Icon && <Icon className="stat-card-icon" size={20} />}
      </div>
      <div className="stat-card-value">{value}</div>
      {subtitle && <div className="stat-card-subtitle">{subtitle}</div>}
    </div>
  );
}
