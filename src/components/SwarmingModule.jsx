// import React, { useState } from 'react';
// import {
//   LineChart,
//   Line,
//   BarChart,
//   Bar,
//   XAxis,
//   YAxis,
//   CartesianGrid,
//   Tooltip,
//   Legend,
//   ResponsiveContainer,
//   Scatter
// } from 'recharts';
// import { ShieldAlert, Zap, Thermometer, Info, AlertTriangle, AlertCircle } from 'lucide-react';

// export default function SwarmingModule({ data, processed }) {
//   const [selectedHive, setSelectedHive] = useState(processed.hives[0] || 'hive41');

//   const swarmingPatterns = processed?.swarmingPatterns;

//   // Filter raw data for selected hive
//   const hiveRows = data
//     .filter(d => d.hive === selectedHive)
//     .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

//   // Find swarming events detected for this hive
//   const swarmEvents = processed.swarmingEvents || [];
//   const localSwarmEvents = swarmEvents.filter(e => e.hive === selectedHive);

//   // Annotate data for chart visualization with proper numeric parsing
//   const chartData = hiveRows.map((d, idx) => {
//     const weightVal = parseFloat(String(d.weight));
//     const co2Val = parseFloat(String(d.co2));
//     const isEvent = swarmEvents.some(e => e.hive === d.hive && e.timestamp === d.timestamp);
//     const prevWeight = idx > 0 ? parseFloat(String(hiveRows[idx-1].weight)) : weightVal;
//     const weightDrop = prevWeight - weightVal;
    
//     return {
//       ...d,
//       displayTime: new Date(d.timestamp).toLocaleDateString() + ' ' + 
//                    new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
//       weightVal: isNaN(weightVal) ? 0 : weightVal,
//       co2Val: isNaN(co2Val) ? 0 : co2Val,
//       // Mark swarm only when significant weight drop happens
//       swarmMarker: (isEvent && weightDrop > 0.5) ? weightVal : null,
//       weightDrop: weightDrop
//     };
//   });

//   // Find min/max for better axis scaling
//   const maxWeight = Math.max(...chartData.map(d => d.weightVal), 60);
//   const maxCo2 = Math.max(...chartData.map(d => d.co2Val), 24000);

//   return (
//     <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

//       {/* HEADER SECTION */}
//       <div className="dashboard-grid">
//         <div className="card welcome-card" style={{ 
//           borderLeft: '4px solid var(--accent-crimson)', 
//           background: 'linear-gradient(135deg, rgba(20, 26, 40, 0.8) 0%, rgba(239, 68, 68, 0.08) 100%)' 
//         }}>
//           <div className="welcome-content">
//             <div className="welcome-text">
//               <h2>Module 2: Colony Swarming Prediction</h2>
//               <p>
//                 Swarming is the natural reproduction mechanism where half of the worker colony leaves with the old queen to establish a new home.
//                 This results in a <strong>sudden weight drop of 2 to 5 kg</strong> within 1-2 hours, accompanied by a <strong>rapid spike in CO2 &gt; 1500ppm</strong> and an elevated temperature deviation as bees engorge on honey and crowd prior to takeoff.
//               </p>
//             </div>
//             <Zap size={48} color="var(--accent-crimson)" style={{ filter: 'drop-shadow(0 0 10px var(--accent-crimson-glow))' }} />
//           </div>
//         </div>
//       </div>

//       {/* QUICK STATS & WARNING FLAGS */}
//       <div className="dashboard-grid">
//         <div className="card highlight-crimson">
//           <div className="stat-header">
//             <span>Swarm Events Detected</span>
//             <ShieldAlert size={16} color="var(--accent-crimson)" />
//           </div>
//           <div className="stat-value">
//             {swarmEvents.length}
//             <span className="stat-unit">across apiary</span>
//           </div>
//           <div className="stat-footer">
//             <span>Trigger: Weight drop &lt; -0.5kg &amp; CO2 trend spike</span>
//           </div>
//         </div>

//         <div className="card highlight-gold">
//           <div className="stat-header">
//             <span>CO2 Spikes Registered</span>
//             <AlertCircle size={16} color="var(--accent-gold)" />
//           </div>
//           <div className="stat-value">
//             {data.filter(d => parseFloat(String(d.co2)) > 1800).length}
//             <span className="stat-unit">total logs</span>
//           </div>
//           <div className="stat-footer">
//             <span>Critical threshold set at 1,800 ppm</span>
//           </div>
//         </div>

//         <div className="card highlight-emerald">
//           <div className="stat-header">
//             <span>Current Risk Assessment</span>
//             <Thermometer size={16} color="var(--accent-emerald)" />
//           </div>
//           <div className="stat-value" style={{ color: localSwarmEvents.length > 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)' }}>
//             {localSwarmEvents.length > 0 ? 'CRITICAL ALERT' : 'SECURE'}
//           </div>
//           <div className="stat-footer">
//             <span>Selected Unit: {selectedHive.toUpperCase()}</span>
//           </div>
//         </div>
//       </div>

//       {/* MAIN CHART: CO2 Spike + Weight Drop Correlation */}
//       <div className="dashboard-grid">
//         <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
//           <div className="chart-header">
//             <div className="chart-title">
//               <h3>Swarm Alarm Event Correlation Chart</h3>
//               <p>Sudden drop in weight coupled with a CO2 concentration surge for {selectedHive.toUpperCase()}</p>
//             </div>
//             <div className="chart-controls">
//               <select
//                 className="chart-select"
//                 value={selectedHive}
//                 onChange={(e) => setSelectedHive(e.target.value)}
//                 style={{
//                   padding: '0.5rem 1rem',
//                   borderRadius: '8px',
//                   background: 'var(--card-bg)',
//                   border: '1px solid var(--card-border)',
//                   color: 'var(--text-primary)'
//                 }}
//               >
//                 {processed.hives.map(hive => (
//                   <option key={hive} value={hive}>{hive.toUpperCase()}</option>
//                 ))}
//               </select>
//             </div>
//           </div>

//           <div className="chart-container" style={{ height: '400px', width: '100%', marginTop: '1rem' }}>
//             <ResponsiveContainer width="100%" height="100%">
//               <LineChart 
//                 data={chartData} 
//                 margin={{ top: 20, right: 35, left: 45, bottom: 20 }}
//               >
//                 <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                
//                 {/* X-Axis - Time */}
//                 <XAxis 
//                   dataKey="displayTime" 
//                   stroke="var(--text-secondary)" 
//                   tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
//                   angle={-25}
//                   textAnchor="end"
//                   height={60}
//                   interval="preserveStartEnd"
//                   minTickGap={50}
//                 />
                
