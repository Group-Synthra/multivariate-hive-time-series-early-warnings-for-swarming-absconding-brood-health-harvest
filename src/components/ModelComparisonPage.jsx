import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line
} from 'recharts';
import { 
  Download, Trophy, TrendingUp, AlertTriangle, 
  RefreshCw, BarChart2, Activity, Cpu,
  Maximize2, Minimize2, X, Shield, Bell, Eye
} from 'lucide-react';

export default function ModelComparisonPage({ onClose }) {
  const [comparisonData, setComparisonData] = useState(null);
  const [bestModel, setBestModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedView, setExpandedView] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState('f1_score');
  const [showRiskDetails, setShowRiskDetails] = useState(true);

  // Risk threshold data from analysis
  const riskDistribution = {
    low: { percentage: 91.61, count: 33571, threshold: "< 40%", action: "Normal operations - routine monitoring" },
    medium: { percentage: 0.73, count: 269, threshold: "40% - 70%", action: "Prepare equipment - schedule inspection within 24 hours" },
    high: { percentage: 7.66, count: 2807, threshold: "> 70%", action: "Immediate intervention required - swarm imminent" },
    total: 36647
  };

  // Probability statistics from analysis
  const probabilityStats = {
    min: 0.00,
    max: 99.97,
    avg: 9.09,
    stdDev: 25.93
  };

  // Fetch model comparison data
  const fetchModelComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:5000/api/swarming/model-comparison');
      if (!response.ok) throw new Error('Failed to fetch model comparison data');
      const data = await response.json();
      
      const filteredModels = data.models.filter(model => 
        model.model === 'Random Forest' || model.model === 'XGBoost'
      );
      
      setComparisonData(filteredModels);
      setBestModel({
        best_model: data.best_model,
        best_model_f1_score: data.best_model_f1_score
      });
    } catch (error) {
      console.error('Failed to fetch model comparison:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModelComparison();
  }, []);

  const handleExport = () => {
    if (!comparisonData) return;
    const exportData = {
      models: comparisonData,
      best_model: bestModel,
      risk_distribution: riskDistribution,
      probability_statistics: probabilityStats,
      export_date: new Date().toISOString()
    };
    const dataStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `model_comparison_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const chartData = comparisonData?.map(model => ({
    model: model.model,
    accuracy: model.accuracy * 100,
    precision: model.precision * 100,
    recall: model.recall * 100,
    f1_score: model.f1_score * 100,
    roc_auc: model.roc_auc * 100
  })) || [];

  const pieData = comparisonData?.map(model => ({
    name: model.model,
    value: model.f1_score * 100,
    isBest: model.model === bestModel?.best_model
  })) || [];

  const riskChartData = [
    { name: 'Low Risk', value: riskDistribution.low.percentage, color: '#22c55e', count: riskDistribution.low.count },
    { name: 'Medium Risk', value: riskDistribution.medium.percentage, color: '#f59e0b', count: riskDistribution.medium.count },
    { name: 'High Risk', value: riskDistribution.high.percentage, color: '#ef4444', count: riskDistribution.high.count }
  ];

  const COLORS = ['#3b82f6', '#10b981'];

  const metrics = [
    { key: 'f1_score', label: 'F1-Score', color: '#10b981', description: 'Balance of precision & recall' },
    { key: 'accuracy', label: 'Accuracy', color: '#3b82f6', description: 'Overall correctness' },
    { key: 'precision', label: 'Precision', color: '#f59e0b', description: 'Low false alarms' },
    { key: 'recall', label: 'Recall', color: '#ef4444', description: 'Catches actual swarms' },
    { key: 'roc_auc', label: 'ROC-AUC', color: '#8b5cf6', description: 'Discrimination ability' }
  ];

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f8fafc' }}>
        <div style={{ textAlign: 'center' }}>
          <RefreshCw size={48} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem', color: '#3b82f6' }} />
          <p style={{ color: '#64748b' }}>Loading model comparison data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f8fafc' }}>
        <div style={{ textAlign: 'center', maxWidth: '500px', background: 'white', borderRadius: '12px', padding: '2rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <AlertTriangle size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
          <h3 style={{ color: '#1e293b' }}>Error Loading Model Comparison</h3>
          <p style={{ color: '#64748b', marginTop: '0.5rem' }}>{error}</p>
          <button onClick={fetchModelComparison} style={{ marginTop: '1rem', padding: '8px 16px', background: '#ef4444', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer' }}>Retry</button>
          <button onClick={onClose} style={{ marginTop: '1rem', marginLeft: '0.5rem', padding: '8px 16px', background: 'transparent', border: '1px solid #e2e8f0', borderRadius: '6px', color: '#64748b', cursor: 'pointer' }}>Close</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: expandedView ? '1rem' : '2rem', maxWidth: expandedView ? '100%' : '1400px', margin: '0 auto', width: '100%', background: '#f8fafc', minHeight: '100vh' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h1 style={{ margin: 0, fontSize: '1.75rem', color: '#1e293b' }}>
            <BarChart2 size={28} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle', color: '#3b82f6' }} />
            Model Comparison: RF vs XGBoost
          </h1>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button onClick={() => setExpandedView(!expandedView)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '8px 16px', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', color: '#475569', cursor: 'pointer' }}>
            {expandedView ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            {expandedView ? 'Compact' : 'Fullscreen'}
          </button>
          <button onClick={handleExport} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '8px 16px', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', color: '#475569', cursor: 'pointer' }}>
            <Download size={16} /> Export
          </button>
          <button onClick={fetchModelComparison} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '8px 16px', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', color: '#475569', cursor: 'pointer' }}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button onClick={onClose} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '8px 16px', background: '#fee2e2', border: '1px solid #fecaca', borderRadius: '8px', color: '#dc2626', cursor: 'pointer' }}>
            <X size={16} /> Close
          </button>
        </div>
      </div>

      {/* ==================== SECTION 1: MODEL COMPARISON RESULTS ==================== */}
      
      {/* Best Model Banner */}
      {bestModel && comparisonData && (
        <div style={{ background: 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)', border: '1px solid #fde047', borderRadius: '16px', padding: '1.5rem', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
            <div style={{ background: '#fef08a', borderRadius: '50%', padding: '1rem' }}><Trophy size={48} color="#ca8a04" /></div>
            <div>
              <div style={{ fontSize: '0.85rem', color: '#854d0e' }}>🏆 Best Performing Model</div>
              {/* <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ca8a04' }}>{bestModel.best_model?.toUpperCase()}</div>
              <div style={{ fontSize: '0.9rem', color: '#854d0e' }}>F1-Score: {(bestModel.best_model_f1_score * 100).toFixed(2)}% • Selected for production deployment</div> */}
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}><div style={{ fontSize: '0.7rem', color: '#854d0e' }}>Last updated: {new Date().toLocaleString()}</div></div>
          </div>
        </div>
      )}

      {/* Metrics Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {comparisonData?.map((model, idx) => (
          <div key={idx} style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', borderTop: `4px solid ${model.model === bestModel?.best_model ? '#eab308' : '#e2e8f0'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <span style={{ fontWeight: 700, fontSize: '1.25rem', color: '#1e293b' }}>{model.model}</span>
              {model.model === bestModel?.best_model && <span style={{ fontSize: '0.7rem', padding: '2px 8px', background: '#fef08a', borderRadius: '20px', color: '#854d0e' }}>🏆 BEST</span>}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div><div style={{ fontSize: '0.7rem', color: '#64748b' }}>F1-Score</div><div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#10b981' }}>{(model.f1_score * 100).toFixed(1)}%</div></div>
              {/* <div><div style={{ fontSize: '0.7rem', color: '#64748b' }}>Accuracy</div><div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#3b82f6' }}>{(model.accuracy * 100).toFixed(1)}%</div></div> */}
              <div><div style={{ fontSize: '0.7rem', color: '#64748b' }}>Precision</div><div style={{ fontSize: '1rem', fontWeight: 600, color: '#f59e0b' }}>{(model.precision * 100).toFixed(1)}%</div></div>
              <div><div style={{ fontSize: '0.7rem', color: '#64748b' }}>Recall</div><div style={{ fontSize: '1rem', fontWeight: 600, color: '#ef4444' }}>{(model.recall * 100).toFixed(1)}%</div></div>
              <div><div style={{ fontSize: '0.7rem', color: '#64748b' }}>ROC-AUC</div><div style={{ fontSize: '1rem', fontWeight: 500, color: '#8b5cf6' }}>{(model.roc_auc * 100).toFixed(1)}%</div></div>
              <div><div style={{ fontSize: '0.7rem', color: '#64748b' }}>Training Time</div><div style={{ fontSize: '1rem', fontWeight: 500, color: '#475569' }}>{(model.training_time_seconds / 60).toFixed(1)} min</div></div>
            </div>
          </div>
        ))}
      </div>

      {/* Metric Selector */}
      <div style={{ background: 'white', borderRadius: '12px', padding: '1rem 1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, color: '#1e293b' }}>Select Metric to Compare:</span>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {metrics.map(metric => (<button key={metric.key} onClick={() => setSelectedMetric(metric.key)} style={{ padding: '6px 16px', background: selectedMetric === metric.key ? metric.color : '#f1f5f9', border: 'none', borderRadius: '20px', color: selectedMetric === metric.key ? 'white' : '#475569', cursor: 'pointer', fontSize: '0.85rem' }}>{metric.label}</button>))}
          </div>
        </div>
      </div>

      {/* Performance Comparison Chart */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h3 style={{ margin: 0, color: '#1e293b' }}>Performance Comparison Chart</h3>
          <p style={{ margin: '0.25rem 0 1rem', fontSize: '0.85rem', color: '#64748b' }}>Comparing {metrics.find(m => m.key === selectedMetric)?.label}</p>
          <div style={{ height: '400px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="model" stroke="#64748b" />
                <YAxis stroke="#64748b" tickFormatter={(value) => `${value}%`} />
                <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px' }} formatter={(value) => [`${value.toFixed(2)}%`, '']} />
                <Legend />
                <Bar dataKey={selectedMetric} name={metrics.find(m => m.key === selectedMetric)?.label} fill={metrics.find(m => m.key === selectedMetric)?.color} radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h3 style={{ margin: 0, color: '#1e293b' }}>F1-Score Distribution</h3>
          <p style={{ margin: '0.25rem 0 1rem', fontSize: '0.85rem', color: '#64748b' }}>Model performance comparison</p>
          <div style={{ height: '350px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart><Pie data={pieData} cx="50%" cy="50%" labelLine={true} label={(entry) => `${entry.name}: ${entry.value.toFixed(1)}%`} outerRadius={100} dataKey="value">{pieData.map((entry, index) => (<Cell key={`cell-${index}`} fill={entry.isBest ? '#eab308' : COLORS[index % COLORS.length]} stroke="white" strokeWidth={2} />))}</Pie><Tooltip formatter={(value) => [`${value.toFixed(2)}%`, 'F1-Score']} /><Legend /></PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Detailed Metrics Table */}
      <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', marginBottom: '2rem' }}>
        <h3 style={{ margin: 0, color: '#1e293b' }}>Detailed Model Metrics</h3>
        <p style={{ margin: '0.25rem 0 1rem', fontSize: '0.85rem', color: '#64748b' }}>Complete performance breakdown: Random Forest vs XGBoost</p>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr style={{ borderBottom: '2px solid #e2e8f0' }}>
              <th style={{ textAlign: 'left', padding: '12px', color: '#475569' }}>Model</th>
              {/* <th style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>Accuracy</th> */}
              <th style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>Precision</th>
              <th style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>Recall</th>
              <th style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>F1-Score</th>
              <th style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>ROC-AUC</th>
              <th style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>Training Time</th>
            </tr></thead>
            <tbody>
              {comparisonData?.map((model, idx) => (<tr key={idx} style={{ background: model.model === bestModel?.best_model ? '#fefce8' : 'white', borderBottom: '1px solid #f1f5f9' }}>
                <td style={{ fontWeight: 700, padding: '12px', color: '#1e293b' }}>{model.model}{model.model === bestModel?.best_model && <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', padding: '2px 8px', background: '#fef08a', borderRadius: '20px', color: '#854d0e' }}>🏆 BEST</span>}</td>
                {/* <td style={{ textAlign: 'center', padding: '12px', fontWeight: 600, color: '#3b82f6' }}>{(model.accuracy * 100).toFixed(2)}%</td> */}
                <td style={{ textAlign: 'center', padding: '12px', fontWeight: 600, color: '#f59e0b' }}>{(model.precision * 100).toFixed(2)}%</td>
                <td style={{ textAlign: 'center', padding: '12px', fontWeight: 600, color: '#ef4444' }}>{(model.recall * 100).toFixed(2)}%</td>
                <td style={{ textAlign: 'center', fontWeight: 800, padding: '12px', color: model.f1_score === Math.max(...comparisonData.map(m => m.f1_score)) ? '#ca8a04' : '#475569' }}>{(model.f1_score * 100).toFixed(2)}%</td>
                <td style={{ textAlign: 'center', padding: '12px', fontWeight: 600, color: '#8b5cf6' }}>{(model.roc_auc * 100).toFixed(2)}%</td>
                <td style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>{(model.training_time_seconds / 60).toFixed(1)} min</td>
              </tr>))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ==================== SECTION 2: RISK ASSESSMENT RESULTS ==================== */}
      
      <div style={{ marginTop: '2rem', marginBottom: '1rem' }}>
        <h2 style={{ color: '#1e293b', borderBottom: '2px solid #e2e8f0', paddingBottom: '0.5rem' }}>
          <Shield size={24} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle' }} />
          Swarming Risk Assessment Results
        </h2>
        <p style={{ color: '#64748b', marginTop: '0.25rem' }}>Based on Random Forest model predictions across 36,647 test sequences</p>
      </div>

      {/* Risk Level Banner */}
      <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)', borderRadius: '16px', padding: '1.5rem', marginBottom: '2rem', border: '1px solid #334155' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(34,197,94,0.1)', borderRadius: '12px', borderLeft: '3px solid #22c55e' }}>
            <div style={{ color: '#22c55e', fontSize: '0.7rem', fontWeight: 600 }}>LOW RISK</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#22c55e' }}>{riskDistribution.low.percentage}%</div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Threshold: {riskDistribution.low.threshold}</div>
            <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '0.25rem' }}>{riskDistribution.low.action}</div>
          </div>
          <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(245,158,11,0.1)', borderRadius: '12px', borderLeft: '3px solid #f59e0b' }}>
            <div style={{ color: '#f59e0b', fontSize: '0.7rem', fontWeight: 600 }}>MEDIUM RISK</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f59e0b' }}>{riskDistribution.medium.percentage}%</div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Threshold: {riskDistribution.medium.threshold}</div>
            <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '0.25rem' }}>{riskDistribution.medium.action}</div>
          </div>
          <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(239,68,68,0.1)', borderRadius: '12px', borderLeft: '3px solid #ef4444' }}>
            <div style={{ color: '#ef4444', fontSize: '0.7rem', fontWeight: 600 }}>HIGH RISK</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ef4444' }}>{riskDistribution.high.percentage}%</div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Threshold: {riskDistribution.high.threshold}</div>
            <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '0.25rem' }}>{riskDistribution.high.action}</div>
          </div>
        </div>
      </div>

      {/* Probability Statistics Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ background: 'white', borderRadius: '12px', padding: '1rem', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Minimum Risk</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#22c55e' }}>{probabilityStats.min}%</div>
        </div>
        <div style={{ background: 'white', borderRadius: '12px', padding: '1rem', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Maximum Risk</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ef4444' }}>{probabilityStats.max}%</div>
        </div>
        <div style={{ background: 'white', borderRadius: '12px', padding: '1rem', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Average Risk</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#3b82f6' }}>{probabilityStats.avg}%</div>
        </div>
        <div style={{ background: 'white', borderRadius: '12px', padding: '1rem', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Standard Deviation</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#8b5cf6' }}>{probabilityStats.stdDev}%</div>
        </div>
      </div>

      {/* Risk Distribution Chart */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h3 style={{ margin: 0, color: '#1e293b' }}>Risk Level Distribution</h3>
          <p style={{ margin: '0.25rem 0 1rem', fontSize: '0.85rem', color: '#64748b' }}>Based on {riskDistribution.total.toLocaleString()} test samples</p>
          <div style={{ height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskChartData} cx="50%" cy="50%" labelLine={true} label={(entry) => `${entry.name}: ${entry.value.toFixed(1)}%`} outerRadius={100} dataKey="value">
                  {riskChartData.map((entry, index) => (<Cell key={`cell-${index}`} fill={entry.color} stroke="white" strokeWidth={2} />))}
                </Pie>
                <Tooltip formatter={(value) => [`${value.toFixed(2)}%`, 'Percentage']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk Interpretation */}
        <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <h3 style={{ margin: 0, color: '#1e293b' }}>Risk Interpretation Guide</h3>
          <p style={{ margin: '0.25rem 0 1rem', fontSize: '0.85rem', color: '#64748b' }}>What each risk level means for beekeepers</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ padding: '1rem', background: '#f0fdf4', borderRadius: '8px', borderLeft: '4px solid #22c55e' }}>
              <strong style={{ color: '#166534' }}>🟢 LOW RISK (Below 40%) - {riskDistribution.low.percentage}% of samples</strong>
              <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: '#166534' }}>✓ Normal hive operations • Continue routine monitoring • No immediate action needed</p>
            </div>
            <div style={{ padding: '1rem', background: '#fefce8', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
              <strong style={{ color: '#854d0e' }}>🟡 MEDIUM RISK (40-70%) - {riskDistribution.medium.percentage}% of samples</strong>
              <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: '#854d0e' }}>⚠️ Early warning sign • Prepare swarm capture equipment • Schedule hive inspection within 24 hours</p>
            </div>
            <div style={{ padding: '1rem', background: '#fef2f2', borderRadius: '8px', borderLeft: '4px solid #ef4444' }}>
              <strong style={{ color: '#991b1b' }}>🔴 HIGH RISK (Above 70%) - {riskDistribution.high.percentage}% of samples</strong>
              <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.8rem', color: '#991b1b' }}>🚨 Swarm imminent! • Immediate intervention required • Deploy swarm capture equipment</p>
            </div>
          </div>
        </div>
      </div>

      {/* Info Note */}
      <div style={{ background: '#f0fdf4', borderRadius: '12px', padding: '1.25rem', border: '1px solid #bbf7d0' }}>
        {/* <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
          <AlertTriangle size={20} color="#eab308" />
          <div>
            <h4 style={{ marginBottom: '0.5rem', color: '#166534' }}>About Model Selection & Risk Thresholds</h4>
            <p style={{ fontSize: '0.85rem', color: '#166534' }}><strong>F1-Score</strong> is the primary selection metric because swarming events are rare. Random Forest achieved <strong>96.35% F1-Score</strong> with <strong>93.54% precision</strong> (few false alarms) and <strong>99.35% recall</strong> (catches almost all swarms).</p>
            <p style={{ fontSize: '0.8rem', color: '#166534', marginTop: '0.5rem' }}>Risk thresholds were determined by analyzing the model's probability distribution across 36,647 test sequences, resulting in natural separation at 40% and 70%.</p>
          </div>
        </div> */}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}