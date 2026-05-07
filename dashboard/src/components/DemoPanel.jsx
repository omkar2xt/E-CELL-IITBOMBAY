import React from 'react';

export function DemoPanel({ demographics }) {
  if (!demographics || !demographics.enabled || demographics.sample_count === 0) {
    return (
      <div className="demo-panel empty">
        <p>Demographic data unavailable or disabled.</p>
      </div>
    );
  }

  const { gender_distribution, age_distribution, sample_count } = demographics;

  const getPercentage = (dist) => {
    if (!dist) return [];
    return Object.entries(dist)
      .sort((a, b) => b[1] - a[1]) // Sort by percentage descending
      .slice(0, 4); // Top 4
  };

  const topGenders = getPercentage(gender_distribution);
  const topAges = getPercentage(age_distribution);

  return (
    <div className="demo-panel">
      <h3>Demographics <span>(n={sample_count})</span></h3>
      
      <div className="demo-section">
        <h4>Gender</h4>
        <div className="demo-bars">
          {topGenders.map(([label, pct]) => (
            <div key={label} className="demo-bar-container">
              <div className="demo-bar-label">{label}</div>
              <div className="demo-bar-track">
                <div 
                  className="demo-bar-fill" 
                  style={{ 
                    width: `${pct}%`, 
                    backgroundColor: label.toLowerCase().includes('woman') ? '#fb923c' : '#38bdf8' 
                  }}
                />
              </div>
              <div className="demo-bar-value">{Math.round(pct)}%</div>
            </div>
          ))}
        </div>
      </div>

      <div className="demo-section">
        <h4>Age Groups</h4>
        <div className="demo-bars">
          {topAges.map(([label, pct]) => (
            <div key={label} className="demo-bar-container">
              <div className="demo-bar-label">{label}</div>
              <div className="demo-bar-track">
                <div 
                  className="demo-bar-fill" 
                  style={{ width: `${pct}%`, backgroundColor: '#4ade80' }}
                />
              </div>
              <div className="demo-bar-value">{Math.round(pct)}%</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