//                 {/* Left Y-Axis - Weight (kg) */}
//                 <YAxis 
//                   yAxisId="weight" 
//                   orientation="left"
//                   stroke="var(--accent-gold)" 
//                   tick={{ fill: 'var(--accent-gold)', fontSize: 11 }}
//                   label={{ 
//                     value: 'Weight (kg)', 
//                     angle: -90, 
//                     position: 'insideLeft', 
//                     fill: 'var(--accent-gold)',
//                     style: { textAnchor: 'middle', fontSize: 12 },
//                     offset: -30
//                   }}
//                   domain={[0, Math.ceil(maxWeight * 1.1)]}
//                   tickCount={8}
//                 />
                
//                 {/* Right Y-Axis - CO2 (ppm) */}
//                 <YAxis 
//                   yAxisId="co2" 
//                   orientation="right"
//                   stroke="var(--accent-emerald)" 
//                   tick={{ fill: 'var(--accent-emerald)', fontSize: 11 }}
//                   label={{ 
//                     value: 'CO₂ Concentration (ppm)', 
//                     angle: 90, 
//                     position: 'insideRight', 
//                     fill: 'var(--accent-emerald)',
//                     style: { textAnchor: 'middle', fontSize: 12 },
//                     offset: -25
//                   }}
//                   domain={[0, Math.ceil(maxCo2 * 1.1)]}
//                   tickCount={8}
//                 />
                
//                 <Tooltip
//                   contentStyle={{ 
//                     background: '#1e293b', 
//                     border: '1px solid rgba(255,255,255,0.2)',
//                     borderRadius: '8px',
//                     color: 'var(--text-primary)'
//                   }}
//                   formatter={(value, name) => {
//                     if (name === 'Hive Weight') return [`${Number(value).toFixed(1)} kg`, 'Weight'];
//                     if (name === 'CO2 Concentration') return [`${Math.round(Number(value))} ppm`, 'CO₂'];
//                     if (name === 'Swarm Event Takeoff') return [`${Number(value).toFixed(1)} kg`, '🐝 Swarm Takeoff'];
//                     return [value, name];
//                   }}
//                 />
                
//                 <Legend 
//                   wrapperStyle={{ paddingTop: '10px' }}
//                   formatter={(value) => {
//                     if (value === 'Hive Weight') return '🍯 Hive Weight';
//                     if (value === 'CO2 Concentration') return '🌫️ CO₂ Concentration';
//                     if (value === 'Swarm Event Takeoff') return '⚠️ Swarm Event Takeoff';
//                     return value;
//                   }}
//                 />
                
//                 {/* Weight Line */}
//                 <Line 
//                   yAxisId="weight" 
//                   type="monotone" 
//                   dataKey="weightVal" 
//                   name="Hive Weight" 
//                   stroke="var(--accent-gold)" 
//                   strokeWidth={2.5} 
//                   dot={false}
//                   activeDot={{ r: 6, fill: 'var(--accent-gold)' }}
//                 />
                
//                 {/* CO2 Line */}
//                 <Line 
//                   yAxisId="co2" 
//                   type="monotone" 
//                   dataKey="co2Val" 
//                   name="CO2 Concentration" 
//                   stroke="var(--accent-emerald)" 
//                   strokeWidth={2} 
//                   dot={false}
//                   activeDot={{ r: 5, fill: 'var(--accent-emerald)' }}
//                 />
                
//                 {/* Scatter points for Swarm Events */}
//                 <Scatter 
//                   yAxisId="weight" 
//                   name="Swarm Event Takeoff" 
//                   data={chartData.filter(d => d.swarmMarker !== null)} 
//                   dataKey="swarmMarker" 
//                   fill="#ef4444"
//                   shape="circle"
//                   legendType="circle"
//                 />
//               </LineChart>
//             </ResponsiveContainer>
//           </div>
          
//           {/* Chart Legend Explanation */}
//           <div style={{ 
//             marginTop: '1rem', 
//             padding: '0.75rem', 
//             background: 'rgba(0,0,0,0.2)', 
//             borderRadius: '6px',
//             fontSize: '0.75rem',
//             color: 'var(--text-muted)',
//             display: 'flex',
//             gap: '1.5rem',
//             flexWrap: 'wrap'
//           }}>
//             <span>🔴 <strong style={{ color: 'var(--accent-crimson)' }}>Red Dot:</strong> Detected swarm event (sudden weight drop + CO₂ spike)</span>
//             <span>🟡 <strong style={{ color: 'var(--accent-gold)' }}>Gold Line:</strong> Hive weight trend (kg)</span>
//             <span>🟢 <strong style={{ color: 'var(--accent-emerald)' }}>Green Line:</strong> CO₂ concentration (ppm)</span>
//             <span>📊 <strong>Alert Thresholds:</strong> Weight drop &gt;0.5kg/hr + CO₂ &gt;1500ppm</span>
//           </div>
//         </div>

//         {/* DETECTED ALERTS LIST */}
//         <div className="card">
//           <div className="chart-header">
//             <div className="chart-title">
//               <h3>Swarm Alarm Event Logs</h3>
//               <p>Historical alarms captured during telemetry processing</p>
//             </div>
//             <ShieldAlert size={20} color="var(--accent-crimson)" />
//           </div>

//           <div className="table-container" style={{ maxHeight: '320px', overflowY: 'auto' }}>
//             {swarmEvents.length === 0 ? (
//               <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
//                 <Info size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
//                 <p>No swarming events detected in the active dataset. Hive clusters appear stable.</p>
//               </div>
//             ) : (
//               <table className="custom-table" style={{ fontSize: '0.825rem', width: '100%', borderCollapse: 'collapse' }}>
//                 <thead>
//                   <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Hive</th>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Time</th>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Wt Drop</th>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>CO2 Max</th>
//                   </tr>
//                 </thead>
//                 <tbody>
//                   {swarmEvents.map((evt, idx) => (
//                     <tr 
//                       key={idx} 
//                       style={{ cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)' }} 
//                       onClick={() => setSelectedHive(evt.hive)}
//                     >
//                       <td style={{ fontWeight: 600, color: 'var(--accent-crimson)', padding: '0.5rem' }}>{evt.hive.toUpperCase()}</td>
//                       <td style={{ padding: '0.5rem', fontSize: '0.75rem' }}>
//                         {new Date(evt.timestamp).toLocaleDateString()} {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
//                       </td>
//                       <td style={{ color: 'var(--accent-crimson)', padding: '0.5rem' }}>{evt.weightChange} kg</td>
//                       <td style={{ color: 'var(--accent-emerald)', padding: '0.5rem' }}>{evt.co2} ppm</td>
//                     </tr>
//                   ))}
//                 </tbody>
//               </table>
//             )}
//           </div>

