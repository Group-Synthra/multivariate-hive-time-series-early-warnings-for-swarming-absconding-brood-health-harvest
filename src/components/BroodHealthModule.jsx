import React, { useState } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine, ReferenceArea,
  Cell
} from 'recharts';
import {
  Heart, Activity, TrendingUp, TrendingDown, Minus,
  AlertTriangle, Shield, Thermometer, Droplet, Wind, Scale,
  ChevronDown, ChevronUp, Info
} from 'lucide-react';
import { useBroodHealthData } from '../hooks/useBroodHealthData';

// Color mappings
const HEALTH_COLORS = {
  Excellent: '#10b981',
  Good: '#34d399',
  Poor: '#f59e0b',
  Critical: '#ef4444'
};

const STABILITY_COLORS = {
  High: '#10b981',
  Moderate: '#f59e0b',
  Low: '#ef4444'
};

const TREND_ICONS = {
  'Rapid Improving': <TrendingUp size={16} color="#10b981" />,
  'Slow Improving': <TrendingUp size={16} color="#34d399" />,
  'Stable': <Minus size={16} color="#6b7280" />,
  'Slow Declining': <TrendingDown size={16} color="#f59e0b" />,
  'Rapid Declining': <TrendingDown size={16} color="#ef4444" />
};

// Score definition mapping (for legend)
const SCORE_LEVELS = [
  { range: "80 - 100", level: "Excellent", color: HEALTH_COLORS.Excellent, description: "Ideal brood climate - stable temperature, humidity & CO2" },
  { range: "60 - 80", level: "Good", color: HEALTH_COLORS.Good, description: "Minor deviations, but still favourable for brood development" },
  { range: "40 - 60", level: "Poor", color: HEALTH_COLORS.Poor, description: "Frequent environmental stress - intervene soon" },
  { range: "0 - 40", level: "Critical", color: HEALTH_COLORS.Critical, description: "Dangerous conditions - immediate inspection required" }
];

