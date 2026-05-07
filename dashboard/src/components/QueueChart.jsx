import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

export function QueueChart({ data }) {
  if (!data || data.length === 0) {
    return <div className="chart-empty">Waiting for data...</div>;
  }

  return (
    <div className="chart-container">
      <h3>Queue History (Last 60 records)</h3>
      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#333" />
            <XAxis dataKey="time" stroke="#888" tick={{fontSize: 12}} minTickGap={20} />
            <YAxis stroke="#888" allowDecimals={false} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '4px', color: '#fff' }}
              itemStyle={{ color: '#ef4444' }}
            />
            <Area 
              type="monotone" 
              dataKey="count" 
              stroke="#ef4444" 
              fillOpacity={1} 
              fill="url(#colorCount)" 
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