//           <div style={{ marginTop: '1rem', borderTop: '1px solid var(--card-border)', paddingTop: '0.75rem' }}>
//             <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Swarming Recommendations:</h4>
//             <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
//               ⚠️ Upon swarm notification, check trees near the apiary within 2 hours. Swarms cluster nearby before searching for permanent nest cavities. Keep a swarm retrieval trap box on standby.
//             </p>
//           </div>
//         </div>
//       </div>

//       {/* SWARMING SIGNATURE ANALYSIS */}
//       <div className="card" style={{ borderLeft: '4px solid var(--accent-gold)' }}>
//         <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
//           Swarming Signatures - Pattern Analysis
//         </h2>

//         <div className="dashboard-grid" style={{ marginBottom: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
//           <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
//             <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)' }}>Weight Change Distribution (Normal Period)</h4>
//             <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Frequency of weight fluctuations under stable colony conditions</p>
//             <div className="chart-container" style={{ height: '260px', marginTop: '0.5rem' }}>
//               <ResponsiveContainer width="100%" height="100%">
//                 <BarChart data={swarmingPatterns?.weight_change?.normal || []} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
//                   <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
//                   <XAxis dataKey="range" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
//                   <Legend />
//                   <Bar dataKey="count" name="Normal Weight Change" fill="var(--accent-gold)" radius={[4, 4, 0, 0]} />
//                 </BarChart>
//               </ResponsiveContainer>
//             </div>
//           </div>

//           <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
//             <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)' }}>CO2 Trend Distribution (Pre-Swarming Period)</h4>
//             <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Significant CO2 surges registered during swarming preparation</p>
//             <div className="chart-container" style={{ height: '260px', marginTop: '0.5rem' }}>
//               <ResponsiveContainer width="100%" height="100%">
//                 <BarChart data={swarmingPatterns?.co2_trend?.pre_swarming || []} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
//                   <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
//                   <XAxis dataKey="range" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
//                   <Legend />
//                   <Bar dataKey="count" name="Pre-Swarming CO2" fill="var(--accent-crimson)" radius={[4, 4, 0, 0]} />
//                 </BarChart>
//               </ResponsiveContainer>
//             </div>
//           </div>
//         </div>

//         <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
//           Indicator Correlation Matrix
//         </h3>
//         <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
//           Pearson correlation coefficients between swarming early warning telemetry indicators
//         </p>

//         {swarmingPatterns?.indicator_correlation ? (
//           <div className="table-container" style={{ overflowX: 'auto' }}>
//             <table className="custom-table" style={{ textAlign: 'center', width: '100%', borderCollapse: 'collapse' }}>
//               <thead>
//                 <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
//                   <th style={{ textAlign: 'left', padding: '0.75rem' }}>Indicator</th>
//                   <th style={{ padding: '0.75rem' }}>Weight Drop</th>
//                   <th style={{ padding: '0.75rem' }}>CO2 Spike</th>
//                   <th style={{ padding: '0.75rem' }}>Temp Spike</th>
//                 </tr>
//               </thead>
//               <tbody>
//                 {Object.entries(swarmingPatterns.indicator_correlation).map(([rowKey, colObj]) => (
//                   <tr key={rowKey} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
//                     <td style={{ fontWeight: 600, textAlign: 'left', padding: '0.5rem 0.75rem' }}>{rowKey}</td>
//                     <td style={{ 
//                       color: colObj["Weight Drop"] !== undefined && Math.abs(colObj["Weight Drop"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
//                       padding: '0.5rem'
//                     }}>
//                       {colObj["Weight Drop"] !== undefined ? colObj["Weight Drop"].toFixed(2) : '—'}
//                     </td>
//                     <td style={{ 
//                       color: colObj["CO2 Spike"] !== undefined && Math.abs(colObj["CO2 Spike"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
//                       padding: '0.5rem'
//                     }}>
//                       {colObj["CO2 Spike"] !== undefined ? colObj["CO2 Spike"].toFixed(2) : '—'}
//                     </td>
//                     <td style={{ 
//                       color: colObj["Temp Spike"] !== undefined && Math.abs(colObj["Temp Spike"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
//                       padding: '0.5rem'
//                     }}>
//                       {colObj["Temp Spike"] !== undefined ? colObj["Temp Spike"].toFixed(2) : '—'}
//                     </td>
//                   </tr>
//                 ))}
//               </tbody>
//             </table>
//           </div>
//         ) : (
//           <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
//             <Info size={16} />
//             <span>Swarming signature pattern telemetry analysis is loading or not available in the current dataset.</span>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// }

// import React, { useState } from 'react';
// import {
//   LineChart,
//   Line,
//   BarChart,
//   Bar,
//   XAxis,
//   YAxis,
//   CartesianGrid,
//   Tooltip,
//   Legend,
//   ResponsiveContainer,
//   Scatter
// } from 'recharts';
// import { 
//   ShieldAlert, Zap, Thermometer, Info, AlertTriangle, AlertCircle,
//   Trophy, Download, BarChart2, TrendingUp, Eye, EyeOff
// } from 'lucide-react';
// import { useNavigate } from 'react-router-dom';
 
// export default function SwarmingModule({ data, processed }) {
//   const [selectedHive, setSelectedHive] = useState(processed.hives[0] || 'hive41');
//   const navigate = useNavigate();

//   const swarmingPatterns = processed?.swarmingPatterns;

//   // Navigate to model comparison page
//   const goToModelComparison = () => {
//     navigate('/swarming/model-comparison');
//   };

//   // Filter raw data for selected hive - FIXED: use hive_id
//   const hiveRows = data
//     .filter(d => d.hive_id === selectedHive)
//     .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

//   // Find swarming events detected for this hive
//   const swarmEvents = processed.swarmingEvents || [];
//   const localSwarmEvents = swarmEvents.filter(e => e.hive === selectedHive);

//   // Annotate data for chart visualization with proper numeric parsing
//   const chartData = hiveRows.map((d, idx) => {
//     const weightVal = parseFloat(String(d.weight));
//     const co2Val = parseFloat(String(d.co2));
//     const isEvent = swarmEvents.some(e => e.hive === d.hive_id && e.timestamp === d.timestamp);
//     const prevWeight = idx > 0 ? parseFloat(String(hiveRows[idx-1].weight)) : weightVal;
//     const weightDrop = prevWeight - weightVal;
    
//     return {
//       ...d,
//       displayTime: new Date(d.timestamp).toLocaleDateString() + ' ' + 
//                    new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
//       weightVal: isNaN(weightVal) ? 0 : weightVal,
//       co2Val: isNaN(co2Val) ? 0 : co2Val,
//       swarmMarker: (isEvent && weightDrop > 0.5) ? weightVal : null,
//       weightDrop: weightDrop
//     };
//   });

