import React, { useState, useMemo, useEffect } from 'react';
import { Zap, ShieldAlert, AlertTriangle, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, Info, ChevronLeft, ChevronRight, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Scatter } from 'recharts';

const SWARM_COLORS = { Critical: '#ef4444', Warning: '#f59e0b', Normal: '#10b981' };
const RISK_LEVELS = [
  { range: "High Risk", color: SWARM_COLORS.Critical, description: "Immediate action required - swarm in progress" },
  { range: "Moderate Risk", color: SWARM_COLORS.Warning, description: "Monitor closely - swarm indicators present" },
  { range: "Low Risk", color: SWARM_COLORS.Normal, description: "Stable - no swarm indicators detected" }
];

const getStatus = (riskLevel) => {
  switch(riskLevel) {
    case 'High Risk': return { label: 'R', color: '#ef4444' };
    case 'Moderate Risk': return { label: 'P', color: '#f59e0b' };
    default: return { label: 'I', color: '#10b981' };
  }
};

const useSwarmingData = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setTimeout(() => {
      const hives = Array.from({ length: 58 }, (_, i) => `hive${String(i + 1).padStart(2, '0')}`);
      const metrics = [];
      const swarmEvents = [];
      hives.forEach(hive => {
        const baseWeight = 30 + Math.random() * 10;
        const baseCO2 = 400 + Math.random() * 200;
        for (let i = 0; i < 100; i++) {
          const timestamp = new Date();
          timestamp.setHours(timestamp.getHours() - i * 0.5);
          const isSwarm = Math.random() < 0.02;
          const weightDrop = isSwarm ? 2 + Math.random() * 3 : 0;
          const co2Spike = isSwarm ? 1500 + Math.random() * 500 : 0;
          metrics.push({ hive, timestamp: timestamp.toISOString(), weight: baseWeight + Math.sin(i / 10) * 2 - weightDrop, co2: baseCO2 + Math.sin(i / 15) * 100 + co2Spike, temperature: 34 + Math.sin(i / 20) * 2, humidity: 55 + Math.sin(i / 25) * 10 });
          if (isSwarm) swarmEvents.push({ hive, timestamp: timestamp.toISOString(), weightChange: -weightDrop.toFixed(2), co2: Math.round(baseCO2 + co2Spike) });
        }
      });
      setData({ metrics, swarmEvents, hives });
      setLoading(false);
    }, 500);
  }, []);
  return { data, loading };
};

const getWindowData = (data, windowNumber, windowSize) => {
  const start = windowNumber * windowSize;
  return data.slice(start, Math.min(start + windowSize, data.length));
};

const getWindowDescription = (data, windowNumber, windowSize) => {
  const total = data.length;
  const start = windowNumber * windowSize;
  const end = Math.min(start + windowSize, total);
  return `Records ${start + 1}-${end} of ${total}`;
};

const getTotalWindows = (totalRecords, windowSize) => Math.ceil(totalRecords / windowSize);

const detectSwarmPattern = (data) => {
  if (data.length < 10) return null;
  const last10 = data.slice(-10);
  const avgWeightDrop = last10.reduce((a, d) => a + (d.weightDrop || 0), 0) / 10;
  const avgCO2Spike = last10.reduce((a, d) => a + (d.co2Spike || 0), 0) / 10;
  if (avgWeightDrop > 0.5 && avgCO2Spike > 1500) return { risk: 'High Risk', confidence: 0.9 };
  if (avgWeightDrop > 0.2 && avgCO2Spike > 1000) return { risk: 'Moderate Risk', confidence: 0.6 };
  return { risk: 'Low Risk', confidence: 0.2 };
};

