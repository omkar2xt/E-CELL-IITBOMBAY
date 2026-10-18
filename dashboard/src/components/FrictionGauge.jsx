// FrictionGauge.jsx — StorePulse AI
// Flow Friction Score semi-circular gauge
// Developer: Omkar Gurav
import React from 'react';

function getColor(score) {
  if (score >= 75) return '#ef4444';
  if (score >= 50) return '#f97316';
  if (score >= 25) return '#f59e0b';
  return '#10b981';
}

function getAlertLabel(level) {
  const map = { NONE: 'Normal', MEDIUM: 'Moderate', HIGH: 'High', CRITICAL: 'Critical' };
  return map[level] || 'Unknown';
}

export function FrictionGauge({ score = 0, alertLevel = 'NONE', size = 120 }) {
  const radius = 46;
  const cx = 60, cy = 56;
  const circumference = Math.PI * radius;  // half circle
  const filled = circumference * (score / 100);
  const color = getColor(score);

  // Arc path: left to right semi-circle
  const startX = cx - radius;
  const endX = cx + radius;
  const pathD = `M ${startX} ${cy} A ${radius} ${radius} 0 0 1 ${endX} ${cy}`;

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width={120} height={70} viewBox="0 0 120 70" className="gauge-arc">
        {/* Track */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Fill */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          style={{ transition: 'stroke-dasharray 0.6s ease, stroke 0.4s ease' }}
          filter={`drop-shadow(0 0 6px ${color}88)`}
        />
        {/* Center label */}
        <text x={cx} y={cy - 2} textAnchor="middle"
          fill="white" fontSize="18" fontWeight="700"
          fontFamily="'Space Grotesk', sans-serif">
          {Math.round(score)}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle"
          fill="rgba(255,255,255,0.4)" fontSize="9" fontWeight="500">
          / 100
        </text>
        {/* Min/Max labels */}
        <text x={startX + 4} y={cy + 18} fill="rgba(255,255,255,0.3)" fontSize="9">0</text>
        <text x={endX - 4} y={cy + 18} fill="rgba(255,255,255,0.3)" fontSize="9" textAnchor="end">100</text>
      </svg>
      <div style={{
        fontSize: 11, fontWeight: 700, color,
        marginTop: 2, letterSpacing: '0.5px'
      }}>
        {getAlertLabel(alertLevel)}
      </div>
    </div>
  );
}