//   // Find min/max for better axis scaling
//   const maxWeight = Math.max(...chartData.map(d => d.weightVal), 60);
//   const maxCo2 = Math.max(...chartData.map(d => d.co2Val), 24000);

//   return (
//     <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

//       {/* HEADER SECTION */}
//       <div className="dashboard-grid">
//         <div className="card welcome-card" style={{ 
//           borderLeft: '4px solid var(--accent-crimson)', 
//           background: 'linear-gradient(135deg, rgba(20, 26, 40, 0.8) 0%, rgba(239, 68, 68, 0.08) 100%)' 
//         }}>
//           <div className="welcome-content">
//             <div className="welcome-text">
//               <h2>Module 2: Colony Swarming Prediction</h2>
//               <p>
//                 Swarming is the natural reproduction mechanism where half of the worker colony leaves with the old queen to establish a new home.
//                 This results in a <strong>sudden weight drop of 2 to 5 kg</strong> within 1-2 hours, accompanied by a <strong>rapid spike in CO2 &gt; 1500ppm</strong> and an elevated temperature deviation as bees engorge on honey and crowd prior to takeoff.
//               </p>
//             </div>
//             <Zap size={48} color="var(--accent-crimson)" style={{ filter: 'drop-shadow(0 0 10px var(--accent-crimson-glow))' }} />
//           </div>
//         </div>
//       </div>

//       {/* QUICK STATS & WARNING FLAGS */}
//       <div className="dashboard-grid">
//         <div className="card highlight-crimson">
//           <div className="stat-header">
//             <span>Swarm Events Detected</span>
//             <ShieldAlert size={16} color="var(--accent-crimson)" />
//           </div>
//           <div className="stat-value">
//             {swarmEvents.length}
//             <span className="stat-unit">across apiary</span>
//           </div>
//           <div className="stat-footer">
//             <span>Trigger: Weight drop &lt; -0.5kg &amp; CO2 trend spike</span>
//           </div>
//         </div>

//         <div className="card highlight-gold">
//           <div className="stat-header">
//             <span>CO2 Spikes Registered</span>
//             <AlertCircle size={16} color="var(--accent-gold)" />
//           </div>
//           <div className="stat-value">
//             {data.filter(d => parseFloat(String(d.co2)) > 1800).length}
//             <span className="stat-unit">total logs</span>
//           </div>
//           <div className="stat-footer">
//             <span>Critical threshold set at 1,800 ppm</span>
//           </div>
//         </div>

//         <div className="card highlight-emerald">
//           <div className="stat-header">
//             <span>Current Risk Assessment</span>
//             <Thermometer size={16} color="var(--accent-emerald)" />
//           </div>
//           <div className="stat-value" style={{ color: localSwarmEvents.length > 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)' }}>
//             {localSwarmEvents.length > 0 ? 'CRITICAL ALERT' : 'SECURE'}
//           </div>
//           <div className="stat-footer">
//             <span>Selected Unit: {selectedHive.toUpperCase()}</span>
//           </div>
//         </div>
//       </div>

//       {/* BUTTON ROW - View Model Comparison */}
//       <div className="dashboard-grid">
//         <div className="card" style={{ gridColumn: 'span 3', textAlign: 'center' }}>
//           <button
//             onClick={goToModelComparison}
//             style={{
//               background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
//               border: 'none',
//               padding: '12px 24px',
//               borderRadius: '8px',
//               color: 'white',
//               fontWeight: 600,
//               cursor: 'pointer',
//               display: 'inline-flex',
//               alignItems: 'center',
//               gap: '10px',
//               fontSize: '14px',
//               transition: 'transform 0.2s, box-shadow 0.2s'
//             }}
//             onMouseEnter={(e) => {
//               e.currentTarget.style.transform = 'translateY(-2px)';
//               e.currentTarget.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
//             }}
//             onMouseLeave={(e) => {
//               e.currentTarget.style.transform = 'translateY(0)';
//               e.currentTarget.style.boxShadow = 'none';
//             }}
//           >
//             <BarChart2 size={18} />
//             View Model Comparison Results (RF vs XGBoost)
//           </button>
//           <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '8px' }}>
//             Compare Random Forest and XGBoost models trained on this dataset
//           </p>
//         </div>
//       </div>

//       {/* MAIN CHART: CO2 Spike + Weight Drop Correlation */}
//       <div className="dashboard-grid">
//         <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
//           <div className="chart-header">
//             <div className="chart-title">
//               <h3>Swarm Alarm Event Correlation Chart</h3>
//               <p>Sudden drop in weight coupled with a CO2 concentration surge for {selectedHive.toUpperCase()}</p>
//             </div>
//             <div className="chart-controls">
//               <select
//                 className="chart-select"
//                 value={selectedHive}
//                 onChange={(e) => setSelectedHive(e.target.value)}
//                 style={{
//                   padding: '0.5rem 1rem',
//                   borderRadius: '8px',
//                   background: 'var(--card-bg)',
//                   border: '1px solid var(--card-border)',
//                   color: 'var(--text-primary)'
//                 }}
//               >
//                 {processed.hives.map(hive => (
//                   <option key={hive} value={hive}>{hive.toUpperCase()}</option>
//                 ))}
//               </select>
//             </div>
//           </div>

//           <div className="chart-container" style={{ height: '400px', width: '100%', marginTop: '1rem' }}>
//             <ResponsiveContainer width="100%" height="100%">
//               <LineChart 
//                 data={chartData} 
//                 margin={{ top: 20, right: 35, left: 45, bottom: 20 }}
//               >
//                 <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                
//                 <XAxis 
//                   dataKey="displayTime" 
//                   stroke="var(--text-secondary)" 
//                   tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
//                   angle={-25}
//                   textAnchor="end"
//                   height={60}
//                   interval="preserveStartEnd"
//                   minTickGap={50}
//                 />
                
//                 <YAxis 
//                   yAxisId="weight" 
//                   orientation="left"
//                   stroke="var(--accent-gold)" 
//                   tick={{ fill: 'var(--accent-gold)', fontSize: 11 }}
//                   label={{ 
//                     value: 'Weight (kg)', 
//                     angle: -90, 
//                     position: 'insideLeft', 
//                     fill: 'var(--accent-gold)',
//                     style: { textAnchor: 'middle', fontSize: 12 },
//                     offset: -30
//                   }}
//                   domain={[0, Math.ceil(maxWeight * 1.1)]}
//                   tickCount={8}
//                 />
                