export default function SwarmingModule() {
  const { data, loading } = useSwarmingData();
  const [selectedHive, setSelectedHive] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [windowSize, setWindowSize] = useState(50);
  const [windowNumber, setWindowNumber] = useState(0);

  const metrics = data?.metrics || [];
  const swarmEvents = data?.swarmEvents || [];
  const hives = data?.hives || [];

  useEffect(() => { if (hives.length > 0 && !selectedHive) setSelectedHive(hives[0]); }, [hives, selectedHive]);

  const fullHiveMetrics = useMemo(() => metrics.filter(m => m.hive === selectedHive).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)), [metrics, selectedHive]);
  const totalWindows = getTotalWindows(fullHiveMetrics.length, windowSize);
  const windowData = useMemo(() => getWindowData(fullHiveMetrics, windowNumber, windowSize), [fullHiveMetrics, windowNumber, windowSize]);
  const windowDesc = getWindowDescription(fullHiveMetrics, windowNumber, windowSize);

  const windowSwarmEvents = useMemo(() => {
    if (windowData.length === 0) return [];
    const startTime = new Date(windowData[0].timestamp);
    const endTime = new Date(windowData[windowData.length - 1].timestamp);
    return swarmEvents.filter(e => new Date(e.timestamp) >= startTime && new Date(e.timestamp) <= endTime && e.hive === selectedHive);
  }, [swarmEvents, windowData, selectedHive]);

  const riskAssessment = detectSwarmPattern(fullHiveMetrics);
  const riskLevel = riskAssessment?.risk || 'Low Risk';
  const confidence = riskAssessment?.confidence || 0;
  const latest = fullHiveMetrics.length > 0 ? fullHiveMetrics[fullHiveMetrics.length - 1] : null;
  const first = fullHiveMetrics.length > 0 ? fullHiveMetrics[0] : null;
  const weightDrop = latest && first ? (first.weight - latest.weight).toFixed(1) : '0';
  const co2Spike = latest ? Math.round(latest.co2 || 500) : '0';
  const swarmCount = swarmEvents.filter(e => e.hive === selectedHive).length;

  const getHiveStatus = (hiveId) => {
    const hiveMetrics = metrics.filter(m => m.hive === hiveId);
    return getStatus(hiveMetrics.length >= 10 ? detectSwarmPattern(hiveMetrics)?.risk || 'Low Risk' : 'Low Risk');
  };

  const formatHiveName = (hiveId) => {
    const status = getHiveStatus(hiveId);
    const hiveNum = parseInt(hiveId.replace('hive', ''));
    if (hiveNum <= 40 && status.label) return `${hiveId.toUpperCase()}_${status.label}`;
    return hiveId.toUpperCase();
  };

  if (loading) return <div className="loader">Loading swarm analytics...</div>;
  if (!data) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="dashboard-grid"><div className="card welcome-card" style={{ borderLeft: '4px solid var(--accent-crimson)' }}>
        <div className="welcome-content"><div className="welcome-text"><h2>🐝 Colony Swarming Prediction</h2> </div>
        <Zap size={48} color="var(--accent-crimson)" /></div></div></div>

      <div className="card" style={{ padding: '1rem' }}>
        <div className="chart-header" style={{ marginBottom: '0.75rem' }}><h3>⚠️ Swarm Risk Levels</h3></div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', justifyContent: 'space-between' }}>
          {RISK_LEVELS.map(level => (<div key={level.range} style={{ flex: 1, minWidth: '150px', background: `${level.color}10`, borderRadius: '8px', padding: '0.75rem', borderLeft: `4px solid ${level.color}` }}>
            <strong style={{ color: level.color }}>{level.range}</strong><p style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: 'var(--text-secondary)' }}>{level.description}</p></div>))}
        </div>
      </div>

      <div className="card" style={{ padding: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
          <div style={{ padding: '0.6rem', background: `linear-gradient(135deg, ${getStatus(riskLevel).color}20, transparent)`, borderRadius: '6px', borderLeft: `3px solid ${getStatus(riskLevel).color}` }}>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Swarm Risk Level</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: getStatus(riskLevel).color }}>{riskLevel}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Confidence: {(confidence * 100).toFixed(0)}%</div>
          </div>
          <div style={{ padding: '0.6rem', background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), transparent)', borderRadius: '6px', borderLeft: '3px solid #f59e0b' }}>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Weight Drop</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#f59e0b' }}>{weightDrop} kg</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Threshold: 2-5 kg</div>
          </div>
          <div style={{ padding: '0.6rem', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), transparent)', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>CO2 Spike</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#10b981' }}>{co2Spike} ppm</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Threshold: {'>'} 1500 ppm</div>
          </div>
          <div style={{ padding: '0.6rem', background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), transparent)', borderRadius: '6px', borderLeft: '3px solid #ef4444' }}>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Swarm Events</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#ef4444' }}>{swarmCount}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Events detected</div>
          </div>
        </div>

        <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '0.75rem' }}>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Select Hive:</h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', maxHeight: '150px', overflowY: 'auto', padding: '0.25rem' }}>
            {hives.map(hive => {
              const isSelected = selectedHive === hive;
              const displayName = formatHiveName(hive);
              const status = getHiveStatus(hive);
              return (<button key={hive} onClick={() => setSelectedHive(hive)} style={{ padding: '0.2rem 0.5rem', background: isSelected ? `${status.color}20` : 'transparent', color: isSelected ? '#ffffff' : 'var(--text-secondary)', border: isSelected ? `1.5px solid ${status.color}` : '1px solid transparent', borderRadius: '3px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: isSelected ? 600 : 400, fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{displayName}</button>);
            })}
          </div>
          <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}><span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }} />R - Risky</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}><span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />P - Pending</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}><span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />I - Ideal</span>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: '0.4rem 0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <button onClick={() => windowNumber + 1 < totalWindows && setWindowNumber(windowNumber + 1)} disabled={windowNumber + 1 >= totalWindows} style={{ background: '#2d3748', border: 'none', padding: '0.2rem 0.5rem', borderRadius: '4px', cursor: 'pointer' }}><ChevronLeft size={14} /></button>
          <span style={{ fontSize: '0.7rem', fontFamily: 'monospace' }}>{windowDesc}</span>
          <button onClick={() => windowNumber > 0 && setWindowNumber(windowNumber - 1)} disabled={windowNumber === 0} style={{ background: '#2d3748', border: 'none', padding: '0.2rem 0.5rem', borderRadius: '4px', cursor: 'pointer' }}><ChevronRight size={14} /></button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <span style={{ fontSize: '0.65rem' }}>Window:</span>
          <select value={windowSize} onChange={(e) => { setWindowSize(Number(e.target.value)); setWindowNumber(0); }} style={{ background: '#1e293b', border: '1px solid #334155', padding: '0.1rem 0.3rem', borderRadius: '3px', fontSize: '0.65rem' }}>
            <option value={25}>25</option><option value={50}>50</option><option value={100}>100</option><option value={200}>200</option>
          </select>
        </div>
      </div>

      <div className="card chart-card"><div className="chart-header"><div className="chart-title"><h3>Swarm Detection Timeline</h3><p>Weight drop and CO2 spike correlation analysis</p></div></div>
        <div className="chart-container" style={{ height: '250px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={windowData.map(d => ({ ...d, displayTime: new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), weightVal: parseFloat(d.weight), co2Val: parseFloat(d.co2), isSwarmEvent: windowSwarmEvents.some(e => e.timestamp === d.timestamp) }))} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="displayTime" stroke="var(--text-secondary)" minTickGap={60} />
              <YAxis yAxisId="weight" stroke="var(--accent-gold)" unit="kg" />
              <YAxis yAxisId="co2" orientation="right" stroke="var(--accent-emerald)" unit="ppm" />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
              <Legend />
              <Line yAxisId="weight" type="monotone" dataKey="weightVal" name="Hive Weight" stroke="var(--accent-gold)" strokeWidth={2} dot={false} />
              <Line yAxisId="co2" type="monotone" dataKey="co2Val" name="CO2" stroke="var(--accent-emerald)" strokeWidth={1.5} dot={false} />
              <Scatter yAxisId="weight" name="Swarm Events" data={windowData.filter(d => windowSwarmEvents.some(e => e.timestamp === d.timestamp))} dataKey="weightVal" fill="var(--accent-crimson)" shape="star" legendType="line" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card"><div className="chart-header"><div className="chart-title"><h3>Swarm Events Log</h3><p>Recent swarm events detected for this hive</p></div></div>
        {windowSwarmEvents.length === 0 ? (<div style={{ textAlign: 'center', padding: '1.5rem' }}><ShieldAlert size={24} style={{ color: 'var(--text-secondary)' }} /><p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No swarm events detected</p></div>) : (
          <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
            <table className="custom-table" style={{ fontSize: '0.7rem' }}>
              <thead><tr><th>Hive</th><th>Time</th><th>Weight Drop</th><th>CO2 Spike</th><th>Confidence</th></tr></thead>
              <tbody>{windowSwarmEvents.map((evt, idx) => (<tr key={idx} style={{ cursor: 'pointer' }} onClick={() => setSelectedHive(evt.hive)}>
                <td style={{ fontWeight: 600, color: 'var(--accent-crimson)' }}>{evt.hive.toUpperCase()}</td>
                <td>{new Date(evt.timestamp).toLocaleString()}</td>
                <td style={{ color: 'var(--accent-crimson)' }}>{evt.weightChange} kg</td>
                <td style={{ color: 'var(--accent-emerald)' }}>{evt.co2} ppm</td>
                <td>{(evt.confidence || 85)}%</td>
              </tr>))}</tbody>
            </table>
          </div>)}
      </div>

      <div className="card" style={{ padding: '0' }}>
        <button onClick={() => setShowExplanation(!showExplanation)} style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', background: 'rgba(255,255,255,0.02)', border: 'none', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
          <span><Info size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} /> How are swarming events detected?</span>
          {showExplanation ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        {showExplanation && (<div style={{ padding: '0.75rem 1rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <h4 style={{ color: 'var(--accent-crimson)', fontSize: '0.85rem' }}>🐝 Swarming Detection Algorithm</h4>
          <ul style={{ marginLeft: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
            <li><strong>Weight Drop (2-5 kg):</strong> Sudden decrease in hive weight as bees leave</li>
            <li><strong>CO2 Spike ({'>'}1500 ppm):</strong> Increased respiration from bees preparing to swarm</li>
            <li><strong>Temperature Deviation:</strong> Crowding causes localized warming</li>
            <li><strong>Pattern Recognition:</strong> Combined analysis of all parameters</li>
          </ul>
          <h4 style={{ color: 'var(--accent-cyan)', fontSize: '0.85rem', marginTop: '0.5rem' }}>⏱️ Response Recommendations</h4>
          <ul style={{ marginLeft: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
            <li><strong>High Risk:</strong> Check trees within 2 hours, prepare swarm traps</li>
            <li><strong>Moderate Risk:</strong> Increase monitoring frequency, inspect hives</li>
            <li><strong>Low Risk:</strong> Continue routine monitoring</li>
          </ul>
        </div>)}
      </div>
    </div>
  );
}

 