import { useState } from 'react';
import {
  Activity, RefreshCw, Database, AlertTriangle, Home, Heart,
  Wind, Zap, Award, BarChart2, CheckCircle, XCircle, Loader
} from 'lucide-react';

import { useEDAData } from './hooks/useEDAData';
import CommonEDA from './components/CommonEDA';
import BroodHealthModule from './components/BroodHealthModule';
import SwarmingModule from './components/SwarmingModule';
import AbscondingModule from './components/AbscondingModule';
import HarvestingModule from './components/HarvestingModule';
import { processHiveData } from './utils/dataProcessor';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const { edaData, loading, error, refetch } = useEDAData();
  const processedData = processHiveData(edaData?.raw_data || []);
  if (processedData && edaData?.swarming_patterns) {
    processedData.swarmingPatterns = edaData.swarming_patterns;
  }
  // ── Loading State ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{
        display: 'flex', height: '100vh', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center',
        background: 'var(--bg-gradient-end)', gap: '1rem'
      }}>
        <Loader size={40} color="var(--accent-gold)"
          style={{ animation: 'spin 1.2s linear infinite' }} />
        <div style={{ color: 'var(--accent-gold)', fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 600 }}>
          Loading Apiary Analytics…
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Fetching EDA data from the backend API
        </p>
      </div>
    );
  }

  // ── Error State ──────────────────────────────────────────────────────────
  if (error) {
    return (
      <div style={{
        display: 'flex', height: '100vh', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center',
        background: 'var(--bg-gradient-end)', gap: '1rem', padding: '2rem'
      }}>
        <XCircle size={48} color="var(--accent-crimson)" />
        <div style={{ color: 'var(--accent-crimson)', fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700 }}>
          Backend Not Available
        </div>
        <div className="card" style={{ maxWidth: '560px', textAlign: 'center', padding: '1.5rem' }}>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            {error}
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.25rem', textAlign: 'left', lineHeight: 1.8 }}>
            To start the backend:<br />
            <code style={{ background: 'rgba(255,255,255,0.05)', padding: '0.2rem 0.4rem', borderRadius: '4px' }}>
              1. python run_eda.py
            </code><br />
            <code style={{ background: 'rgba(255,255,255,0.05)', padding: '0.2rem 0.4rem', borderRadius: '4px' }}>
              2. python backend/app.py
            </code>
          </p>
          <button className="upload-btn" onClick={refetch}>
            <RefreshCw size={16} /> Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // ── Helper: safely access nested edaData fields ──────────────────────────
  const summary = edaData?.summary || {};
  const sensorStats = edaData?.sensor_statistics || {};
  const outlierAnalysis = edaData?.outlier_analysis || {};
  const anomalies = edaData?.anomalies || {};
  const moduleInsights = edaData?.module_insights || {};
  const broodPerHive = edaData?.brood_health_per_hive || [];

  const totalActiveAlerts =
    (anomalies.co2_spikes > 0 ? 1 : 0) +
    (anomalies.weight_drops > 5 ? 1 : 0) +
    broodPerHive.filter(h => h.status === 'Needs Attention').length;

  return (
    <div className="app-container">
      {/* HEADER */}
      <header className="app-header">
        <div className="brand-section">
          <Activity size={32} className="brand-icon" />
          <div className="brand-title">
            <h1>HiveEDA Dashboard</h1>
            <p>Smart Apiary Telemetry &amp; Biological Predictive Analytics</p>
          </div>
        </div>

        <div className="controls-section">
          <div className="data-status">
            <span className="status-dot"></span>
            <span style={{ color: 'var(--text-secondary)' }}>Source:</span>
            <span style={{ fontWeight: 600 }}>Live EDA — Python Backend</span>
          </div>
          <button className="upload-btn" onClick={refetch}>
            <RefreshCw size={16} />
            Refresh Analysis
          </button>
        </div>
      </header>

      {/* TABS NAVIGATION */}
      <nav className="tab-navigation">
        <button
          id="tab-overview"
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <Home size={16} /> Overview
        </button>
        <button
          id="tab-common"
          className={`tab-btn ${activeTab === 'common' ? 'active' : ''}`}
          onClick={() => setActiveTab('common')}
        >
          <BarChart2 size={16} /> Common Data EDA
        </button>
        <button
          id="tab-brood"
          className={`tab-btn ${activeTab === 'brood' ? 'active' : ''}`}
          onClick={() => setActiveTab('brood')}
        >
          <Heart size={16} /> 1. Brood Health
        </button>
        <button
          id="tab-swarming"
          className={`tab-btn ${activeTab === 'swarming' ? 'active' : ''}`}
          onClick={() => setActiveTab('swarming')}
        >
          <Zap size={16} /> 2. Colony Swarming
        </button>
        <button
          id="tab-absconding"
          className={`tab-btn ${activeTab === 'absconding' ? 'active' : ''}`}
          onClick={() => setActiveTab('absconding')}
        >
          <Wind size={16} /> 3. Absconding Risk
        </button>
        <button
          id="tab-harvest"
          className={`tab-btn ${activeTab === 'harvest' ? 'active' : ''}`}
          onClick={() => setActiveTab('harvest')}
        >
          <Award size={16} /> 4. Honey Harvesting
        </button>
      </nav>

      {/* TAB CONTENT */}
      <main className="tab-content" style={{ animation: 'fadeIn 0.4s ease-out' }}>

        {/* ── OVERVIEW TAB ──────────────────────────────────────────── */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

            {/* Welcome Banner */}
            <div className="dashboard-grid">
              <div className="card welcome-card">
                <div className="welcome-content">
                  <div className="welcome-text">
                    <h2>Welcome to the Hive Analytics Console</h2>
                    <p>
                      Real-time biological intelligence powered by Python EDA analysis.
                      Dataset spans <strong>{summary.analysis_start?.substring(0, 10)}</strong> to <strong>{summary.analysis_end?.substring(0, 10)}</strong>.
                      Select a module tab to drill into specific predictive analytics.
                    </p>
                  </div>
                  <div className="quick-stats-row">
                    <div className="quick-stat-item">
                      <div className="quick-stat-label">Total Hives</div>
                      <div className="quick-stat-value">{summary.total_hives ?? '—'}</div>
                    </div>
                    <div className="quick-stat-item">
                      <div className="quick-stat-label">Total Records</div>
                      <div className="quick-stat-value">{summary.total_records?.toLocaleString() ?? '—'}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Summary Cards */}
            <div className="dashboard-grid">
              <div className="card highlight-gold">
                <div className="stat-header">
                  <span>Tracked Hive Units</span>
                  <Database size={16} color="var(--accent-gold)" />
                </div>
                <div className="stat-value">{summary.total_hives ?? '—'}</div>
                <div className="stat-footer">Active colony clusters in dataset</div>
              </div>

              <div className="card highlight-cyan">
                <div className="stat-header">
                  <span>Processed Records</span>
                  <Activity size={16} color="var(--accent-cyan)" />
                </div>
                <div className="stat-value">{summary.total_records?.toLocaleString() ?? '—'}</div>
                <div className="stat-footer">Sensor readings evaluated by EDA</div>
              </div>

              <div className="card highlight-crimson">
                <div className="stat-header">
                  <span>Active Alerts</span>
                  <AlertTriangle size={16} color="var(--accent-crimson)" />
                </div>
                <div className="stat-value"
                  style={{ color: totalActiveAlerts > 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)' }}>
                  {totalActiveAlerts}
                </div>
                <div className="stat-footer">Swarm, absconding, or brood alerts</div>
              </div>
            </div>

            {/* Sensor Stats Grid */}
            <div className="dashboard-grid">
              {/* Temperature */}
              <div className="card highlight-crimson">
                <div className="stat-header">
                  <span>Temperature</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>°C</span>
                </div>
                <div className="stat-value">
                  {sensorStats.temperature?.mean ?? '—'}
                  <span className="stat-unit">avg</span>
                </div>
                <div className="stat-footer">
                  <span>Min: {sensorStats.temperature?.min ?? '—'} | Max: {sensorStats.temperature?.max ?? '—'}</span>
                </div>
              </div>

              {/* Humidity */}
              <div className="card highlight-cyan">
                <div className="stat-header">
                  <span>Humidity</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>%</span>
                </div>
                <div className="stat-value">
                  {sensorStats.humidity?.mean ?? '—'}
                  <span className="stat-unit">avg</span>
                </div>
                <div className="stat-footer">
                  <span>Range: {sensorStats.humidity?.min ?? '—'} – {sensorStats.humidity?.max ?? '—'}%</span>
                </div>
              </div>

              {/* Weight */}
              <div className="card highlight-gold">
                <div className="stat-header">
                  <span>Hive Weight</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>kg</span>
                </div>
                <div className="stat-value">
                  {sensorStats.weight?.mean ?? '—'}
                  <span className="stat-unit">avg</span>
                </div>
                <div className="stat-footer">
                  <span>Range: {sensorStats.weight?.min ?? '—'} – {sensorStats.weight?.max ?? '—'} kg</span>
                </div>
              </div>

              {/* CO2 */}
              <div className="card highlight-emerald">
                <div className="stat-header">
                  <span>CO2 Concentration</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ppm</span>
                </div>
                <div className="stat-value">
                  {sensorStats.co2?.mean ?? '—'}
                  <span className="stat-unit">avg</span>
                </div>
                <div className="stat-footer">
                  <span>Range: {sensorStats.co2?.min ?? '—'} – {sensorStats.co2?.max ?? '—'} ppm</span>
                </div>
              </div>
            </div>

            {/* Module Overview Cards */}
            <div className="dashboard-grid">
              <div className="card">
                <div className="chart-header">
                  <div className="chart-title">
                    <h3>Biological Predictive Engines</h3>
                    <p>Core intelligence modules powering this dashboard</p>
                  </div>
                </div>
                <div className="recs-container" style={{ marginTop: '1rem' }}>
                  <div className="rec-item">
                    <Heart size={18} color="var(--accent-emerald)" style={{ flexShrink: 0 }} />
                    <div className="rec-text">
                      <h4 style={{ color: 'var(--accent-emerald)' }}>1. Brood Health Status</h4>
                      <p>Evaluates thermal and humidity stability against physiological tolerances.</p>
                    </div>
                  </div>
                  <div className="rec-item">
                    <Zap size={18} color="var(--accent-crimson)" style={{ flexShrink: 0 }} />
                    <div className="rec-text">
                      <h4 style={{ color: 'var(--accent-crimson)' }}>2. Colony Swarming</h4>
                      <p>Detects abrupt weight changes with CO2 and temperature spikes.</p>
                    </div>
                  </div>
                  <div className="rec-item">
                    <Wind size={18} color="var(--accent-gold)" style={{ flexShrink: 0 }} />
                    <div className="rec-text">
                      <h4 style={{ color: 'var(--accent-gold)' }}>3. Absconding Behavior</h4>
                      <p>Identifies slow-moving depopulation before full colony loss.</p>
                    </div>
                  </div>
                  <div className="rec-item">
                    <Award size={18} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
                    <div className="rec-text">
                      <h4 style={{ color: 'var(--accent-cyan)' }}>4. Optimal Harvesting</h4>
                      <p>Calculates weight plateaus to schedule maximum yield extraction.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Anomaly summary card */}
              <div className="card highlight-crimson">
                <div className="chart-header">
                  <div className="chart-title">
                    <h3>Anomaly Detection Summary</h3>
                    <p>From Python EDA pipeline</p>
                  </div>
                  <AlertTriangle size={20} color="var(--accent-crimson)" />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
                  {[
                    { label: 'Temp Anomalies (|dev| > 1°C)', value: anomalies.temperature_anomalies ?? '—' },
                    { label: 'Weight Drops (< -0.5 kg)', value: anomalies.weight_drops ?? '—' },
                    { label: 'CO2 Spikes (> 1800 ppm)', value: anomalies.co2_spikes ?? '—' },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.03)' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{label}</span>
                      <span style={{ fontWeight: 700, fontFamily: 'var(--font-display)', color: Number(value) > 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)' }}>
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Global Alert Banner */}
            {totalActiveAlerts > 0 && (
              <div className="alert-banner">
                <AlertTriangle size={20} style={{ flexShrink: 0 }} />
                <div>
                  <strong>Apiary Alert Summary:</strong> Python EDA detected {anomalies.co2_spikes} CO2 spikes, {anomalies.weight_drops} weight drops, and {broodPerHive.filter(h => h.status === 'Needs Attention').length} hive(s) with poor brood climate control. Open individual tabs for full diagnostics.
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── MODULE TABS ─────────────────────────────────────────────── */}
        {activeTab === 'common' && <CommonEDA edaData={edaData} />}
        {activeTab === 'brood' && (
          <BroodHealthModule data={edaData?.raw_data || []}
            processed={processedData} />)}
        {activeTab === 'swarming' && (
          <SwarmingModule
            data={edaData?.raw_data || []}
            processed={processedData}
          />
        )}
        {activeTab === 'absconding' && (
          <AbscondingModule data={edaData?.raw_data || []}
            processed={processedData} />)}
        {activeTab === 'harvest' && (<HarvestingModule
          data={edaData?.raw_data || []}
          processed={processedData}
        />)}


      </main>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
}

export default App;