//                 <YAxis 
//                   yAxisId="co2" 
//                   orientation="right"
//                   stroke="var(--accent-emerald)" 
//                   tick={{ fill: 'var(--accent-emerald)', fontSize: 11 }}
//                   label={{ 
//                     value: 'CO₂ Concentration (ppm)', 
//                     angle: 90, 
//                     position: 'insideRight', 
//                     fill: 'var(--accent-emerald)',
//                     style: { textAnchor: 'middle', fontSize: 12 },
//                     offset: -25
//                   }}
//                   domain={[0, Math.ceil(maxCo2 * 1.1)]}
//                   tickCount={8}
//                 />
                
//                 <Tooltip
//                   contentStyle={{ 
//                     background: '#1e293b', 
//                     border: '1px solid rgba(255,255,255,0.2)',
//                     borderRadius: '8px',
//                     color: 'var(--text-primary)'
//                   }}
//                   formatter={(value, name) => {
//                     if (name === 'Hive Weight') return [`${Number(value).toFixed(1)} kg`, 'Weight'];
//                     if (name === 'CO2 Concentration') return [`${Math.round(Number(value))} ppm`, 'CO₂'];
//                     if (name === 'Swarm Event Takeoff') return [`${Number(value).toFixed(1)} kg`, '🐝 Swarm Takeoff'];
//                     return [value, name];
//                   }}
//                 />
                
//                 <Legend 
//                   wrapperStyle={{ paddingTop: '10px' }}
//                   formatter={(value) => {
//                     if (value === 'Hive Weight') return '🍯 Hive Weight';
//                     if (value === 'CO2 Concentration') return '🌫️ CO₂ Concentration';
//                     if (value === 'Swarm Event Takeoff') return '⚠️ Swarm Event Takeoff';
//                     return value;
//                   }}
//                 />
                
//                 <Line 
//                   yAxisId="weight" 
//                   type="monotone" 
//                   dataKey="weightVal" 
//                   name="Hive Weight" 
//                   stroke="var(--accent-gold)" 
//                   strokeWidth={2.5} 
//                   dot={false}
//                   activeDot={{ r: 6, fill: 'var(--accent-gold)' }}
//                 />
                
//                 <Line 
//                   yAxisId="co2" 
//                   type="monotone" 
//                   dataKey="co2Val" 
//                   name="CO2 Concentration" 
//                   stroke="var(--accent-emerald)" 
//                   strokeWidth={2} 
//                   dot={false}
//                   activeDot={{ r: 5, fill: 'var(--accent-emerald)' }}
//                 />
                
//                 <Scatter 
//                   yAxisId="weight" 
//                   name="Swarm Event Takeoff" 
//                   data={chartData.filter(d => d.swarmMarker !== null)} 
//                   dataKey="swarmMarker" 
//                   fill="#ef4444"
//                   shape="circle"
//                   legendType="circle"
//                 />
//               </LineChart>
//             </ResponsiveContainer>
//           </div>
          
//           {/* Chart Legend Explanation */}
//           <div style={{ 
//             marginTop: '1rem', 
//             padding: '0.75rem', 
//             background: 'rgba(0,0,0,0.2)', 
//             borderRadius: '6px',
//             fontSize: '0.75rem',
//             color: 'var(--text-muted)',
//             display: 'flex',
//             gap: '1.5rem',
//             flexWrap: 'wrap'
//           }}>
//             <span>🔴 <strong style={{ color: 'var(--accent-crimson)' }}>Red Dot:</strong> Detected swarm event (sudden weight drop + CO₂ spike)</span>
//             <span>🟡 <strong style={{ color: 'var(--accent-gold)' }}>Gold Line:</strong> Hive weight trend (kg)</span>
//             <span>🟢 <strong style={{ color: 'var(--accent-emerald)' }}>Green Line:</strong> CO₂ concentration (ppm)</span>
//             <span>📊 <strong>Alert Thresholds:</strong> Weight drop &gt;0.5kg/hr + CO₂ &gt;1500ppm</span>
//           </div>
//         </div>

//         {/* DETECTED ALERTS LIST */}
//         <div className="card">
//           <div className="chart-header">
//             <div className="chart-title">
//               <h3>Swarm Alarm Event Logs</h3>
//               <p>Historical alarms captured during telemetry processing</p>
//             </div>
//             <ShieldAlert size={20} color="var(--accent-crimson)" />
//           </div>

//           <div className="table-container" style={{ maxHeight: '320px', overflowY: 'auto' }}>
//             {swarmEvents.length === 0 ? (
//               <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
//                 <Info size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
//                 <p>No swarming events detected in the active dataset. Hive clusters appear stable.</p>
//               </div>
//             ) : (
//               <table className="custom-table" style={{ fontSize: '0.825rem', width: '100%', borderCollapse: 'collapse' }}>
//                 <thead>
//                   <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Hive</th>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Time</th>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Wt Drop</th>
//                     <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>CO2 Max</th>
//                   </tr>
//                 </thead>
//                 <tbody>
//                   {swarmEvents.map((evt, idx) => (
//                     <tr 
//                       key={idx} 
//                       style={{ cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)' }} 
//                       onClick={() => setSelectedHive(evt.hive)}
//                     >
//                       <td style={{ fontWeight: 600, color: 'var(--accent-crimson)', padding: '0.5rem' }}>{evt.hive.toUpperCase()}</td>
//                       <td style={{ padding: '0.5rem', fontSize: '0.75rem' }}>
//                         {new Date(evt.timestamp).toLocaleDateString()} {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
//                       </td>
//                       <td style={{ color: 'var(--accent-crimson)', padding: '0.5rem' }}>{evt.weightChange} kg</td>
//                       <td style={{ color: 'var(--accent-emerald)', padding: '0.5rem' }}>{evt.co2} ppm</td>
//                     </tr>
//                   ))}
//                 </tbody>
//               </table>
//             )}
//           </div>

//           <div style={{ marginTop: '1rem', borderTop: '1px solid var(--card-border)', paddingTop: '0.75rem' }}>
//             <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Swarming Recommendations:</h4>
//             <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
//               ⚠️ Upon swarm notification, check trees near the apiary within 2 hours. Swarms cluster nearby before searching for permanent nest cavities. Keep a swarm retrieval trap box on standby.
//             </p>
//           </div>
//         </div>
//       </div>

//       {/* SWARMING SIGNATURE ANALYSIS */}
//       <div className="card" style={{ borderLeft: '4px solid var(--accent-gold)' }}>
//         <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
//           Swarming Signatures - Pattern Analysis
//         </h2>

