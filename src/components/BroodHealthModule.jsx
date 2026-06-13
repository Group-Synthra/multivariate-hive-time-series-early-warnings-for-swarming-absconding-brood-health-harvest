import React, { useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, AreaChart, Area, ReferenceDot
} from 'recharts';
import { Heart, Activity, Info, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function BroodHealthModule({ data, processed }) {
  const [selectedHive, setSelectedHive] = useState(processed.hives[0] || 'hive41');

  // Filter raw data for histograms
  const hiveRows = data.filter(d => d.hive === selectedHive);

  // Generate Temperature Distribution data (bins)
  // Temp ranges from 15 to 45
  const getTempBins = () => {
    const bins = Array.from({ length: 30 }, (_, i) => ({
      binStart: 15 + i,
      binLabel: `${15 + i}°C`,
      count: 0
    }));
    hiveRows.forEach(row => {
      const t = Math.round(parseFloat(row.temp));
      const binIdx = bins.findIndex(b => b.binStart === t);
      if (binIdx !== -1) bins[binIdx].count++;
    });
    return bins;
  };

  // Generate Humidity Distribution data (bins)
  const getHumBins = () => {
    const bins = Array.from({ length: 20 }, (_, i) => ({
      binStart: 10 + i * 5,
      binLabel: `${10 + i * 5}%`,
      count: 0
    }));
    hiveRows.forEach(row => {
      const h = Math.round(parseFloat(row.humidity) / 5) * 5;
      const binIdx = bins.findIndex(b => b.binStart === h);
      if (binIdx !== -1) bins[binIdx].count++;
    });
    return bins;
  };

  const tempBins = getTempBins();
  const humBins = getHumBins();

  // Find stability summary for selected hive
  const hiveHealth = processed.broodHealth.find(h => h.hive === selectedHive) || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* HEADER SECTION */}
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ borderLeft: '4px solid var(--accent-emerald)', background: 'linear-gradient(135deg, rgba(20, 26, 40, 0.8) 0%, rgba(16, 185, 129, 0.08) 100%)' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>Module 1: Brood Health Status Prediction</h2>
              <p>
                Honeybee brood requires strict microclimate regulation inside the hive core. 
                Optimal Temperature: <strong>34°C - 36°C</strong>. Optimal Humidity: <strong>50% - 65%</strong>. 
                Deviations from these bounds indicate colony stress, queen failure, or environmental extremes.
              </p>
            </div>
            <Heart size={48} color="var(--accent-emerald)" style={{ filter: 'drop-shadow(0 0 10px var(--accent-emerald-glow))' }} />
          </div>
        </div>
      </div>

      {/* QUICK STATS CARDS */}
      <div className="dashboard-grid">
        <div className="card highlight-emerald">
          <div className="stat-header">
            <span>Optimal Temp Coverage</span>
            <Activity size={16} color="var(--accent-emerald)" />
          </div>
          <div className="stat-value">
            {hiveHealth.optimalTempPct}%
          </div>
          <div className="stat-footer">
            <span>Percentage of readings within 34-36°C</span>
          </div>
        </div>

        <div className="card highlight-cyan">
          <div className="stat-header">
            <span>Optimal Humidity Coverage</span>
            <Activity size={16} color="var(--accent-cyan)" />
          </div>
          <div className="stat-value">
            {hiveHealth.optimalHumidityPct}%
          </div>
          <div className="stat-footer">
            <span>Percentage of readings within 50-65%</span>
          </div>
        </div>

        <div className="card highlight-gold">
          <div className="stat-header">
            <span>Combined Brood Health Index</span>
            <ShieldCheck size={16} color="var(--accent-gold)" />
          </div>
          <div className="stat-value">
            {hiveHealth.optimalBothPct}%
          </div>
          <div className="stat-footer">
            <span className={`badge ${hiveHealth.status === 'Excellent' ? 'excellent' : hiveHealth.status === 'Good' ? 'good' : 'warning'}`}>
              Status: {hiveHealth.status}
            </span>
          </div>
        </div>
      </div>

      {/* DETAILED PLOTS */}
      <div className="dashboard-grid">
        {/* INTER-HIVE COMPARISON */}
        <div className="card chart-card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Brood Climate Range Coverage (By Hive)</h3>
              <p>Comparison of thermal and moisture stability metrics across the apiary</p>
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={processed.broodHealth}
                margin={{ top: 15, right: 20, left: -15, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hive" stroke="var(--text-secondary)" tickFormatter={v => v.toUpperCase()} />
                <YAxis stroke="var(--text-secondary)" unit="%" />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  formatter={(value) => [`${value}%`]}
                />
                <Legend />
                <Bar dataKey="optimalTempPct" name="Temp Stability (34-36°C)" fill="var(--accent-crimson)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="optimalHumidityPct" name="Humidity Stability (50-65%)" fill="var(--accent-cyan)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="optimalBothPct" name="Combined Health Index" fill="var(--accent-emerald)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* CLIMATE SHADOW & RECOMMENDATIONS */}
        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Hive-Specific Health Profile</h3>
              <p>Select apiary unit to inspect diagnostics</p>
            </div>
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

          <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="recs-container">
              <div className="rec-item" style={{ borderLeft: '3px solid var(--accent-emerald)' }}>
                <div className="rec-icon">
                  <ShieldCheck size={20} color="var(--accent-emerald)" />
                </div>
                <div className="rec-text">
                  <h4>Average Microclimate State</h4>
                  <p>
                    Mean Brood Temperature: <strong>{hiveHealth.avgTemp}°C</strong> | Mean Brood Humidity: <strong>{hiveHealth.avgHumidity}%</strong>.
                  </p>
                </div>
              </div>

              {hiveHealth.optimalBothPct < 60 ? (
                <div className="rec-item" style={{ borderLeft: '3px solid var(--accent-crimson)' }}>
                  <div className="rec-icon">
                    <AlertTriangle size={20} color="var(--accent-crimson)" />
                  </div>
                  <div className="rec-text">
                    <h4>Critical Instability Warning</h4>
                    <p>
                      This hive fails to regulate its brood zone climate, leaving larvae exposed. Potential causes: poor hive insulation, lack of worker population, queenless state, or draft leaks.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="rec-item" style={{ borderLeft: '3px solid var(--accent-cyan)' }}>
                  <div className="rec-icon">
                    <Info size={20} color="var(--accent-cyan)" />
                  </div>
                  <div className="rec-text">
                    <h4>Healthy Brood Maintenance</h4>
                    <p>
                      Hive maintains a very stable microclimate profile. This indicates high nurse bee density, strong cluster cohesion, and good ventilation management.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div style={{ marginTop: '0.5rem' }}>
              <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Core Recommendation Summary:</h4>
              <ul style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <li>Analyze temporal cycles to see if temperature drops align with cold night-time dips.</li>
                <li>Hives with &lt;50% health index require urgent manual queen checks.</li>
                <li>In high heat indexes, ensure landing boards are clear for fanning ventilation.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* SENSOR VALUE DISTRIBUTIONS FOR THE HIVE */}
      <div className="dashboard-grid">
        {/* TEMPERATURE DISTRIBUTION */}
        <div className="card chart-card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Brood Temperature Distribution</h3>
              <p>Frequency of readings. Green bar represents the Optimal rearing range (34-36°C)</p>
            </div>
          </div>
          <div className="chart-container" style={{ height: '240px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={tempBins} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-crimson)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--accent-crimson)" stopOpacity={0.05}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="binLabel" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  formatter={(value) => [value, 'Readings']}
                />
                {/* Visual optimal zone highlight */}
                <Area type="monotone" dataKey="count" stroke="var(--accent-crimson)" fillOpacity={1} fill="url(#tempGrad)" />
                
                {/* Highlight optimal area coordinates: from index 34 to 36 */}
                {/* Recharts reference band would work well here */}
                {/* Standard vertical lines for optimal borders */}
                <ReferenceDot x="34°C" y={5} r={0} stroke="var(--accent-emerald)" strokeWidth={2} label={{ value: 'Optimal Start', fill: 'var(--accent-emerald)', position: 'insideTopLeft' }} />
                <ReferenceDot x="36°C" y={5} r={0} stroke="var(--accent-emerald)" strokeWidth={2} label={{ value: 'Optimal End', fill: 'var(--accent-emerald)', position: 'insideTopRight' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* HUMIDITY DISTRIBUTION */}
        <div className="card chart-card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Brood Humidity Distribution</h3>
              <p>Frequency of readings. Blue shaded bar represents the Optimal rearing range (50-65%)</p>
            </div>
          </div>
          <div className="chart-container" style={{ height: '240px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={humBins} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="humGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-cyan)" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0.05}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="binLabel" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  formatter={(value) => [value, 'Readings']}
                />
                <Area type="monotone" dataKey="count" stroke="var(--accent-cyan)" fillOpacity={1} fill="url(#humGrad)" />
                <ReferenceDot x="50%" y={5} r={0} stroke="var(--accent-emerald)" strokeWidth={2} label={{ value: 'Optimal Start', fill: 'var(--accent-emerald)', position: 'insideTopLeft' }} />
                <ReferenceDot x="65%" y={5} r={0} stroke="var(--accent-emerald)" strokeWidth={2} label={{ value: 'Optimal End', fill: 'var(--accent-emerald)', position: 'insideTopRight' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

    </div>
  );
}
