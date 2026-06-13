import React, { useState } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer
} from 'recharts';
import { Wind, AlertTriangle, ShieldAlert, Award, Info, HeartCrack } from 'lucide-react';

export default function AbscondingModule({ data, processed }) {
  const [selectedHive, setSelectedHive] = useState(processed.hives[0] || 'hive41');

  // Filter raw data for selected hive
  const hiveRows = data
    .filter(d => d.hive === selectedHive)
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  // Downsample to daily values for easier trend visualization
  const getDailyAverages = () => {
    const dailyMap = {};
    hiveRows.forEach(row => {
      const dateStr = new Date(row.timestamp).toLocaleDateString();
      if (!dailyMap[dateStr]) {
        dailyMap[dateStr] = { dateStr, weightSum: 0, co2Sum: 0, tempSum: 0, count: 0 };
      }
      dailyMap[dateStr].weightSum += parseFloat(row.weight) || 0;
      dailyMap[dateStr].co2Sum += parseFloat(row.co2) || 0;
      dailyMap[dateStr].tempSum += parseFloat(row.temp) || 0;
      dailyMap[dateStr].count++;
    });
    
    return Object.values(dailyMap).map(d => ({
      date: d.dateStr,
      weight: Math.round((d.weightSum / d.count) * 100) / 100,
      co2: Math.round(d.co2Sum / d.count),
      temp: Math.round((d.tempSum / d.count) * 10) / 10
    }));
  };

  const dailyTrend = getDailyAverages();
  const localAnalysis = processed.abscondingAnalysis.find(a => a.hive === selectedHive) || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* HEADER SECTION */}
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ borderLeft: '4px solid var(--accent-gold)', background: 'linear-gradient(135deg, rgba(20, 26, 40, 0.8) 0%, rgba(245, 158, 11, 0.08) 100%)' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>Module 3: Absconding Behavior Prediction</h2>
              <p>
                Absconding is the complete abandonment of the hive by the entire colony. 
                Unlike swarming, it is triggered by negative stressors (Varroa mite overload, small hive beetle infestation, wasp attacks, lack of food, or severe thermal instability). 
                Early warning signs include a <strong>steady decline in weight over 5-15 days</strong> coupled with a <strong>continuous drop in CO2 and wild temperature fluctuations</strong>.
              </p>
            </div>
            <Wind size={48} color="var(--accent-gold)" style={{ filter: 'drop-shadow(0 0 10px var(--accent-gold-glow))' }} />
          </div>
        </div>
      </div>

      {/* QUICK STATUS CARDS */}
      <div className="dashboard-grid">
        <div className="card highlight-gold">
          <div className="stat-header">
            <span>Depopulation Rate</span>
            <HeartCrack size={16} color="var(--accent-gold)" />
          </div>
          <div className="stat-value">
            {localAnalysis.weightChangePeriod || 0}
            <span className="stat-unit">kg (last 6 days)</span>
          </div>
          <div className="stat-footer">
            <span style={{ color: (localAnalysis.weightChangePeriod || 0) < -1 ? 'var(--accent-crimson)' : 'var(--accent-secondary)' }}>
              Weight trend in selected period
            </span>
          </div>
        </div>

        <div className="card highlight-cyan">
          <div className="stat-header">
            <span>CO2 Delta</span>
            <Wind size={16} color="var(--accent-cyan)" />
          </div>
          <div className="stat-value">
            {localAnalysis.co2ChangePeriod || 0}
            <span className="stat-unit">ppm</span>
          </div>
          <div className="stat-footer">
            <span>Net carbon footprint trend</span>
          </div>
        </div>

        <div className="card highlight-crimson">
          <div className="stat-header">
            <span>Absconding Alert Status</span>
            <AlertTriangle size={16} color="var(--accent-crimson)" />
          </div>
          <div className="stat-value" style={{ fontSize: '1.25rem', height: '2.25rem', display: 'flex', alignItems: 'center', color: localAnalysis.status?.includes('High Risk') ? 'var(--accent-crimson)' : localAnalysis.status?.includes('Warning') ? 'var(--accent-gold)' : 'var(--accent-emerald)' }}>
            {localAnalysis.status || 'Normal'}
          </div>
          <div className="stat-footer">
            <span>Hive unit: {selectedHive.toUpperCase()}</span>
          </div>
        </div>
      </div>

      {/* DIAGNOSTIC GRAPH */}
      <div className="dashboard-grid">
        {/* DAILY AVERAGES TREND CHART */}
        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Long-Term Climate and Weight Trend Chart</h3>
              <p>Daily running averages for {selectedHive.toUpperCase()} showing gradual hive decline signals</p>
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
              <LineChart data={dailyTrend} margin={{ top: 10, right: 30, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="var(--text-secondary)" />
                <YAxis yAxisId="weight" stroke="var(--accent-gold)" unit="kg" label={{ value: 'Weight (kg)', angle: -90, position: 'insideLeft', fill: 'var(--accent-gold)' }} />
                <YAxis yAxisId="co2" orientation="right" stroke="var(--accent-cyan)" unit="ppm" label={{ value: 'CO2 (ppm)', angle: 90, position: 'insideRight', fill: 'var(--accent-cyan)' }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                />
                <Legend />
                <Line yAxisId="weight" type="monotone" dataKey="weight" name="Hive Weight" stroke="var(--accent-gold)" strokeWidth={2.5} />
                <Line yAxisId="co2" type="monotone" dataKey="co2" name="CO2 Concentration" stroke="var(--accent-cyan)" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* APIARY SUMMARY TABLE AND ACTION RECOMMENDATIONS */}
        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Absconding Risk (All Hives)</h3>
              <p>Depopulation rankings across the apiary</p>
            </div>
            <ShieldAlert size={20} color="var(--accent-gold)" />
          </div>
          
          <div className="table-container">
            <table className="custom-table" style={{ fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Hive</th>
                  <th>Wt Change</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {processed.abscondingAnalysis.map((item, idx) => (
                  <tr key={idx} style={{ cursor: 'pointer' }} onClick={() => setSelectedHive(item.hive)}>
                    <td style={{ fontWeight: 600 }}>{item.hive.toUpperCase()}</td>
                    <td style={{ color: item.weightChangePeriod < -1 ? 'var(--accent-crimson)' : 'var(--text-primary)' }}>
                      {item.weightChangePeriod} kg
                    </td>
                    <td>
                      <span className={`badge ${
                        item.status.includes('High Risk') ? 'critical' : 
                        item.status.includes('Warning') ? 'warning' : 'excellent'
                      }`}>
                        {item.status.split(' - ')[0]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div style={{ marginTop: '1.25rem', borderTop: '1px solid var(--card-border)', paddingTop: '0.5rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Mitigation Guidelines:</h4>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              🔒 <strong>For high-risk hives:</strong> Apply Varroa mite treatments immediately, check for wasp traps around the hive exterior, and install entrance mouse guards. Feed sugar syrup and pollen patties if food stores are depleted.
            </p>
          </div>
        </div>
      </div>
      
    </div>
  );
}