//         <div className="dashboard-grid" style={{ marginBottom: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
//           <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
//             <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)' }}>Weight Change Distribution (Normal Period)</h4>
//             <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Frequency of weight fluctuations under stable colony conditions</p>
//             <div className="chart-container" style={{ height: '260px', marginTop: '0.5rem' }}>
//               <ResponsiveContainer width="100%" height="100%">
//                 <BarChart data={swarmingPatterns?.weight_change?.normal || []} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
//                   <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
//                   <XAxis dataKey="range" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
//                   <Legend />
//                   <Bar dataKey="count" name="Normal Weight Change" fill="var(--accent-gold)" radius={[4, 4, 0, 0]} />
//                 </BarChart>
//               </ResponsiveContainer>
//             </div>
//           </div>

//           <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
//             <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)' }}>CO2 Trend Distribution (Pre-Swarming Period)</h4>
//             <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Significant CO2 surges registered during swarming preparation</p>
//             <div className="chart-container" style={{ height: '260px', marginTop: '0.5rem' }}>
//               <ResponsiveContainer width="100%" height="100%">
//                 <BarChart data={swarmingPatterns?.co2_trend?.pre_swarming || []} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
//                   <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
//                   <XAxis dataKey="range" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
//                   <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
//                   <Legend />
//                   <Bar dataKey="count" name="Pre-Swarming CO2" fill="var(--accent-crimson)" radius={[4, 4, 0, 0]} />
//                 </BarChart>
//               </ResponsiveContainer>
//             </div>
//           </div>
//         </div>

//         <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
//           Indicator Correlation Matrix
//         </h3>
//         <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
//           Pearson correlation coefficients between swarming early warning telemetry indicators
//         </p>

//         {swarmingPatterns?.indicator_correlation ? (
//           <div className="table-container" style={{ overflowX: 'auto' }}>
//             <table className="custom-table" style={{ textAlign: 'center', width: '100%', borderCollapse: 'collapse' }}>
//               <thead>
//                 <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
//                   <th style={{ textAlign: 'left', padding: '0.75rem' }}>Indicator</th>
//                   <th style={{ padding: '0.75rem' }}>Weight Drop</th>
//                   <th style={{ padding: '0.75rem' }}>CO2 Spike</th>
//                   <th style={{ padding: '0.75rem' }}>Temp Spike</th>
//                  </tr>
//               </thead>
//               <tbody>
//                 {Object.entries(swarmingPatterns.indicator_correlation).map(([rowKey, colObj]) => (
//                   <tr key={rowKey} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
//                     <td style={{ fontWeight: 600, textAlign: 'left', padding: '0.5rem 0.75rem' }}>{rowKey}</td>
//                     <td style={{ 
//                       color: colObj["Weight Drop"] !== undefined && Math.abs(colObj["Weight Drop"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
//                       padding: '0.5rem'
//                     }}>
//                       {colObj["Weight Drop"] !== undefined ? colObj["Weight Drop"].toFixed(2) : '—'}
//                     </td>
//                     <td style={{ 
//                       color: colObj["CO2 Spike"] !== undefined && Math.abs(colObj["CO2 Spike"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
//                       padding: '0.5rem'
//                     }}>
//                       {colObj["CO2 Spike"] !== undefined ? colObj["CO2 Spike"].toFixed(2) : '—'}
//                     </td>
//                     <td style={{ 
//                       color: colObj["Temp Spike"] !== undefined && Math.abs(colObj["Temp Spike"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
//                       padding: '0.5rem'
//                     }}>
//                       {colObj["Temp Spike"] !== undefined ? colObj["Temp Spike"].toFixed(2) : '—'}
//                     </td>
//                    </tr>
//                 ))}
//               </tbody>
//             </table>
//           </div>
//         ) : (
//           <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
//             <Info size={16} />
//             <span>Swarming signature pattern telemetry analysis is loading or not available in the current dataset.</span>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// }


import React, { useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Scatter
} from 'recharts';
import { 
  ShieldAlert, Zap, Thermometer, Info, AlertTriangle, AlertCircle,
  BarChart2, X
} from 'lucide-react';
import ModelComparisonPage from './ModelComparisonPage';