export default function BroodHealthModule() {
  const { data, loading, error } = useBroodHealthData();
  const [selectedHive, setSelectedHive] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);

  if (loading) return <div className="loader">Loading brood health analytics...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!data) return null;

  const { metrics, summary } = data;
  const hives = [...new Set(metrics.map(m => m.hive))];
  const currentHive = selectedHive || (hives[0] || null);

  // Filter time series for current hive
  const hiveMetrics = metrics.filter(m => m.hive === currentHive).slice(-200);

  // Prepare bar chart data for all hives
  const barData = summary.map(s => ({
    hive: s.hive,
    score: s.current_score,
    bhsi: s.avg_bhsi,
    health: s.health_level
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ borderLeft: '4px solid var(--accent-emerald)' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>🐝 Brood Health Status Prediction</h2>
              <p>
                Continuous, non-invasive assessment using <strong>relative multivariate indices</strong>.
                Scores adapt automatically to each hive's baseline – works for any region, any hive size.
              </p>
            </div>
            <Heart size={48} color="var(--accent-emerald)" />
          </div>
        </div>
      </div>

      {/* Score Definition Legend */}
      <div className="card" style={{ padding: '1rem' }}>
        <div className="chart-header" style={{ marginBottom: '0.75rem' }}>
          <h3>📊 Brood Health Score – Meaning</h3>
          <p>How to interpret the 0–100 score</p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', justifyContent: 'space-between' }}>
          {SCORE_LEVELS.map(level => (
            <div key={level.level} style={{ flex: 1, minWidth: '150px', background: `${level.color}10`, borderRadius: '8px', padding: '0.75rem', borderLeft: `4px solid ${level.color}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong style={{ color: level.color }}>{level.level}</strong>
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{level.range}</span>
              </div>
              <p style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: 'var(--text-secondary)' }}>{level.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Hive Selector */}
      <div className="card" style={{ padding: '0.75rem 1.25rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600 }}>Select Hive:</span>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {hives.map(hive => (
              <button
                key={hive}
                onClick={() => setSelectedHive(hive)}
                className={`badge ${selectedHive === hive ? 'active' : ''}`}
                style={{
                  padding: '0.3rem 0.9rem',
                  background: selectedHive === hive ? 'var(--accent-emerald)' : 'rgba(255,255,255,0.05)',
                  color: selectedHive === hive ? '#0f172a' : 'var(--text-secondary)',
                  border: 'none',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  fontWeight: 500
                }}
              >
                {hive.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Current Hive Stats Cards */}
      {currentHive && (() => {
        const latest = hiveMetrics[hiveMetrics.length - 1];
        if (!latest) return null;
        return (
          <div className="dashboard-grid">
            <div className="card" style={{ background: `linear-gradient(135deg, ${HEALTH_COLORS[latest.health_level]}20, transparent)` }}>
              <div className="stat-header"><span>Brood Health Score</span><Shield size={16} /></div>
              <div className="stat-value" style={{ color: HEALTH_COLORS[latest.health_level] }}>{latest.brood_health_score}</div>
              <div className="stat-footer">{latest.health_level}</div>
            </div>
            <div className="card">
              <div className="stat-header"><span>BHSI (Stability)</span><Activity size={16} /></div>
              <div className="stat-value" style={{ color: STABILITY_COLORS[latest.stability_level] }}>{latest.bhsi}</div>
              <div className="stat-footer">{latest.stability_level} Stability</div>
            </div>
            <div className="card">
              <div className="stat-header"><span>Rate of Deterioration</span>{TREND_ICONS[latest.trend_label]}</div>
              <div className="stat-value">{latest.rod.toFixed(1)}<span className="stat-unit">pts/hr</span></div>
              <div className="stat-footer">{latest.trend_label}</div>
            </div>
          </div>
        );
      })()}

      {/* Main Chart: Brood Health Score + BHSI over time */}
      <div className="card chart-card">
        <div className="chart-header">
          <h3>📈 Brood Health Score & BHSI Timeline</h3>
          <p>Health score (0–100) and stability index over last 200 readings</p>
        </div>
        <div className="chart-container" style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={hiveMetrics}>
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

      {/* Rate of Deterioration (RoD) trend gauge */}
      <div className="dashboard-grid">
        <div className="card chart-card">
          <div className="chart-header"><h3>⏱️ Rate of Deterioration (RoD)</h3><p>Points lost/gained per hour – negative slope = danger</p></div>
          <div className="chart-container" style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hiveMetrics}>
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

        {/* Per-hive bar chart (all hives) */}
        <div className="card chart-card">
          <div className="chart-header"><h3>🏠 Apiary Overview</h3><p>Current Brood Health Score per hive</p></div>
          <div className="chart-container" style={{ height: 250 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hive" stroke="var(--text-secondary)" />
                <YAxis domain={[0, 100]} stroke="var(--text-secondary)" />
                <Tooltip />
                <Bar dataKey="score" fill="var(--accent-emerald)" radius={[4,4,0,0]}>
                  {barData.map((entry, idx) => (
                    <Cell key={`cell-${idx}`} fill={HEALTH_COLORS[entry.health]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Expandable Explanation Section */}
      <div className="card" style={{ padding: '0' }}>
        <button
          onClick={() => setShowExplanation(!showExplanation)}
          style={{
            width: '100%',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1rem',
            background: 'rgba(255,255,255,0.02)',
            border: 'none',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: 600,
            color: 'var(--text-primary)'
          }}
        >
          <span><Info size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} /> How are these scores calculated?</span>
          {showExplanation ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        {showExplanation && (
          <div style={{ padding: '1rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ marginBottom: '1rem' }}>
              <h4 style={{ color: 'var(--accent-emerald)' }}>🐝 Brood Health Score (0–100)</h4>
              <p><strong>What it measures:</strong> How close the hive's internal climate is to <em>its own recent normal</em></p>
              <p><strong>Computation:</strong></p>
              <ul style={{ marginLeft: '1.25rem', color: 'var(--text-secondary)' }}>
                <li>For each hive, we track temperature, humidity, CO2, and weight over the last 7 days (rolling baseline).</li>
                <li>We calculate a <strong>z-score</strong> = (current value - recent average) / recent standard deviation. This tells us how unusual the reading is.</li>
                <li>Each z-score is converted to a sub-score (0–100) using an exponential penalty – big deviations hurt more.</li>
                <li>We apply <strong>biological direction</strong>: too cold is penalised twice as much as too warm; only high CO2 and weight loss are penalised.</li>
                <li>The final score is a weighted average: <strong>40% temperature + 25% humidity + 20% CO2 + 15% weight</strong>.</li>
              </ul>
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <h4 style={{ color: 'var(--accent-cyan)' }}>📊 Brood Health Stability Index (BHSI)</h4>
              <p><strong>What it measures:</strong> How consistent the environment is over the last <strong>6 hours</strong>.</p>
              <p>
                <strong>Computation:</strong> It looks at the coefficient of variation (CoV = standard deviation / mean) of temperature, humidity, and CO2 over a rolling 6-hour window. 
                Lower CoV means more stability. BHSI = 100 - 100 * (average CoV / 0.1). A score {'>='}70 means high stability, {'<'}40 means unstable.
              </p>
            </div>
            <div>
              <h4 style={{ color: 'var(--accent-crimson)' }}>⏱️ Rate of Deterioration (RoD)</h4>
              <p><strong>What it measures:</strong> How fast the Brood Health Score is changing – <strong>negative values mean getting worse</strong>.</p>
              <p>
                <strong>Computation:</strong> Linear regression slope of the health score over the last 4 hours (units = points per hour). 
                Rapid decline ({'<'} -3 points/hr) triggers an alert.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}