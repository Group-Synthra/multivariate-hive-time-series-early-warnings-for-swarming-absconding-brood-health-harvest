import React, { useState, useMemo, useEffect } from 'react';
import {
  Heart, Activity, TrendingUp, TrendingDown, Minus,
  Shield, ChevronDown, ChevronUp, Info, ChevronLeft, ChevronRight
} from 'lucide-react';
import { useBroodHealthData } from '../hooks/useBroodHealthData';
import {
  HealthTimelineChart,
  RodTrendChart,
  ApiaryBarChart
} from './BroodHealthCharts';
import {
  getWindowData,
  getWindowDescription,
  getTotalWindows
} from '../utils/broodHealthHelpers';

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
  const [windowSize, setWindowSize] = useState(200);
  const [windowNumber, setWindowNumber] = useState(0);

  const metrics = data?.metrics || [];
  const summary = data?.summary || [];
  const hives = [...new Set(metrics.map(m => m.hive))];
  const currentHive = selectedHive || (hives[0] || null);

  const fullHiveMetrics = useMemo(() => {
    return metrics
      .filter(m => m.hive === currentHive)
      .sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
  }, [metrics, currentHive]);

  const totalRecords = fullHiveMetrics.length;
  const totalWindows = getTotalWindows(totalRecords, windowSize);

  useEffect(() => {
    if (totalWindows > 0 && windowNumber >= totalWindows) {
      setWindowNumber(totalWindows - 1);
    }
  }, [totalWindows, windowNumber]);

  const windowData = useMemo(() => {
    return getWindowData(fullHiveMetrics, windowNumber, windowSize);
  }, [fullHiveMetrics, windowNumber, windowSize]);

  const windowDesc = getWindowDescription(fullHiveMetrics, windowNumber, windowSize);
  const latest = windowData.length > 0 ? windowData[windowData.length - 1] : null;

  const windowEndTimestamp = useMemo(() => {
    if (windowData.length === 0) return null;
    return windowData[windowData.length - 1].timestamp;
  }, [windowData]);

  const barData = useMemo(() => {
    if (!windowEndTimestamp) return [];

    const endTime = new Date(windowEndTimestamp);
    const hiveLatestInWindow = new Map();

    metrics.forEach(record => {
      const hive = record.hive;
      const recordTime = new Date(record.timestamp);
      if (recordTime > endTime) return; 

      const existing = hiveLatestInWindow.get(hive);
      if (!existing || recordTime > new Date(existing.timestamp)) {
        hiveLatestInWindow.set(hive, record);
      }
    });

    return Array.from(hiveLatestInWindow.values())
      .map(record => ({
        hive: record.hive,
        score: record.brood_health_score,
        health: record.health_level
      }))
      .sort((a, b) => b.score - a.score);
  }, [metrics, windowEndTimestamp]);

  const handlePrev = () => {
    if (windowNumber + 1 < totalWindows) {
      setWindowNumber(windowNumber + 1);
    }
  };

  const handleNext = () => {
    if (windowNumber > 0) {
      setWindowNumber(windowNumber - 1);
    }
  };

  if (loading) return <div className="loader">Loading brood health analytics...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!data) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ borderLeft: '4px solid var(--accent-emerald)' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>🐝 Brood Health Status Prediction</h2>
              <p>Continuous, non‑invasive assessment using relative multivariate indices.</p>
            </div>
            <Heart size={48} color="var(--accent-emerald)" />
          </div>
        </div>
      </div>

      {/* Score Legend */}
      <div className="card" style={{ padding: '1rem' }}>
        <div className="chart-header" style={{ marginBottom: '0.75rem' }}>
          <h3>📊 Brood Health Score – Meaning</h3>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', justifyContent: 'space-between' }}>
          {SCORE_LEVELS.map(level => (
            <div key={level.level} style={{ flex: 1, minWidth: '150px', background: `${level.color}10`, borderRadius: '8px', padding: '0.75rem', borderLeft: `4px solid ${level.color}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong style={{ color: level.color }}>{level.level}</strong>
                <span>{level.range}</span>
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
                onClick={() => { setSelectedHive(hive); setWindowNumber(0); }}
                className={`badge ${selectedHive === hive ? 'active' : ''}`}
                style={{
                  padding: '0.3rem 0.9rem',
                  background: selectedHive === hive ? 'var(--accent-emerald)' : 'rgba(255,255,255,0.05)',
                  color: selectedHive === hive ? '#0f172a' : 'var(--text-secondary)',
                  border: 'none',
                  borderRadius: '20px',
                  cursor: 'pointer'
                }}
              >
                {hive.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Current Hive Stats Cards */}
      {latest && (
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
      )}

      {/* Window Navigation Controls */}
      <div className="card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button onClick={handlePrev} disabled={windowNumber + 1 >= totalWindows} style={{ background: '#2d3748', border: 'none', padding: '0.4rem 0.8rem', borderRadius: '6px', cursor: 'pointer' }}>
            <ChevronLeft size={18} />
          </button>
          <span style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>{windowDesc}</span>
          <button onClick={handleNext} disabled={windowNumber === 0} style={{ background: '#2d3748', border: 'none', padding: '0.4rem 0.8rem', borderRadius: '6px', cursor: 'pointer' }}>
            <ChevronRight size={18} />
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem' }}>Window size:</span>
          <select value={windowSize} onChange={(e) => { setWindowSize(Number(e.target.value)); setWindowNumber(0); }} style={{ background: '#1e293b', border: '1px solid #334155', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
            <option value={1000}>1000</option>
          </select>
        </div>
      </div>

      {/* Charts using current window data */}
      <HealthTimelineChart data={windowData} />
      <div className="dashboard-grid">
        <RodTrendChart data={windowData} />
        {/* Bar chart now shows scores at the END of the current window */}
        <ApiaryBarChart data={barData} colors={HEALTH_COLORS} />
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