export default function SwarmingModule({ data, processed }) {
  const [selectedHive, setSelectedHive] = useState(processed.hives[0] || 'hive41');
  const [showComparison, setShowComparison] = useState(false);

  const swarmingPatterns = processed?.swarmingPatterns;

  // Open model comparison modal
  const openModelComparison = () => {
    setShowComparison(true);
  };

  // Close model comparison modal
  const closeModelComparison = () => {
    setShowComparison(false);
  };

  // Filter raw data for selected hive - FIXED: use hive_id
  const hiveRows = data
    .filter(d => d.hive_id === selectedHive)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  // Find swarming events detected for this hive
  const swarmEvents = processed.swarmingEvents || [];
  const localSwarmEvents = swarmEvents.filter(e => e.hive === selectedHive);

  // Annotate data for chart visualization with proper numeric parsing
  const chartData = hiveRows.map((d, idx) => {
    const weightVal = parseFloat(String(d.weight));
    const co2Val = parseFloat(String(d.co2));
    const isEvent = swarmEvents.some(e => e.hive === d.hive_id && e.timestamp === d.timestamp);
    const prevWeight = idx > 0 ? parseFloat(String(hiveRows[idx-1].weight)) : weightVal;
    const weightDrop = prevWeight - weightVal;
    
    return {
      ...d,
      displayTime: new Date(d.timestamp).toLocaleDateString() + ' ' + 
                   new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      weightVal: isNaN(weightVal) ? 0 : weightVal,
      co2Val: isNaN(co2Val) ? 0 : co2Val,
      swarmMarker: (isEvent && weightDrop > 0.5) ? weightVal : null,
      weightDrop: weightDrop
    };
  });

  // Find min/max for better axis scaling
  const maxWeight = Math.max(...chartData.map(d => d.weightVal), 60);
  const maxCo2 = Math.max(...chartData.map(d => d.co2Val), 24000);

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* HEADER SECTION */}
        <div className="dashboard-grid">
          <div className="card welcome-card" style={{ 
            borderLeft: '4px solid var(--accent-crimson)', 
            background: 'linear-gradient(135deg, rgba(20, 26, 40, 0.8) 0%, rgba(239, 68, 68, 0.08) 100%)' 
          }}>
            <div className="welcome-content">
              <div className="welcome-text">
                <h2>Module 2: Colony Swarming Prediction</h2>
                <p>
                  Swarming is the natural reproduction mechanism where half of the worker colony leaves with the old queen to establish a new home.
                  This results in a <strong>sudden weight drop of 2 to 5 kg</strong> within 1-2 hours, accompanied by a <strong>rapid spike in CO2 &gt; 1500ppm</strong> and an elevated temperature deviation as bees engorge on honey and crowd prior to takeoff.
                </p>
              </div>
              <Zap size={48} color="var(--accent-crimson)" style={{ filter: 'drop-shadow(0 0 10px var(--accent-crimson-glow))' }} />
            </div>
          </div>
        </div>

        {/* QUICK STATS & WARNING FLAGS */}
        <div className="dashboard-grid">
          <div className="card highlight-crimson">
            <div className="stat-header">
              <span>Swarm Events Detected</span>
              <ShieldAlert size={16} color="var(--accent-crimson)" />
            </div>
            <div className="stat-value">
              {swarmEvents.length}
              <span className="stat-unit">across apiary</span>
            </div>
            <div className="stat-footer">
              <span>Trigger: Weight drop &lt; -0.5kg &amp; CO2 trend spike</span>
            </div>
          </div>

          <div className="card highlight-gold">
            <div className="stat-header">
              <span>CO2 Spikes Registered</span>
              <AlertCircle size={16} color="var(--accent-gold)" />
            </div>
            <div className="stat-value">
              {data.filter(d => parseFloat(String(d.co2)) > 1800).length}
              <span className="stat-unit">total logs</span>
            </div>
            <div className="stat-footer">
              <span>Critical threshold set at 1,800 ppm</span>
            </div>
          </div>

          <div className="card highlight-emerald">
            <div className="stat-header">
              <span>Current Risk Assessment</span>
              <Thermometer size={16} color="var(--accent-emerald)" />
            </div>
            <div className="stat-value" style={{ color: localSwarmEvents.length > 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)' }}>
              {localSwarmEvents.length > 0 ? 'CRITICAL ALERT' : 'SECURE'}
            </div>
            <div className="stat-footer">
              <span>Selected Unit: {selectedHive.toUpperCase()}</span>
            </div>
          </div>
        </div>

        {/* BUTTON ROW - View Model Comparison */}
        <div className="dashboard-grid">
          <div className="card" style={{ gridColumn: 'span 3', textAlign: 'center' }}>
            <button
              onClick={openModelComparison}
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                padding: '12px 24px',
                borderRadius: '8px',
                color: 'white',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '10px',
                fontSize: '14px',
                transition: 'transform 0.2s, box-shadow 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <BarChart2 size={18} />
              View Model Comparison Results (RF vs XGBoost)
            </button>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '8px' }}>
              Compare Random Forest and XGBoost models trained on this dataset
            </p>
          </div>
        </div>

        {/* MAIN CHART: CO2 Spike + Weight Drop Correlation */}
        <div className="dashboard-grid">
          <div className="card chart-card" style={{ gridColumn: 'span 2' }}>
            <div className="chart-header">
              <div className="chart-title">
                <h3>Swarm Alarm Event Correlation Chart</h3>
                <p>Sudden drop in weight coupled with a CO2 concentration surge for {selectedHive.toUpperCase()}</p>
              </div>
              <div className="chart-controls">
                <select
                  className="chart-select"
                  value={selectedHive}
                  onChange={(e) => setSelectedHive(e.target.value)}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: '8px',
                    background: 'var(--card-bg)',
                    border: '1px solid var(--card-border)',
                    color: 'var(--text-primary)'
                  }}
                >
                  {processed.hives.map(hive => (
                    <option key={hive} value={hive}>{hive.toUpperCase()}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="chart-container" style={{ height: '400px', width: '100%', marginTop: '1rem' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart 
                  data={chartData} 
                  margin={{ top: 20, right: 35, left: 45, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  
                  <XAxis 
                    dataKey="displayTime" 
                    stroke="var(--text-secondary)" 
                    tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                    angle={-25}
                    textAnchor="end"
                    height={60}
                    interval="preserveStartEnd"
                    minTickGap={50}
                  />
                  
                  <YAxis 
                    yAxisId="weight" 
                    orientation="left"
                    stroke="var(--accent-gold)" 
                    tick={{ fill: 'var(--accent-gold)', fontSize: 11 }}
                    label={{ 
                      value: 'Weight (kg)', 
                      angle: -90, 
                      position: 'insideLeft', 
                      fill: 'var(--accent-gold)',
                      style: { textAnchor: 'middle', fontSize: 12 },
                      offset: -30
                    }}
                    domain={[0, Math.ceil(maxWeight * 1.1)]}
                    tickCount={8}
                  />
                  
                  <YAxis 
                    yAxisId="co2" 
                    orientation="right"
                    stroke="var(--accent-emerald)" 
                    tick={{ fill: 'var(--accent-emerald)', fontSize: 11 }}
                    label={{ 
                      value: 'CO₂ Concentration (ppm)', 
                      angle: 90, 
                      position: 'insideRight', 
                      fill: 'var(--accent-emerald)',
                      style: { textAnchor: 'middle', fontSize: 12 },
                      offset: -25
                    }}
                    domain={[0, Math.ceil(maxCo2 * 1.1)]}
                    tickCount={8}
                  />
                  
                  <Tooltip
                    contentStyle={{ 
                      background: '#1e293b', 
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)'
                    }}
                    formatter={(value, name) => {
                      if (name === 'Hive Weight') return [`${Number(value).toFixed(1)} kg`, 'Weight'];
                      if (name === 'CO2 Concentration') return [`${Math.round(Number(value))} ppm`, 'CO₂'];
                      if (name === 'Swarm Event Takeoff') return [`${Number(value).toFixed(1)} kg`, '🐝 Swarm Takeoff'];
                      return [value, name];
                    }}
                  />
                  
                  <Legend 
                    wrapperStyle={{ paddingTop: '10px' }}
                    formatter={(value) => {
                      if (value === 'Hive Weight') return '🍯 Hive Weight';
                      if (value === 'CO2 Concentration') return '🌫️ CO₂ Concentration';
                      if (value === 'Swarm Event Takeoff') return '⚠️ Swarm Event Takeoff';
                      return value;
                    }}
                  />
                  
                  <Line 
                    yAxisId="weight" 
                    type="monotone" 
                    dataKey="weightVal" 
                    name="Hive Weight" 
                    stroke="var(--accent-gold)" 
                    strokeWidth={2.5} 
                    dot={false}
                    activeDot={{ r: 6, fill: 'var(--accent-gold)' }}
                  />
                  
                  <Line 
                    yAxisId="co2" 
                    type="monotone" 
                    dataKey="co2Val" 
                    name="CO2 Concentration" 
                    stroke="var(--accent-emerald)" 
                    strokeWidth={2} 
                    dot={false}
                    activeDot={{ r: 5, fill: 'var(--accent-emerald)' }}
                  />
                  
                  <Scatter 
                    yAxisId="weight" 
                    name="Swarm Event Takeoff" 
                    data={chartData.filter(d => d.swarmMarker !== null)} 
                    dataKey="swarmMarker" 
                    fill="#ef4444"
                    shape="circle"
                    legendType="circle"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            {/* Chart Legend Explanation */}
            <div style={{ 
              marginTop: '1rem', 
              padding: '0.75rem', 
              background: 'rgba(0,0,0,0.2)', 
              borderRadius: '6px',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              display: 'flex',
              gap: '1.5rem',
              flexWrap: 'wrap'
            }}>
              <span>🔴 <strong style={{ color: 'var(--accent-crimson)' }}>Red Dot:</strong> Detected swarm event (sudden weight drop + CO₂ spike)</span>
              <span>🟡 <strong style={{ color: 'var(--accent-gold)' }}>Gold Line:</strong> Hive weight trend (kg)</span>
              <span>🟢 <strong style={{ color: 'var(--accent-emerald)' }}>Green Line:</strong> CO₂ concentration (ppm)</span>
              <span>📊 <strong>Alert Thresholds:</strong> Weight drop &gt;0.5kg/hr + CO₂ &gt;1500ppm</span>
            </div>
          </div>

          {/* DETECTED ALERTS LIST */}
          <div className="card">
            <div className="chart-header">
              <div className="chart-title">
                <h3>Swarm Alarm Event Logs</h3>
                <p>Historical alarms captured during telemetry processing</p>
              </div>
              <ShieldAlert size={20} color="var(--accent-crimson)" />
            </div>

            <div className="table-container" style={{ maxHeight: '320px', overflowY: 'auto' }}>
              {swarmEvents.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-secondary)' }}>
                  <Info size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                  <p>No swarming events detected in the active dataset. Hive clusters appear stable.</p>
                </div>
              ) : (
                <table className="custom-table" style={{ fontSize: '0.825rem', width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
                      <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Hive</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Time</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Wt Drop</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>CO2 Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {swarmEvents.map((evt, idx) => (
                      <tr 
                        key={idx} 
                        style={{ cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)' }} 
                        onClick={() => setSelectedHive(evt.hive)}
                      >
                        <td style={{ fontWeight: 600, color: 'var(--accent-crimson)', padding: '0.5rem' }}>{evt.hive.toUpperCase()}</td>
                        <td style={{ padding: '0.5rem', fontSize: '0.75rem' }}>
                          {new Date(evt.timestamp).toLocaleDateString()} {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td style={{ color: 'var(--accent-crimson)', padding: '0.5rem' }}>{evt.weightChange} kg</td>
                        <td style={{ color: 'var(--accent-emerald)', padding: '0.5rem' }}>{evt.co2} ppm</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div style={{ marginTop: '1rem', borderTop: '1px solid var(--card-border)', paddingTop: '0.75rem' }}>
              <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Swarming Recommendations:</h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                ⚠️ Upon swarm notification, check trees near the apiary within 2 hours. Swarms cluster nearby before searching for permanent nest cavities. Keep a swarm retrieval trap box on standby.
              </p>
            </div>
          </div>
        </div>

        {/* SWARMING SIGNATURE ANALYSIS */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent-gold)' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
            Swarming Signatures - Pattern Analysis
          </h2>

          <div className="dashboard-grid" style={{ marginBottom: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)' }}>Weight Change Distribution (Normal Period)</h4>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Frequency of weight fluctuations under stable colony conditions</p>
              <div className="chart-container" style={{ height: '260px', marginTop: '0.5rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={swarmingPatterns?.weight_change?.normal || []} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="range" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                    <Legend />
                    <Bar dataKey="count" name="Normal Weight Change" fill="var(--accent-gold)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)' }}>CO2 Trend Distribution (Pre-Swarming Period)</h4>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Significant CO2 surges registered during swarming preparation</p>
              <div className="chart-container" style={{ height: '260px', marginTop: '0.5rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={swarmingPatterns?.co2_trend?.pre_swarming || []} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="range" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                    <Legend />
                    <Bar dataKey="count" name="Pre-Swarming CO2" fill="var(--accent-crimson)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
            Indicator Correlation Matrix
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Pearson correlation coefficients between swarming early warning telemetry indicators
          </p>

          {swarmingPatterns?.indicator_correlation ? (
            <div className="table-container" style={{ overflowX: 'auto' }}>
              <table className="custom-table" style={{ textAlign: 'center', width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--card-border)' }}>
                    <th style={{ textAlign: 'left', padding: '0.75rem' }}>Indicator</th>
                    <th style={{ padding: '0.75rem' }}>Weight Drop</th>
                    <th style={{ padding: '0.75rem' }}>CO2 Spike</th>
                    <th style={{ padding: '0.75rem' }}>Temp Spike</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(swarmingPatterns.indicator_correlation).map(([rowKey, colObj]) => (
                    <tr key={rowKey} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ fontWeight: 600, textAlign: 'left', padding: '0.5rem 0.75rem' }}>{rowKey}</td>
                      <td style={{ 
                        color: colObj["Weight Drop"] !== undefined && Math.abs(colObj["Weight Drop"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
                        padding: '0.5rem'
                      }}>
                        {colObj["Weight Drop"] !== undefined ? colObj["Weight Drop"].toFixed(2) : '—'}
                      </td>
                      <td style={{ 
                        color: colObj["CO2 Spike"] !== undefined && Math.abs(colObj["CO2 Spike"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
                        padding: '0.5rem'
                      }}>
                        {colObj["CO2 Spike"] !== undefined ? colObj["CO2 Spike"].toFixed(2) : '—'}
                      </td>
                      <td style={{ 
                        color: colObj["Temp Spike"] !== undefined && Math.abs(colObj["Temp Spike"]) > 0.5 ? 'var(--accent-crimson)' : 'var(--text-primary)',
                        padding: '0.5rem'
                      }}>
                        {colObj["Temp Spike"] !== undefined ? colObj["Temp Spike"].toFixed(2) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
              <Info size={16} />
              <span>Swarming signature pattern telemetry analysis is loading or not available in the current dataset.</span>
            </div>
          )}
        </div>
      </div>

      {/* Modal for Model Comparison */}
      {showComparison && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.95)',
          zIndex: 1000,
          overflowY: 'auto',
          padding: '2rem'
        }}>
          <div style={{
            position: 'relative',
            maxWidth: '1400px',
            margin: '0 auto'
          }}>
            <button
              onClick={closeModelComparison}
              style={{
                position: 'sticky',
                top: '1rem',
                float: 'right',
                background: 'rgba(255,255,255,0.1)',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 12px',
                cursor: 'pointer',
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                zIndex: 1001
              }}
            >
              <X size={18} />
              Close
            </button>
            <ModelComparisonPage onClose={closeModelComparison} />
          </div>
        </div>
      )}
    </>
  );
}