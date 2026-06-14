import React from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine, Cell
} from 'recharts';

export const HealthTimelineChart = ({ data }) => (
  <div className="card chart-card">
    <div className="chart-header">
      <h3>📈 Brood Health Score & BHSI Timeline</h3>
      <p>Health score (0–100) and stability index</p>
    </div>
    <div className="chart-container" style={{ height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleDateString()} stroke="var(--text-secondary)" />
          <YAxis domain={[0, 100]} stroke="var(--text-secondary)" />
          <Tooltip contentStyle={{ background: '#1e293b', border: 'none' }} />
          <Legend />
          <Line type="monotone" dataKey="brood_health_score" stroke="var(--accent-emerald)" strokeWidth={2} dot={false} name="Health Score" />
          <Line type="monotone" dataKey="bhsi" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} name="BHSI (Stability)" />
          <ReferenceLine y={60} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Good threshold", fill: "#f59e0b" }} />
          <ReferenceLine y={40} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "Poor threshold", fill: "#ef4444" }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export const RodTrendChart = ({ data }) => (
  <div className="card chart-card">
    <div className="chart-header"><h3>⏱️ Rate of Deterioration (RoD)</h3><p>Points lost/gained per hour – negative slope = danger</p></div>
    <div className="chart-container" style={{ height: 200 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleDateString()} />
          <YAxis stroke="var(--text-secondary)" />
          <Tooltip />
          <Area type="monotone" dataKey="rod" stroke="var(--accent-crimson)" fill="var(--accent-crimson)" fillOpacity={0.3} />
          <ReferenceLine y={0} stroke="#fff" strokeDasharray="3 3" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export const ApiaryBarChart = ({ data, colors }) => {
  const gradientId = "barGradient";
  return (
    <div className="card chart-card">
      <div className="chart-header">
        <h3>🏠 Apiary Overview</h3>
        <p>Current Brood Health Score per hive (sorted highest to lowest)</p>
      </div>
      <div className="chart-container" style={{ height: 350, overflowX: 'auto' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical" 
            margin={{ top: 10, right: 30, left: 60, bottom: 5 }}
            animationDuration={800}
            animationEasing="ease-in-out"
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="var(--accent-emerald)" stopOpacity={0.9} />
                <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity={0.7} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis type="number" domain={[0, 100]} stroke="var(--text-secondary)" />
            <YAxis 
              type="category" 
              dataKey="hive" 
              stroke="var(--text-secondary)" 
              tick={{ fontSize: 11 }}
              width={70}
            />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px' }}
              formatter={(value, name, props) => [`${value} (${props.payload.health})`, 'Health Score']}
            />
            <Bar
              dataKey="score"
              fill={`url(#${gradientId})`}
              radius={[0, 8, 8, 0]}
              animationBegin={0}
              animationDuration={1000}
              isAnimationActive={true}
            >
              {data.map((entry, idx) => (
                <Cell key={`cell-${idx}`} fill={colors[entry.health]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};