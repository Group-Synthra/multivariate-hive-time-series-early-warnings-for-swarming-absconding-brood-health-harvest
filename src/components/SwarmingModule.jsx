import React, { useState } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, ReferenceLine, ScatterChart, Scatter
} from 'recharts';
import { ShieldAlert, Zap, Thermometer, Info, AlertTriangle, AlertCircle } from 'lucide-react';

export default function SwarmingModule({ data, processed }) {
  const [selectedHive, setSelectedHive] = useState(processed.hives[0] || 'hive41');

  // Filter raw data for selected hive
  const hiveRows = data
    .filter(d => d.hive === selectedHive)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  // Find swarming events detected for this hive or globally
  const swarmEvents = processed.swarmingEvents;
  const localSwarmEvents = swarmEvents.filter(e => e.hive === selectedHive);

  // Annotate data for chart visualization
  const chartData = hiveRows.map(d => {
    const isEvent = swarmEvents.some(e => e.hive === d.hive && e.timestamp === d.timestamp);
    return {
      ...d,
      displayTime: new Date(d.timestamp).toLocaleDateString() + ' ' + new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      weightVal: parseFloat(d.weight),
      co2Val: parseFloat(d.co2),
      swarmMarker: isEvent ? parseFloat(d.weight) : null
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* HEADER SECTION */}
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ borderLeft: '4px solid var(--accent-crimson)', background: 'linear-gradient(135deg, rgba(20, 26, 40, 0.8) 0%, rgba(239, 68, 68, 0.08) 100%)' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>Module 2: Colony Swarming Prediction</h2>
              <p>
                Swarming is the natural reproduction mechanism where half of the worker colony leaves with the old queen to establish a new home. 
                This results in a <strong>sudden weight drop of 2 to 5 kg</strong> within 1-2 hours, accompanied by a <strong>rapid spike in CO2 &gt; 1500ppm</strong> and an elevated temperature deviation as bees engorge on honey and crowd prior to takeoff.
              </p>
            </div>
            <Zap size={48} color="var(--accent-crimson)" style={{ filter: 'drop-shadow(0 0 10px var(--accent-crimson-glow))' }} />
          </div>
        </div>
      </div>

      {/* QUICK STATS & WARNING FLAGS */}
      <div className="dashboard-grid">
        <div className="card highlight-crimson">
          <div className="stat-header">
            <span>Swarm Events Detected</span>
            <ShieldAlert size={16} color="var(--accent-crimson)" />
          </div>
          <div className="stat-value">
            {swarmEvents.length}
            <span className="stat-unit">across apiary</span>
          </div>
          <div className="stat-footer">
            <span>Trigger: Weight drop &lt; -0.5kg &amp; CO2 trend spike</span>
          </div>
        </div>

        <div className="card highlight-gold">
          <div className="stat-header">
            <span>CO2 Spikes Registered</span>
            <AlertCircle size={16} color="var(--accent-gold)" />
          </div>
          <div className="stat-value">
            {data.filter(d => parseFloat(d.co2) > 1800).length}
            <span className="stat-unit">total logs</span>
          </div>
          <div className="stat-footer">
            <span>Critical threshold set at 1,800 ppm</span>
          </div>
        </div>

        <div className="card highlight-emerald">
          <div className="stat-header">
            <span>Current Risk Assessment</span>
            <Thermometer size={16} color="var(--accent-emerald)" />
          </div>
          <div className="stat-value" style={{ color: localSwarmEvents.length > 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)' }}>
            {localSwarmEvents.length > 0 ? 'CRITICAL ALERT' : 'SECURE'}
          </div>
          <div className="stat-footer">
            <span>Selected Unit: {selectedHive.toUpperCase()}</span>
          </div>
        </div>
      </div>

      {/* PLOT: CO2 Spike + Weight Drop Correlation */}
      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Swarm Alarm Event Correlation Chart</h3>
              <p>Sudden drop in weight coupled with a CO2 concentration surge for {selectedHive.toUpperCase()}</p>
            </div>
            <div className="chart-controls">
              <select 
                className="chart-select" 
                value={selectedHive} 
                onChange={(e) => setSelectedHive(e.target.value)}
              >
                {processed.hives.map(hive => (
                  <option key={hive} value={hive}>{hive.toUpperCase()}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 30, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="displayTime" stroke="var(--text-secondary)" minTickGap={70} />
                {/* Weight Axis */}
                <YAxis yAxisId="weight" stroke="var(--accent-gold)" unit="kg" label={{ value: 'Weight (kg)', angle: -90, position: 'insideLeft', fill: 'var(--accent-gold)' }} />
                {/* CO2 Axis */}
                <YAxis yAxisId="co2" orientation="right" stroke="var(--accent-emerald)" unit="ppm" label={{ value: 'CO2 (ppm)', angle: 90, position: 'insideRight', fill: 'var(--accent-emerald)' }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <Legend />
                <Line yAxisId="weight" type="monotone" dataKey="weightVal" name="Hive Weight" stroke="var(--accent-gold)" strokeWidth={2} dot={false} />
                <Line yAxisId="co2" type="monotone" dataKey="co2Val" name="CO2 Concentration" stroke="var(--accent-emerald)" strokeWidth={1.5} dot={false} />
                
                {/* Highlight Swarm Event markers if any */}
                <Scatter yAxisId="weight" name="Swarm Event Takeoff" data={chartData.filter(d => d.swarmMarker !== null)} dataKey="swarmMarker" fill="var(--accent-crimson)" shape="star" legendType="line" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* DETECTED ALERTS LIST */}
        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Swarm Alarm Event Logs</h3>
              <p>Historical alarms captured during telemetry processing</p>
            </div>
            <ShieldAlert size={20} color="var(--accent-crimson)" />
          </div>
          
          <div className="table-container" style={{ maxHeight: '320px', overflowY: 'auto' }}>
            {swarmEvents.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
                <Info size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                <p>No swarming events detected in the active dataset. Hive clusters appear stable.</p>
              </div>
            ) : (
              <table className="custom-table" style={{ fontSize: '0.825rem' }}>
                <thead>
                  <tr>
                    <th>Hive</th>
                    <th>Time</th>
                    <th>Wt Drop</th>
                    <th>CO2 Max</th>
                  </tr>
                </thead>
                <tbody>
                  {swarmEvents.map((evt, idx) => (
                    <tr key={idx} style={{ cursor: 'pointer' }} onClick={() => setSelectedHive(evt.hive)}>
                      <td style={{ fontWeight: 600, color: 'var(--accent-crimson)' }}>{evt.hive.toUpperCase()}</td>
                      <td>{new Date(evt.timestamp).toLocaleDateString() + ' ' + new Date(evt.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                      <td style={{ color: 'var(--accent-crimson)' }}>{evt.weightChange} kg</td>
                      <td style={{ color: 'var(--accent-emerald)' }}>{evt.co2} ppm</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          
          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--card-border)', paddingTop: '0.5rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Swarming Recommendations:</h4>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              ⚠️ Upon swarm notification, check trees near the apiary within 2 hours. Swarms cluster nearby before searching for permanent nest cavities. Keep a swarm retrieval trap box on standby.
            </p>
          </div>
        </div>
      </div>
      
    </div>
  );
}
