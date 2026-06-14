import React, { useState, useEffect } from 'react';
import { CheckCircle, BarChart3, Loader, TrendingUp, XCircle } from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

export default function BroodHealthTraining() {
  const [status, setStatus] = useState('idle'); 
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [currentStep, setCurrentStep] = useState('');
  const [polling, setPolling] = useState(null);

  const checkStatus = async () => {
    try {
      const res = await axios.get(`${API_BASE}/brood_health/train/status`);
      const data = res.data;
      setProgress(data.progress || 0);
      setMessage(data.message || '');
      setCurrentStep(data.current_step || '');

      if (!data.running && data.result) {
        setStatus('completed');
        setResult(data.result);
        setProgress(100);
        if (polling) clearInterval(polling);
        setPolling(null);
      } else if (!data.running && data.error) {
        setStatus('error');
        setError(data.error);
        if (polling) clearInterval(polling);
        setPolling(null);
      } else if (data.running) {
        setStatus('running');
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Start the training (call backend)
  const startTraining = async () => {
    setStatus('running');
    setResult(null);
    setError(null);
    setProgress(0);
    setMessage('Starting training...');
    try {
      await axios.post(`${API_BASE}/brood_health/train`);
      const interval = setInterval(() => checkStatus(), 1500);
      setPolling(interval);
    } catch (err) {
      setStatus('error');
      setError(err.response?.data?.message || err.message);
    }
  };

  // On mount: check if a cached result already exists (from training_summary.json)
  useEffect(() => {
    const fetchCached = async () => {
      try {
        const res = await axios.get(`${API_BASE}/brood_health/train/status`);
        if (res.data.result) {
          setStatus('completed');
          setResult(res.data.result);
          setProgress(100);
        } else if (res.data.running) {
          setStatus('running');
          setProgress(res.data.progress || 0);
          setMessage(res.data.message || '');
          setCurrentStep(res.data.current_step || '');
          const interval = setInterval(() => checkStatus(), 1500);
          setPolling(interval);
        } else {
          setStatus('idle');
        }
      } catch (err) {
        setError(err.message);
        setStatus('error');
      }
    };
    fetchCached();

    // Cleanup polling on unmount
    return () => {
      if (polling) clearInterval(polling);
    };
  }, []);

  // ──────────────────────────────────────────────────────────────
  // Render idle state (show Start Training button)
  if (status === 'idle') {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
        <BarChart3 size={48} color="var(--accent-cyan)" style={{ marginBottom: '1rem' }} />
        <h3>Model Training</h3>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto 1.5rem' }}>
          Train three regression models (Random Forest, XGBoost, Gradient Boosting) on the existing dataset.<br />
          The best model (lowest RMSE) will be saved for future predictions.
        </p>
        <button onClick={startTraining} className="upload-btn" style={{ background: 'var(--accent-emerald)', padding: '0.75rem 2rem' }}>
          <TrendingUp size={18} style={{ marginRight: '0.5rem' }} />
          Start Training
        </button>
      </div>
    );
  }

  // ──────────────────────────────────────────────────────────────
  // Render running state with progress bar
  if (status === 'running') {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
        <Loader size={40} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem', color: 'var(--accent-cyan)' }} />
        <h3>Training in progress...</h3>
        <div style={{ width: '80%', margin: '1rem auto', background: '#2d3748', borderRadius: '10px', height: '10px', overflow: 'hidden' }}>
          <div style={{ width: `${progress}%`, background: 'var(--accent-emerald)', height: '100%', transition: 'width 0.3s' }} />
        </div>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>{message}</p>
        {currentStep && <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Current model: {currentStep}</p>}
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
        <XCircle size={48} color="var(--accent-crimson)" style={{ marginBottom: '1rem' }} />
        <h3>Training Failed</h3>
        <p style={{ color: 'var(--text-secondary)' }}>{error}</p>
        <button onClick={() => setStatus('idle')} className="upload-btn" style={{ marginTop: '1rem' }}>Try Again</button>
      </div>
    );
  }

  if (status === 'completed' && result) {
    const models = Object.entries(result.all_models);
    const bestModel = result.best_model;
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Success banner */}
        <div className="card" style={{ background: 'rgba(16, 185, 129, 0.1)', borderLeft: '4px solid var(--accent-emerald)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <CheckCircle size={32} color="var(--accent-emerald)" />
            <div>
              <h3 style={{ margin: 0 }}>Model Training Complete</h3>
              <p style={{ margin: 0, fontSize: '0.85rem' }}>Best model: <strong>{bestModel}</strong> (RMSE = {result.metrics.rmse})</p>
            </div>
          </div>
        </div>

        {/* Comparison table */}
        <div className="card">
          <div className="chart-header">
            <h3>📊 Model Performance Comparison</h3>
            <p>Lower RMSE and higher R² indicate better predictive accuracy.</p>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center' }}>
              <thead>
                <tr>
                  <th style={{ padding: '0.75rem' }}>Model</th>
                  <th style={{ padding: '0.75rem' }}>RMSE ↓</th>
                  <th style={{ padding: '0.75rem' }}>MAE</th>
                  <th style={{ padding: '0.75rem' }}>R²</th>
                  <th style={{ padding: '0.75rem' }}>CV R² (3-fold)</th>
                </tr>
              </thead>
              <tbody>
                {models.map(([name, metrics]) => (
                  <tr key={name} style={{ background: name === bestModel ? 'rgba(16, 185, 129, 0.15)' : 'transparent' }}>
                    <td style={{ padding: '0.75rem', fontWeight: name === bestModel ? 'bold' : 'normal' }}>
                      {name} {name === bestModel && <CheckCircle size={14} style={{ display: 'inline', marginLeft: '0.5rem', color: 'var(--accent-emerald)' }} />}
                    </td>
                    <td style={{ color: name === bestModel ? 'var(--accent-emerald)' : 'inherit' }}>{metrics.rmse}</td>
                    <td>{metrics.mae}</td>
                    <td>{metrics.r2}</td>
                    <td>{metrics.cv_r2_mean}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="stat-footer" style={{ marginTop: '1rem' }}>
            Training samples: {result.train_samples} | Test samples: {result.test_samples}
          </div>
        </div>
      </div>
    );
  }

  return null;
}