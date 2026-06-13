
import React from 'react';
import {
  AlertTriangle, Wind, TrendingUp, ShieldCheck, Activity, Info, RefreshCw
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend
} from 'recharts';

import { useAbscondingData } from '../hooks/useAbscondingData';

const imgUrl = (filename) => `/api/absconding/images/${filename}`;

function levelColor(level) {
  if (level === 'High') return 'var(--accent-crimson)';
  if (level === 'Medium') return 'var(--accent-gold)';
  return 'var(--accent-emerald)';
}

function percent(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(1)}%`;
}

export default function AbscondingModule({ edaData }) {
  const { abscondingData, abscondingLoading, abscondingError, refetchAbsconding } = useAbscondingData();

  const fallbackInsight = edaData?.module_insights?.absconding || 'Run the absconding module to generate ML-based risk scores.';
  const data = abscondingData || {};
  const summary = data.summary || {};
  const metrics = data.model_metrics || {};
  const perHive = data.per_hive_absconding_risk || [];
  const alerts = data.alerts || [];
  const features = data.feature_importance || [];

  const riskBarData = perHive.slice(0, 12).map(h => ({
    hive: h.hive,
    risk: Number(h.risk_percentage || 0),
    arm: Number((h.arm || 0) * 100),
    level: h.risk_level,
  }));

  const featureData = features.slice(0, 10).map(f => ({
    feature: f.feature?.replaceAll('_', ' '),
    importance: Number(f.importance || 0),
  }));

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
        <div className="card highlight-crimson">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Absconding Prediction Module Not Generated Yet</h3>
              <p>{abscondingError}</p>
            </div>
            <AlertTriangle size={24} color="var(--accent-crimson)" />
          </div>
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            Run <code>python backend/scripts/run_absconding.py</code>, then restart your backend.
          </p>
          <p style={{ color: 'var(--text-muted)' }}>{fallbackInsight}</p>
          <button className="upload-btn" onClick={refetchAbsconding}>
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

      <div className="dashboard-grid">
        <div className="card welcome-card" style={{ gridColumn: 'span 3' }}>
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>Module 03 — Absconding Behaviour Prediction</h2>
              <p>
                Predicts colony abandonment risk using multivariate time-series patterns,
                ARM trend analysis, and explainable environmental stress factors.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card highlight-crimson">
          <div className="stat-header">
            <span>High Risk Hives</span>
            <AlertTriangle size={16} color="var(--accent-crimson)" />
          </div>
          <div className="stat-value">{summary.high_risk_hives ?? 0}</div>
          <div className="stat-footer">Requires immediate inspection</div>
        </div>

        <div className="card highlight-gold">
          <div className="stat-header">
            <span>Medium Risk Hives</span>
            <TrendingUp size={16} color="var(--accent-gold)" />
          </div>
          <div className="stat-value">{summary.medium_risk_hives ?? 0}</div>
          <div className="stat-footer">Monitor closely</div>
        </div>

        <div className="card highlight-cyan">
          <div className="stat-header">
            <span>Model Recall</span>
            <ShieldCheck size={16} color="var(--accent-cyan)" />
          </div>
          <div className="stat-value">{percent((metrics.recall || 0) * 100)}</div>
          <div className="stat-footer">Absconding event capture rate</div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Evaluation Metrics</h3>
              <p>Time-based test split, next-72h absconding label</p>
            </div>
            <Activity size={18} color="var(--accent-gold)" />
          </div>
          <div className="table-container">
            <table className="custom-table">
              <tbody>
                <tr><td>Accuracy</td><td>{percent((metrics.accuracy || 0) * 100)}</td></tr>
                <tr><td>Precision</td><td>{percent((metrics.precision || 0) * 100)}</td></tr>
                <tr><td>Recall</td><td>{percent((metrics.recall || 0) * 100)}</td></tr>
                <tr><td>F1 Score</td><td>{percent((metrics.f1_score || 0) * 100)}</td></tr>
                <tr><td>ROC-AUC</td><td>{metrics.roc_auc ?? '—'}</td></tr>
                <tr><td>PR-AUC</td><td>{metrics.pr_auc ?? '—'}</td></tr>
                <tr><td>MAE</td><td>{metrics.mae ?? '—'}</td></tr>
                <tr><td>RMSE</td><td>{metrics.rmse ?? '—'}</td></tr>
                <tr><td>Decision Threshold</td><td>{metrics.threshold ?? '—'}</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Latest Absconding Risk by Hive</h3>
              <p>Risk probability with ARM-based escalation</p>
            </div>
            <Wind size={20} color="var(--accent-cyan)" />
          </div>
          <div className="chart-container" style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskBarData} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="hive" stroke="var(--text-secondary)" angle={-25} textAnchor="end" height={60} />
                <YAxis stroke="var(--text-secondary)" unit="%" />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }}
                  formatter={(v, n) => [`${Number(v).toFixed(2)}%`, n === 'risk' ? 'Risk' : 'ARM ×100']}
                />
                <Legend />
                <Bar dataKey="risk" name="Risk %" fill="var(--accent-crimson)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="arm" name="ARM ×100" fill="var(--accent-gold)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="dashboard-grid">
          <div className="card highlight-crimson" style={{ gridColumn: 'span 3' }}>
            <div className="chart-header">
              <div className="chart-title">
                <h3>Early Warning Alerts</h3>
                <p>Generated when risk or ARM trend crosses thresholds</p>
              </div>
              <AlertTriangle size={22} color="var(--accent-crimson)" />
            </div>
            {alerts.map(alert => (
              <div key={alert.hive} style={{
                padding: '0.9rem',
                marginTop: '0.75rem',
                border: '1px solid rgba(248,113,113,0.35)',
                borderRadius: '10px',
                background: 'rgba(248,113,113,0.08)',
              }}>
                <strong>{alert.hive}</strong> — {alert.message}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Explainable Risk Factors</h3>
              <p>Top model features used to classify absconding risk</p>
            </div>
            <Info size={18} color="var(--text-secondary)" />
          </div>
          <div className="chart-container" style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={featureData} margin={{ top: 10, right: 20, left: 0, bottom: 70 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="feature" stroke="var(--text-secondary)" angle={-35} textAnchor="end" interval={0} height={80} />
                <YAxis stroke="var(--text-secondary)" />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Line type="monotone" dataKey="importance" name="Importance" stroke="var(--accent-gold)" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Confusion Matrix</h3>
              <p>Model classification performance</p>
            </div>
          </div>
          <img
            src={imgUrl('absconding_confusion_matrix.png')}
            alt="Absconding confusion matrix"
            style={{ width: '100%', borderRadius: '8px', marginTop: '0.75rem' }}
          />
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card chart-card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Risk Timeline with ARM</h3>
              <p>Risk trajectory for the highest-risk hive in the test period</p>
            </div>
          </div>
          <img
            src={imgUrl('absconding_risk_timeline.png')}
            alt="Absconding risk timeline"
            style={{ width: '100%', borderRadius: '8px', marginTop: '0.75rem' }}
          />
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="card" style={{ gridColumn: 'span 3' }}>
          <div className="chart-header">
            <div className="chart-title">
              <h3>Per-Hive Decision Table</h3>
              <p>Latest probability, ARM trend, explanation, and alert decision</p>
            </div>
          </div>
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Hive</th>
                  <th>Risk %</th>
                  <th>Level</th>
                  <th>ARM</th>
                  <th>Trend</th>
                  <th>Main Explanation</th>
                  <th>Recommended Action</th>
                </tr>
              </thead>
              <tbody>
                {perHive.map(h => (
                  <tr key={h.hive}>
                    <td style={{ fontWeight: 700 }}>{h.hive}</td>
                    <td>{Number(h.risk_percentage).toFixed(2)}%</td>
                    <td style={{ color: levelColor(h.risk_level), fontWeight: 700 }}>{h.risk_level}</td>
                    <td>{Number(h.arm).toFixed(4)}</td>
                    <td>{h.arm_trend}</td>
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
}
