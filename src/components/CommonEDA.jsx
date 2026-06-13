import React, { useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';
import { AlertTriangle, Info, BarChart2, Calendar, ImageIcon } from 'lucide-react';

// Helper: get image URL served by Flask
const imgUrl = (filename) => `/api/eda/images/${filename}`;

export default function CommonEDA({ edaData }) {
  const [selectedSensor, setSelectedSensor] = useState('temp');

  const sensorColors = {
    co2: '#10b981',
    temp: '#ef4444',
    humidity: '#06b6d4',
    weight: '#f59e0b',
  };
  const sensorUnits = { co2: 'ppm', temp: '°C', humidity: '%', weight: 'kg' };

  const overallStats = edaData?.sensor_statistics || {};
  const outlierAnalysis = edaData?.outlier_analysis || {};
  const hiveStats = edaData?.hive_stats || [];
  const hourlyPatterns = edaData?.hourly_patterns || [];
  const summary = edaData?.summary || {};

  // Outlier bar chart data
  const outlierBarData = [
    { sensor: 'CO2', outlierPercent: outlierAnalysis.co2_percentage ?? 0 },
    { sensor: 'Temperature', outlierPercent: outlierAnalysis.temperature_percentage ?? 0 },
    { sensor: 'Humidity', outlierPercent: outlierAnalysis.humidity_percentage ?? 0 },
    { sensor: 'Weight', outlierPercent: outlierAnalysis.weight_percentage ?? 0 },
  ];

  // Hive comparison bar chart data
  const hiveBarData = hiveStats.map(h => ({
    hive: h.hive,
    value: h[`${selectedSensor}_mean`] ?? 0,
  }));

  // Stats table rows
  const statsRows = [
    { label: 'Temperature (°C)', key: 'temperature' },
    { label: 'Humidity (%)', key: 'humidity' },
    { label: 'Weight (kg)', key: 'weight' },
    { label: 'CO2 (ppm)', key: 'co2' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

      {/* WELCOME BANNER */}
      <div className="dashboard-grid">
        <div className="card welcome-card">
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>Dataset Exploratory Summary</h2>
              <p>
                Real EDA results computed by Python analysis pipeline.
                Dataset: <strong>{summary.total_records?.toLocaleString()}</strong> records
                from <strong>{summary.total_hives}</strong> hives.
                Period: {summary.analysis_start?.substring(0, 10)} → {summary.analysis_end?.substring(0, 10)}.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* STATS TABLE + OUTLIER BAR CHART */}
      <div className="dashboard-grid">
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Overall Dataset Statistics</h3>
              <p>Computed by Python pandas describe() pipeline</p>
            </div>
            <BarChart2 size={20} color="var(--accent-gold)" />
          </div>
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Sensor</th>
                  <th>Mean</th>
                  <th>Std Dev</th>
                  <th>Min</th>
                  <th>Q1 (25%)</th>
                  <th>Median</th>
                  <th>Q3 (75%)</th>
                  <th>Max</th>
                </tr>
              </thead>
              <tbody>
                {statsRows.map(({ label, key }) => {
                  const s = overallStats[key] || {};
                  return (
                    <tr key={key}>
                      <td style={{ fontWeight: 600 }}>{label}</td>
                      <td>{s.mean ?? '—'}</td>
                      <td>{s.std ?? '—'}</td>
                      <td>{s.min ?? '—'}</td>
                      <td>{s.q1 ?? '—'}</td>
                      <td style={{ fontWeight: 600 }}>{s.median ?? '—'}</td>
                      <td>{s.q3 ?? '—'}</td>
                      <td>{s.max ?? '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* OUTLIER BAR CHART */}
        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Outlier Percentage by Sensor</h3>
              <p>IQR method (1.5× IQR threshold)</p>
            </div>
            <AlertTriangle size={20} color="var(--accent-crimson)" />
          </div>
          <div style={{ height: '220px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={outlierBarData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="sensor" stroke="var(--text-secondary)" />
                <YAxis stroke="var(--text-secondary)" unit="%" />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  formatter={(val) => [`${val}%`, 'Outliers']}
                />
                <Bar dataKey="outlierPercent" radius={[4, 4, 0, 0]}>
                  {outlierBarData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.outlierPercent < 1 ? 'var(--accent-emerald)'
                        : entry.outlierPercent < 5 ? 'var(--accent-gold)'
                        : 'var(--accent-crimson)'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            <span style={{ color: 'var(--accent-emerald)' }}>Green &lt;1%</span>
            <span style={{ color: 'var(--accent-gold)' }}>Orange &lt;5%</span>
            <span style={{ color: 'var(--accent-crimson)' }}>Red ≥5%</span>
          </div>
        </div>
      </div>

      {/* PYTHON EDA IMAGES — Outlier Boxplots */}
      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Outlier Analysis — Boxplots</h3>
              <p>Generated by Python EDA pipeline (matplotlib/seaborn)</p>
            </div>
            <ImageIcon size={20} color="var(--accent-cyan)" />
          </div>
          <img
            src={imgUrl('outlier_analysis_boxplots.png')}
            alt="Outlier Boxplots"
            style={{ width: '100%', borderRadius: '8px', marginTop: '0.5rem', background: '#fff1' }}
            onError={e => { e.target.style.display = 'none'; }}
          />
        </div>
      </div>

      {/* HIVE COMPARISON CHART + CORRELATION IMAGE */}
      <div className="dashboard-grid">
        <div className="card chart-card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Inter-Hive Sensor Comparison</h3>
              <p>Average sensor values per hive unit</p>
            </div>
            <div className="chart-controls">
              <select
                className="chart-select"
                value={selectedSensor}
                onChange={e => setSelectedSensor(e.target.value)}
              >
                {['co2', 'temp', 'humidity', 'weight'].map(s => (
                  <option key={s} value={s}>{s.toUpperCase()}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hiveBarData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hive" stroke="var(--text-secondary)" tickFormatter={v => v.toUpperCase()} />
                <YAxis stroke="var(--text-secondary)" unit={sensorUnits[selectedSensor]} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  formatter={v => [`${v} ${sensorUnits[selectedSensor]}`, 'Average']}
                />
                <Bar dataKey="value" fill={sensorColors[selectedSensor]} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* CORRELATION MATRIX IMAGE */}
        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Correlation Matrix</h3>
              <p>Pearson coefficients — all features</p>
            </div>
            <Info size={18} color="var(--text-secondary)" />
          </div>
          <img
            src={imgUrl('correlation_matrix_all_modules.png')}
            alt="Correlation Matrix"
            style={{ width: '100%', borderRadius: '8px', marginTop: '0.75rem' }}
            onError={e => {
              e.target.replaceWith(Object.assign(document.createElement('p'), {
                textContent: 'Run python run_eda.py to generate this image.',
                style: 'color:var(--text-muted);font-size:0.85rem;padding:1rem;'
              }));
            }}
          />
        </div>
      </div>

      {/* ANOMALY DETECTION IMAGE */}
      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Anomaly Detection</h3>
              <p>CO2, weight, and temperature anomaly time series from Python EDA</p>
            </div>
          </div>
          <img
            src={imgUrl('anomalies_all_modules.png')}
            alt="Anomalies"
            style={{ width: '100%', borderRadius: '8px', marginTop: '0.5rem' }}
            onError={e => { e.target.style.display = 'none'; }}
          />
        </div>
      </div>

      {/* HOURLY PATTERNS LINE CHART */}
      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Diurnal Sensor Cycles (Hourly Averages)</h3>
              <p>Daily honeybee metabolic profiles and weight accumulation patterns</p>
            </div>
            <Calendar size={20} color="var(--accent-cyan)" />
          </div>
          <div className="chart-container" style={{ height: '280px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyPatterns} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hour" stroke="var(--text-secondary)" tickFormatter={h => `${h}:00`} />
                <YAxis yAxisId="left" stroke="var(--accent-cyan)" unit="°C" />
                <YAxis yAxisId="right" orientation="right" stroke="var(--accent-gold)" unit=" kg" />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  labelFormatter={h => `Hour: ${h}:00`}
                />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="temp" name="Avg Temperature" stroke="var(--accent-crimson)" strokeWidth={2.5} dot={false} />
                <Line yAxisId="left" type="monotone" dataKey="humidity" name="Avg Humidity" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="weight" name="Avg Weight" stroke="var(--accent-gold)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* HIVE COMPARISON IMAGE */}
      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Hive Comparison — Python EDA Plot</h3>
              <p>Box plots comparing sensor distributions across all hive units</p>
            </div>
          </div>
          <img
            src={imgUrl('hive_comparison_all_modules.png')}
            alt="Hive Comparison"
            style={{ width: '100%', borderRadius: '8px', marginTop: '0.5rem' }}
            onError={e => { e.target.style.display = 'none'; }}
          />
        </div>
      </div>

    </div>
  );
}
