import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle, Wind, TrendingUp, ShieldCheck, Activity, Info, RefreshCw,
  Database, Award, Eye, GitCompare, BarChart2, Brain, Zap, CheckCircle, RadioTower,
  SlidersHorizontal
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, Cell
} from 'recharts';

import { useAbscondingData } from '../hooks/useAbscondingData';

const imgUrl = (filename) => `/api/absconding/images/${filename}`;

function levelColor(level) {
  if (level === 'High') return 'var(--accent-crimson)';
  if (level === 'Medium') return 'var(--accent-gold)';
  return 'var(--accent-emerald)';
}

function percent(value, digits = 1) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(digits)}%`;
}

function metricPercent(row, key) {
  const val = row?.[key];
  if (val === undefined || val === null || Number.isNaN(Number(val))) return '—';
  return `${(Number(val) * 100).toFixed(2)}%`;
}

function numberValue(value, digits = 2, suffix = '') {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(digits)}${suffix}`;
}

function shortDateTime(value) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value).slice(0, 16);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:00`;
}

function SectionTabs({ activeView, setActiveView }) {
  const tabs = [
    { key: 'eda', label: 'Exploratory Analysis', icon: BarChart2, color: 'var(--accent-emerald)' },
    { key: 'training', label: 'Model Training', icon: Brain, color: 'var(--accent-cyan)' },
    { key: 'live', label: 'Live Prediction (IoT)', icon: Zap, color: 'var(--accent-gold)' },
  ];
  return (
    <nav className="tab-navigation" style={{ marginTop: 0 }}>
      {tabs.map(tab => {
        const Icon = tab.icon;
        return (
          <button
            key={tab.key}
            className={`tab-btn ${activeView === tab.key ? 'active' : ''}`}
            onClick={() => setActiveView(tab.key)}
            style={activeView === tab.key ? { background: tab.color, color: '#05111f', boxShadow: `0 0 18px ${tab.color}55` } : {}}
          >
            <Icon size={16} /> {tab.label}
          </button>
        );
      })}
    </nav>
  );
}

function RiskMeaningCard() {
  const rows = [
    { label: 'Low', range: '0 – 35', text: 'Normal colony conditions. Continue routine monitoring.', color: 'var(--accent-emerald)' },
    { label: 'Medium', range: '35 – 70', text: 'Early instability pattern. Monitor queen, food stores, ventilation, and disturbance.', color: 'var(--accent-gold)' },
    { label: 'High', range: '70 – 100', text: 'High probability or fast ARM escalation. Immediate inspection recommended.', color: 'var(--accent-crimson)' },
  ];
  return (
    <div className="card" style={{ gridColumn: 'span 3' }}>
      <div className="chart-header">
        <div className="chart-title"><h3>Absconding Risk Score — Meaning</h3><p>Risk is based on model probability plus ARM escalation trend.</p></div>
        <SlidersHorizontal size={18} color="var(--text-secondary)" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '1rem', marginTop: '1rem' }}>
        {rows.map(row => (
          <div key={row.label} style={{ borderLeft: `4px solid ${row.color}`, padding: '0.9rem', borderRadius: '10px', background: 'rgba(255,255,255,0.04)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
              <strong style={{ color: row.color }}>{row.label}</strong>
              <strong>{row.range}</strong>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginTop: '0.45rem', lineHeight: 1.5 }}>{row.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ title, value, footer, icon: Icon, color = 'var(--accent-gold)', className = '' }) {
  return (
    <div className={`card ${className}`}>
      <div className="stat-header"><span>{title}</span>{Icon && <Icon size={16} color={color} />}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-footer">{footer}</div>
    </div>
  );
}

export default function AbscondingModule({ edaData }) {
  const { abscondingData, abscondingLoading, abscondingError, refetchAbsconding } = useAbscondingData();
  const [activeView, setActiveView] = useState('eda');
  const [selectedHive, setSelectedHive] = useState('');

  const fallbackInsight = edaData?.module_insights?.absconding || '';
  const summary = abscondingData?.summary || {};
  const metrics = abscondingData?.model_metrics || {};
  const perHive = abscondingData?.per_hive_absconding_risk || [];
  const alerts = abscondingData?.alerts || [];
  const hiveOptions = abscondingData?.hive_options || perHive.map(h => h.hive);
  const hiveDetails = abscondingData?.hive_details || {};
  const modelComparison = abscondingData?.model_comparison || [];
  const rationale = abscondingData?.model_selection_rationale || {};
  const features = abscondingData?.feature_importance || [];
  const thresholds = abscondingData?.risk_thresholds || {};

  useEffect(() => {
    if (!selectedHive && hiveOptions.length > 0) setSelectedHive(hiveOptions[0]);
  }, [hiveOptions, selectedHive]);

  const selectedDetail = hiveDetails[selectedHive] || {};
  const selectedLatest = selectedDetail.latest || perHive.find(h => h.hive === selectedHive) || null;
  const selectedTimeline = selectedDetail.timeline || [];

  const riskBarData = useMemo(() => perHive.slice(0, 15).map(h => ({
    hive: h.hive,
    risk: Number(h.risk_percentage || 0),
    arm: Number((h.arm || 0) * 100),
    level: h.risk_level,
  })), [perHive]);

  const modelChartData = useMemo(() => modelComparison
    .filter(m => m.f1_score !== undefined)
    .map(m => ({
      model: (m.model_name || m.model_key || 'Model')
        .replace(' + Time-Series Features', '')
        .replace(' + Time-Series Sequence', ' + Seq')
        .replace('Environmental Stress ', 'Stress '),
      recall: Number((m.recall || 0) * 100),
      f1: Number((m.f1_score || 0) * 100),
      prAuc: Number((m.pr_auc || 0) * 100),
      defence: Number((m.defence_score || 0) * 100),
    })), [modelComparison]);

  const featureData = useMemo(() => features.slice(0, 12).map(f => ({
    feature: (f.feature || '').replaceAll('_', ' '),
    importance: Number(f.importance || 0),
  })), [features]);

  const riskTimelineData = useMemo(() => selectedTimeline.map(row => ({
    time: shortDateTime(row.timestamp),
    risk: Number(row.risk_percentage || 0),
    arm: Number((row.arm || 0) * 100),
    stress: Number((row.environmental_stress_score || 0) * 100),
    actual: Number(row.actual_next_72h_label || 0) * 100,
  })), [selectedTimeline]);

  const sensorTimelineData = useMemo(() => selectedTimeline.map(row => ({
    time: shortDateTime(row.timestamp),
    temp: Number(row.temperature_c || 0),
    humidity: Number(row.humidity_pct || 0),
    weight: Number(row.weight_kg || 0),
    co2Scaled: Number((row.co2_ppm || 0) / 100),
  })), [selectedTimeline]);

  if (abscondingLoading) {
    return (
      <div className="card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <RefreshCw size={20} color="var(--accent-gold)" style={{ animation: 'spin 1.2s linear infinite' }} />
          <span>Loading Absconding Prediction Module…</span>
        </div>
      </div>
    );
  }

  if (abscondingError) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <SectionTabs activeView={activeView} setActiveView={setActiveView} />
        <div className="card highlight-crimson">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Absconding Prediction Module Not Generated Yet</h3>
              <p>{abscondingError}</p>
            </div>
            <AlertTriangle size={24} color="var(--accent-crimson)" />
          </div>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            Run <code>python backend/scripts/run_absconding.py --model best_classical --compare-models</code>, then restart your backend.
            For final LSTM proof, run <code>python backend/ml/absconding/lstm_absconding.py</code> in Google Colab/GPU and rerun the backend script.
          </p>
          <p style={{ color: 'var(--text-muted)' }}>{fallbackInsight}</p>
          <button className="upload-btn" onClick={refetchAbsconding}><RefreshCw size={16} /> Retry</button>
        </div>
      </div>
    );
  }

  const EDAView = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ gridColumn: 'span 3' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>🌬️ Absconding Behaviour Prediction</h2>
              <p>
                Proactive colony abandonment warning using temperature, humidity, CO₂, hive weight,
                time-series features, ARM, and explainable risk factors.
              </p>
            </div>
            <Wind size={46} color="var(--accent-gold)" />
          </div>
        </div>
      </div>

      <div className="dashboard-grid"><RiskMeaningCard /></div>

      <div className="dashboard-grid">
        <div className="card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Select Hive</h3>
              <p>Select any hive and the whole dashboard changes to that hive’s risk, ARM, sensors, and explanation.</p>
            </div>
            <Eye size={18} color="var(--accent-gold)" />
          </div>
          <div style={{ display: 'flex', gap: '0.85rem', flexWrap: 'wrap', alignItems: 'center', marginTop: '1rem' }}>
            <select className="chart-select" value={selectedHive} onChange={e => setSelectedHive(e.target.value)} style={{ minWidth: '230px', padding: '0.75rem', borderRadius: '8px' }}>
              {hiveOptions.map(hive => <option key={hive} value={hive}>{hive}</option>)}
            </select>
            {selectedLatest && (
              <div style={{ color: 'var(--text-secondary)' }}>
                Current status: <strong style={{ color: levelColor(selectedLatest.risk_level) }}>{selectedLatest.risk_level}</strong>
                {' '}risk — {numberValue(selectedLatest.risk_percentage, 2, '%')}, ARM {numberValue(selectedLatest.arm, 4)} ({selectedLatest.arm_trend})
              </div>
            )}
          </div>
        </div>
      </div>

      {selectedLatest && (
        <div className="dashboard-grid">
          <StatCard title="Absconding Risk" value={numberValue(selectedLatest.risk_percentage, 1, '%')} footer={`${selectedLatest.risk_level} | ${selectedLatest.arm_trend}`} icon={Wind} color={levelColor(selectedLatest.risk_level)} className="highlight-crimson" />
          <StatCard title="ARM" value={numberValue(selectedLatest.arm, 4)} footer="Risk momentum per hour" icon={TrendingUp} color="var(--accent-gold)" className="highlight-gold" />
          <StatCard title="Environmental Stress" value={numberValue((selectedLatest.latest_sensor_readings?.environmental_stress_score || 0) * 100, 1, '%')} footer="Combined temp + humidity + CO₂ + weight stress" icon={Activity} color="var(--accent-cyan)" className="highlight-cyan" />
        </div>
      )}

      {selectedTimeline.length > 0 && (
        <div className="dashboard-grid">
          <div className="card chart-card" style={{ gridColumn: 'span 3' }}>
            <div className="chart-header">
              <div className="chart-title"><h3>{selectedHive} — Absconding Risk, ARM and Stress Timeline</h3><p>Shows how probability and risk momentum change through time.</p></div>
            </div>
            <div className="chart-container" style={{ height: '340px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={riskTimelineData} margin={{ top: 10, right: 30, left: -10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="time" stroke="var(--text-secondary)" minTickGap={40} />
                  <YAxis stroke="var(--text-secondary)" unit="%" />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} formatter={(v) => [`${Number(v).toFixed(2)}%`, '']} />
                  <Legend />
                  <Line type="monotone" dataKey="risk" name="Risk %" stroke="var(--accent-crimson)" strokeWidth={3} dot={false} />
                  <Line type="monotone" dataKey="arm" name="ARM ×100" stroke="var(--accent-gold)" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="stress" name="Stress ×100" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title"><h3>{selectedHive} — Sensor Behaviour</h3><p>Temperature, humidity, weight, and scaled CO₂ over recent readings.</p></div>
          </div>
          <div className="chart-container" style={{ height: '310px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sensorTimelineData} margin={{ top: 10, right: 30, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" stroke="var(--text-secondary)" minTickGap={40} />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Legend />
                <Line type="monotone" dataKey="temp" name="Temp °C" stroke="var(--accent-crimson)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="humidity" name="Humidity %" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="weight" name="Weight kg" stroke="var(--accent-gold)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="co2Scaled" name="CO₂ /100" stroke="var(--accent-emerald)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="chart-header">
            <div className="chart-title"><h3>{selectedHive} — Explainable Risk Analysis</h3><p>Readable reasons for the current risk level.</p></div>
            <Info size={18} color="var(--text-secondary)" />
          </div>
          {(selectedLatest?.key_factors || []).map((factor, index) => (
            <div key={`${factor.factor}-${index}`} style={{ marginTop: '0.75rem', padding: '0.8rem', borderRadius: '8px', background: 'rgba(255,255,255,0.04)' }}>
              <strong>{factor.factor}</strong>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.45 }}>
                Value: {factor.value} {factor.unit} — {factor.interpretation}
              </div>
            </div>
          ))}
          <div style={{ marginTop: '1rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            <strong>Recommended action:</strong> {selectedLatest?.alert_required ? 'Immediate hive inspection: check queen, food stores, ventilation, pests, and disturbance.' : 'Continue monitoring and inspect if ARM rises.'}
          </div>
        </div>
      </div>
    </div>
  );

  const TrainingView = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="dashboard-grid">
        <div className="card highlight-emerald" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3><CheckCircle size={22} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} /> Model Training Complete</h3>
              <p>
                Active backend model: <strong>{summary.active_backend_model || metrics.model_name || '—'}</strong> | Training records: {metrics.training_records?.toLocaleString?.() ?? '—'} | Test records: {metrics.testing_records?.toLocaleString?.() ?? '—'}
              </p>
            </div>
            <Brain size={26} color="var(--accent-emerald)" />
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title"><h3>Model Performance Comparison</h3><p>Higher Recall/F1/PR-AUC and Defence Score are better for early warnings.</p></div>
            <GitCompare size={18} color="var(--accent-gold)" />
          </div>
          <div className="chart-container" style={{ height: '360px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelChartData} margin={{ top: 10, right: 20, left: -10, bottom: 85 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="model" stroke="var(--text-secondary)" angle={-30} textAnchor="end" interval={0} height={95} />
                <YAxis stroke="var(--text-secondary)" unit="%" />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} formatter={(v) => [`${Number(v).toFixed(2)}%`, '']} />
                <Legend />
                <Bar dataKey="recall" name="Recall" fill="var(--accent-crimson)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="f1" name="F1" fill="var(--accent-gold)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="prAuc" name="PR-AUC" fill="var(--accent-cyan)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="chart-header">
            <div className="chart-title"><h3>Why LSTM + Time Series?</h3></div>
            <Award size={18} color="var(--accent-cyan)" />
          </div>
          <div style={{ color: 'var(--text-secondary)', lineHeight: 1.75 }}>
            <p><strong>Best by generated metrics:</strong> {rationale.best_model_by_defence_score || 'Run comparison first'}</p>
            <p><strong>LSTM metrics available:</strong> {rationale.lstm_metrics_available ? 'Yes' : 'No — run LSTM script/Colab first'}</p>
            <p><strong>LSTM selected:</strong> {rationale.is_lstm_best ? 'Yes, by defence score' : 'Pending real LSTM metrics or not the best yet'}</p>
            {(rationale.why_lstm_is_defensible || []).slice(0, 4).map((point, i) => (
              <div key={i} style={{ marginTop: '0.6rem', padding: '0.65rem', borderRadius: '8px', background: 'rgba(255,255,255,0.04)' }}>{point}</div>
            ))}
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title"><h3>Detailed Model Comparison Table</h3><p>Includes rule baseline, several classical time-series feature models, and LSTM sequence model when generated.</p></div>
          </div>
          <div className="table-container">
            <table className="custom-table">
              <thead><tr><th>Model</th><th>Family</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>PR-AUC</th><th>ROC-AUC</th><th>MAE</th><th>RMSE</th><th>Defence Score</th><th>Status</th></tr></thead>
              <tbody>
                {modelComparison.map((m, index) => (
                  <tr key={`${m.model_key || m.model_name}-${index}`}>
                    <td style={{ fontWeight: 700 }}>{m.model_name || m.model_key}</td>
                    <td>{m.model_family || '—'}</td>
                    <td>{metricPercent(m, 'accuracy')}</td>
                    <td>{metricPercent(m, 'precision')}</td>
                    <td>{metricPercent(m, 'recall')}</td>
                    <td>{metricPercent(m, 'f1_score')}</td>
                    <td>{metricPercent(m, 'pr_auc')}</td>
                    <td>{metricPercent(m, 'roc_auc')}</td>
                    <td>{m.mae ?? '—'}</td>
                    <td>{m.rmse ?? '—'}</td>
                    <td>{metricPercent(m, 'defence_score')}</td>
                    <td style={{ color: m.error ? 'var(--accent-crimson)' : 'var(--text-secondary)' }}>{m.error || m.status || 'Done'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <div className="chart-header"><div className="chart-title"><h3>Active Model Metrics</h3><p>Time-based test split, not random shuffle</p></div><Activity size={18} color="var(--accent-gold)" /></div>
          <div className="table-container">
            <table className="custom-table"><tbody>
              <tr><td>Accuracy</td><td>{metricPercent(metrics, 'accuracy')}</td></tr>
              <tr><td>Precision</td><td>{metricPercent(metrics, 'precision')}</td></tr>
              <tr><td>Recall</td><td>{metricPercent(metrics, 'recall')}</td></tr>
              <tr><td>F1 Score</td><td>{metricPercent(metrics, 'f1_score')}</td></tr>
              <tr><td>ROC-AUC</td><td>{metrics.roc_auc ?? '—'}</td></tr>
              <tr><td>PR-AUC</td><td>{metrics.pr_auc ?? '—'}</td></tr>
              <tr><td>MAE</td><td>{metrics.mae ?? '—'}</td></tr>
              <tr><td>RMSE</td><td>{metrics.rmse ?? '—'}</td></tr>
              <tr><td>Decision Threshold</td><td>{metrics.threshold ?? '—'}</td></tr>
            </tbody></table>
          </div>
        </div>

        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header"><div className="chart-title"><h3>Top Explainable Features</h3><p>Feature importance from the active backend model</p></div><Info size={18} color="var(--text-secondary)" /></div>
          <div className="chart-container" style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featureData} layout="vertical" margin={{ top: 10, right: 20, left: 95, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" stroke="var(--text-secondary)" />
                <YAxis type="category" dataKey="feature" stroke="var(--text-secondary)" width={130} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Bar dataKey="importance" name="Importance" fill="var(--accent-gold)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <div className="chart-header"><div className="chart-title"><h3>Confusion Matrix</h3><p>Classification performance of active model</p></div></div>
          <img src={imgUrl('absconding_confusion_matrix.png')} alt="Absconding confusion matrix" style={{ width: '100%', borderRadius: '8px', marginTop: '0.75rem' }} onError={e => { e.target.style.display = 'none'; }} />
        </div>
        <div className="card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header"><div className="chart-title"><h3>Training Design Summary</h3></div><ShieldCheck size={18} color="var(--accent-emerald)" /></div>
          <div style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            <p><strong>Target:</strong> {metrics.target_column || 'absconding_label_next_72h'} — early warning label for next 72 hours.</p>
            <p><strong>Split:</strong> Time-based split, so future records are tested after older training records.</p>
            <p><strong>Inputs:</strong> temperature, humidity, CO₂, weight, external weather proxies, rolling windows, trend, and stress features.</p>
            <p><strong>Thresholds:</strong> Low {thresholds.low || '<0.35'}, Medium {thresholds.medium || '0.35–0.70'}, High {thresholds.high || '>=0.70'}, ARM escalation {thresholds.arm_escalation || '>=0.08'}.</p>
            <p><strong>Selection logic:</strong> model comparison prioritizes Recall and F1 because missing an absconding event causes complete colony loss.</p>
          </div>
        </div>
      </div>
    </div>
  );

  const LiveView = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ gridColumn: 'span 3' }}>
          <div className="welcome-content">
            <div className="welcome-text"><h2>Live Absconding Prediction View</h2><p>Designed for IoT use: latest reading per hive, generated alert message, and immediate action recommendation.</p></div>
            <RadioTower size={44} color="var(--accent-cyan)" />
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <StatCard title="High Risk Hives" value={summary.high_risk_hives ?? 0} footer="Immediate inspection" icon={AlertTriangle} color="var(--accent-crimson)" className="highlight-crimson" />
        <StatCard title="Medium Risk Hives" value={summary.medium_risk_hives ?? 0} footer="Monitor closely" icon={TrendingUp} color="var(--accent-gold)" className="highlight-gold" />
        <StatCard title="Latest Alerts" value={summary.latest_alerts ?? alerts.length} footer="Generated from risk + ARM" icon={Wind} color="var(--accent-cyan)" className="highlight-cyan" />
      </div>

      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header"><div className="chart-title"><h3>Latest Absconding Risk by Hive</h3><p>Top hives by latest predicted probability.</p></div></div>
          <div className="chart-container" style={{ height: '330px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskBarData} margin={{ top: 10, right: 20, left: -10, bottom: 65 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hive" stroke="var(--text-secondary)" angle={-25} textAnchor="end" height={75} />
                <YAxis stroke="var(--text-secondary)" unit="%" />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} formatter={(v, n) => [`${Number(v).toFixed(2)}%`, n === 'risk' ? 'Risk' : 'ARM ×100']} />
                <Legend />
                <Bar dataKey="risk" name="Risk %" radius={[4, 4, 0, 0]}>
                  {riskBarData.map((entry, idx) => <Cell key={idx} fill={levelColor(entry.level)} />)}
                </Bar>
                <Bar dataKey="arm" name="ARM ×100" fill="var(--accent-gold)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="chart-header"><div className="chart-title"><h3>Current Hive Reading</h3><p>{selectedHive} latest prediction and sensors.</p></div></div>
          <select className="chart-select" value={selectedHive} onChange={e => setSelectedHive(e.target.value)} style={{ width: '100%', padding: '0.75rem', marginTop: '0.7rem' }}>
            {hiveOptions.map(hive => <option key={hive} value={hive}>{hive}</option>)}
          </select>
          {selectedLatest && (
            <div style={{ marginTop: '1rem', display: 'grid', gap: '0.65rem', color: 'var(--text-secondary)' }}>
              <div><strong style={{ color: levelColor(selectedLatest.risk_level) }}>{selectedLatest.risk_level}</strong> — {numberValue(selectedLatest.risk_percentage, 2, '%')}</div>
              <div>ARM: {numberValue(selectedLatest.arm, 4)} ({selectedLatest.arm_trend})</div>
              <div>Temperature: {numberValue(selectedLatest.latest_sensor_readings?.temperature_c, 2, '°C')}</div>
              <div>Humidity: {numberValue(selectedLatest.latest_sensor_readings?.humidity_pct, 2, '%')}</div>
              <div>CO₂: {numberValue(selectedLatest.latest_sensor_readings?.co2_ppm, 0, ' ppm')}</div>
              <div>Weight: {numberValue(selectedLatest.latest_sensor_readings?.weight_kg, 2, ' kg')}</div>
              <div style={{ padding: '0.75rem', borderRadius: '8px', background: 'rgba(255,255,255,0.04)' }}>{selectedLatest.message}</div>
            </div>
          )}
        </div>
      </div>

      {alerts.length > 0 ? (
        <div className="dashboard-grid">
          <div className="card highlight-crimson" style={{ gridColumn: 'span 3' }}>
            <div className="chart-header"><div className="chart-title"><h3>Early Warning Alerts</h3><p>Generated when risk or ARM trend crosses threshold.</p></div><AlertTriangle size={22} color="var(--accent-crimson)" /></div>
            {alerts.map(alert => (
              <div key={alert.hive} style={{ padding: '0.9rem', marginTop: '0.75rem', border: '1px solid rgba(248,113,113,0.35)', borderRadius: '10px', background: 'rgba(248,113,113,0.08)' }}>
                <strong>{alert.hive}</strong> — {alert.message}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="card highlight-emerald"><strong>No high-risk absconding alerts currently.</strong> Continue monitoring ARM and environmental stress.</div>
      )}

      <div className="dashboard-grid">
        <div className="card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header"><div className="chart-title"><h3>Per-Hive Decision Table</h3><p>Latest probability, ARM, explanation, and action for each hive.</p></div></div>
          <div className="table-container">
            <table className="custom-table">
              <thead><tr><th>Hive</th><th>Risk %</th><th>Level</th><th>ARM</th><th>Trend</th><th>Temp</th><th>CO₂</th><th>Weight</th><th>Main Explanation</th><th>Recommended Action</th></tr></thead>
              <tbody>
                {perHive.map(h => (
                  <tr key={h.hive} onClick={() => { setSelectedHive(h.hive); setActiveView('eda'); }} style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 700 }}>{h.hive}</td>
                    <td>{numberValue(h.risk_percentage, 2, '%')}</td>
                    <td style={{ color: levelColor(h.risk_level), fontWeight: 700 }}>{h.risk_level}</td>
                    <td>{numberValue(h.arm, 4)}</td>
                    <td>{h.arm_trend}</td>
                    <td>{numberValue(h.latest_sensor_readings?.temperature_c, 1, '°C')}</td>
                    <td>{numberValue(h.latest_sensor_readings?.co2_ppm, 0, ' ppm')}</td>
                    <td>{numberValue(h.latest_sensor_readings?.weight_kg, 1, ' kg')}</td>
                    <td>{h.key_factors?.[0]?.factor ?? '—'}</td>
                    <td>{h.alert_required ? 'Immediate hive inspection' : 'Continue monitoring'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <SectionTabs activeView={activeView} setActiveView={setActiveView} />
      {activeView === 'eda' && EDAView}
      {activeView === 'training' && TrainingView}
      {activeView === 'live' && LiveView}
    </div>
  );
}
