import React, { useState } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, ReferenceArea, ReferenceLine
} from 'recharts';
import { Award, TrendingUp, Compass, Calendar, Info, ShieldCheck } from 'lucide-react';

export default function HarvestingModule({ data, processed }) {
  const [selectedHive, setSelectedHive] = useState(processed.hives[0] || 'hive41');

  // Filter raw data for selected hive
  const hiveRows = data
    .filter(d => d.hive === selectedHive)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  // Find harvesting analysis for this hive
  const harvestStats = processed.harvestingAnalysis.find(h => h.hive === selectedHive) || {};

  // Formulate data for weight plot
  const chartData = hiveRows.map(d => ({
    ...d,
    displayTime: new Date(d.timestamp).toLocaleDateString(),
    weightVal: parseFloat(d.weight)
  }));

  // Identify where the weight plateaus to draw a reference area
  // In a real application this is a dynamically predicted range.
  // For the selected hive, let's look at when the weight is near the max and stable.
  // Let's find index range of max weight to highlight the "optimal window"
  const maxWeight = Math.max(...chartData.map(d => d.weightVal));
  const maxWeightIdx = chartData.findIndex(d => d.weightVal === maxWeight);
  
  // Highlight an area around the peak
  const peakTimeStart = chartData[Math.max(0, maxWeightIdx - 48)]?.displayTime;
  const peakTimeEnd = chartData[Math.min(chartData.length - 1, maxWeightIdx + 48)]?.displayTime;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* HEADER SECTION */}
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ borderLeft: '4px solid var(--accent-gold)', background: 'linear-gradient(135deg, rgba(20, 26, 40, 0.8) 0%, rgba(245, 158, 11, 0.08) 100%)' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>Module 4: Time-Optimal Honey Harvesting</h2>
              <p>
                Harvesting honey at the perfect moment maximizes yield and ensures honey has been properly capped and cured by bees (water content &lt; 18%). 
                We monitor weight curves to detect a **weight plateau** (nectar flow end) where weight gain ceases but remains at capacity. 
                A **sudden drop of 10 to 30 kg** represents a successful honey extraction event.
              </p>
            </div>
            <Award size={48} color="var(--accent-gold)" style={{ filter: 'drop-shadow(0 0 10px var(--accent-gold-glow))' }} />
          </div>
        </div>
      </div>

      {/* STATISTICS CARDS */}
      <div className="dashboard-grid">
        <div className="card highlight-gold">
          <div className="stat-header">
            <span>Peak Hive Weight</span>
            <TrendingUp size={16} color="var(--accent-gold)" />
          </div>
          <div className="stat-value">
            {harvestStats.maxWeight || 0}
            <span className="stat-unit">kg</span>
          </div>
          <div className="stat-footer">
            <span>Maximum weight reached in this cycle</span>
          </div>
        </div>

        <div className="card highlight-cyan">
          <div className="stat-header">
            <span>Current Weight</span>
            <Compass size={16} color="var(--accent-cyan)" />
          </div>
          <div className="stat-value">
            {harvestStats.currentWeight || 0}
            <span className="stat-unit">kg</span>
          </div>
          <div className="stat-footer">
            <span>Current weight load of selected unit</span>
          </div>
        </div>

        <div className="card highlight-emerald">
          <div className="stat-header">
            <span>Harvest Readiness</span>
            <ShieldCheck size={16} color="var(--accent-emerald)" />
          </div>
          <div className="stat-value" style={{ fontSize: '1.25rem', height: '2.25rem', display: 'flex', alignItems: 'center', color: harvestStats.status === 'Optimal Harvest Window' ? 'var(--accent-emerald)' : 'var(--text-secondary)' }}>
            {harvestStats.status || 'Not Ready'}
          </div>
          <div className="stat-footer">
            <span>Unit: {selectedHive.toUpperCase()} | Extractions: {harvestStats.harvestCount}</span>
          </div>
        </div>
      </div>

      {/* PLOT: Weight Curve + Harvest Events */}
      <div className="dashboard-grid">
        {/* WEIGHT CURVE GRAPH */}
        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Honey Weight Curve & Harvesting Windows</h3>
              <p>Detecting weight plateaus and super removal events for {selectedHive.toUpperCase()}</p>
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
                <YAxis stroke="var(--accent-gold)" unit="kg" domain={['dataMin - 5', 'dataMax + 5']} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <Legend />
                
                {/* Draw shaded area highlighting optimal harvest window (near maximum weight) */}
                {peakTimeStart && peakTimeEnd && (
                  <ReferenceArea x1={peakTimeStart} x2={peakTimeEnd} fill="rgba(245, 158, 11, 0.05)" stroke="var(--accent-gold)" strokeDasharray="3 3" label={{ value: 'Optimal Harvest Window', fill: 'var(--accent-gold)', position: 'insideTopLeft' }} />
                )}

                <Line type="monotone" dataKey="weightVal" name="Hive Weight" stroke="var(--accent-gold)" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* APIARY READINESS LEADERBOARD */}
        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Apiary Harvest Board</h3>
              <p>Readiness levels and honey accumulation status</p>
            </div>
            <Calendar size={20} color="var(--accent-gold)" />
          </div>
          
          <div className="table-container">
            <table className="custom-table" style={{ fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Hive</th>
                  <th>Weight</th>
                  <th>Readiness</th>
                  <th>Extr.</th>
                </tr>
              </thead>
              <tbody>
                {processed.harvestingAnalysis.map((item, idx) => (
                  <tr key={idx} style={{ cursor: 'pointer' }} onClick={() => setSelectedHive(item.hive)}>
                    <td style={{ fontWeight: 600 }}>{item.hive.toUpperCase()}</td>
                    <td>{item.currentWeight} kg</td>
                    <td>
                      <span className={`badge ${
                        item.status === 'Optimal Harvest Window' ? 'excellent' : 
                        item.status === 'Nearing Capacity' ? 'warning' : 'good'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td>{item.harvestCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div style={{ marginTop: '1.25rem', borderTop: '1px solid var(--card-border)', paddingTop: '0.5rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Harvesting Advice:</h4>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              🍯 <strong>Maximize Hive Output:</strong> Harvest when weights plateau during nectar flows. Avoid harvesting during high humidity days to prevent honey moisture absorption, which could cause fermentation.
            </p>
          </div>
        </div>
      </div>
      
    </div>
  );
}
