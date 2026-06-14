// import React, { useState, useEffect } from 'react';
// import {
//   BarChart,
//   Bar,
//   XAxis,
//   YAxis,
//   CartesianGrid,
//   Tooltip,
//   Legend,
//   ResponsiveContainer,
//   PieChart,
//   Pie,
//   Cell
// } from 'recharts';
// import { 
//   Download, Trophy, TrendingUp, AlertTriangle, 
//   RefreshCw, BarChart2, Activity, Cpu,
//   Maximize2, Minimize2, X
// } from 'lucide-react';

// export default function ModelComparisonPage({ onClose }) {
//   const [comparisonData, setComparisonData] = useState(null);
//   const [bestModel, setBestModel] = useState(null);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState(null);
//   const [expandedView, setExpandedView] = useState(false);
//   const [selectedMetric, setSelectedMetric] = useState('f1_score');

//   // Fetch model comparison data
//   const fetchModelComparison = async () => {
//     setLoading(true);
//     setError(null);
//     try {
//       const response = await fetch('http://localhost:5000/api/swarming/model-comparison');
//       if (!response.ok) throw new Error('Failed to fetch model comparison data');
//       const data = await response.json();
//       setComparisonData(data.models);
//       setBestModel({
//         best_model: data.best_model,
//         best_model_f1_score: data.best_model_f1_score
//       });
//     } catch (error) {
//       console.error('Failed to fetch model comparison:', error);
//       setError(error.message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchModelComparison();
//   }, []);

//   // Export function
//   const handleExport = () => {
//     if (!comparisonData) return;
//     const dataStr = JSON.stringify({ 
//       models: comparisonData, 
//       best_model: bestModel,
//       export_date: new Date().toISOString()
//     }, null, 2);
//     const blob = new Blob([dataStr], { type: 'application/json' });
//     const url = URL.createObjectURL(blob);
//     const a = document.createElement('a');
//     a.href = url;
//     a.download = `model_comparison_${new Date().toISOString().split('T')[0]}.json`;
//     a.click();
//     URL.revokeObjectURL(url);
//   };

//   // Prepare chart data
//   const chartData = comparisonData?.map(model => ({
//     model: model.model,
//     accuracy: model.accuracy * 100,
//     precision: model.precision * 100,
//     recall: model.recall * 100,
//     f1_score: model.f1_score * 100,
//     roc_auc: model.roc_auc * 100
//   })) || [];

//   // Prepare pie chart data for best model distribution
//   const pieData = comparisonData?.map(model => ({
//     name: model.model,
//     value: model.f1_score * 100,
//     isBest: model.model === bestModel?.best_model?.toUpperCase()
//   })) || [];

//   const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

//   // Metric selector options
//   const metrics = [
//     { key: 'f1_score', label: 'F1-Score', color: '#10b981' },
//     { key: 'accuracy', label: 'Accuracy', color: '#3b82f6' },
//     { key: 'precision', label: 'Precision', color: '#f59e0b' },
//     { key: 'recall', label: 'Recall', color: '#ef4444' },
//     { key: 'roc_auc', label: 'ROC-AUC', color: '#8b5cf6' }
//   ];

//   if (loading) {
//     return (
//       <div style={{ 
//         display: 'flex', 
//         justifyContent: 'center', 
//         alignItems: 'center', 
//         height: '100vh',
//         background: '#f8fafc'
//       }}>
//         <div style={{ textAlign: 'center' }}>
//           <RefreshCw size={48} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem', color: '#3b82f6' }} />
//           <p style={{ color: '#64748b' }}>Loading model comparison data...</p>
//         </div>
//       </div>
//     );
//   }

//   if (error) {
//     return (
//       <div style={{ 
//         display: 'flex', 
//         justifyContent: 'center', 
//         alignItems: 'center', 
//         height: '100vh',
//         background: '#f8fafc'
//       }}>
//         <div className="card" style={{ textAlign: 'center', maxWidth: '500px', background: 'white', borderRadius: '12px', padding: '2rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
//           <AlertTriangle size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
//           <h3 style={{ color: '#1e293b' }}>Error Loading Model Comparison</h3>
//           <p style={{ color: '#64748b', marginTop: '0.5rem' }}>{error}</p>
//           <button 
//             onClick={fetchModelComparison}
//             style={{
//               marginTop: '1rem',
//               padding: '8px 16px',
//               background: '#ef4444',
//               border: 'none',
//               borderRadius: '6px',
//               color: 'white',
//               cursor: 'pointer'
//             }}
//           >
//             Retry
//           </button>
//           <button 
//             onClick={onClose}
//             style={{
//               marginTop: '1rem',
//               marginLeft: '0.5rem',
//               padding: '8px 16px',
//               background: 'transparent',
//               border: '1px solid #e2e8f0',
//               borderRadius: '6px',
//               color: '#64748b',
//               cursor: 'pointer'
//             }}
//           >
//             Close
//           </button>
//         </div>
//       </div>
//     );
//   }

//   return (
//     <div style={{ 
//       padding: expandedView ? '1rem' : '2rem',
//       maxWidth: expandedView ? '100%' : '1400px',
//       margin: '0 auto',
//       width: '100%',
//       background: '#f8fafc',
//       minHeight: '100vh'
//     }}>
//       {/* Header with Close Button */}
//       <div style={{ 
//         display: 'flex', 
//         justifyContent: 'space-between', 
//         alignItems: 'center',
//         marginBottom: '2rem',
//         flexWrap: 'wrap',
//         gap: '1rem'
//       }}>
//         <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
//           <h1 style={{ margin: 0, fontSize: '1.75rem', color: '#1e293b' }}>
//             <BarChart2 size={28} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle', color: '#3b82f6' }} />
//             Model Comparison Results
//           </h1>
//         </div>
//         <div style={{ display: 'flex', gap: '0.75rem' }}>
//           <button
//             onClick={() => setExpandedView(!expandedView)}
//             style={{
//               display: 'flex',
//               alignItems: 'center',
//               gap: '0.5rem',
//               padding: '8px 16px',
//               background: 'white',
//               border: '1px solid #e2e8f0',
//               borderRadius: '8px',
//               color: '#475569',
//               cursor: 'pointer',
//               fontSize: '14px',
//               fontWeight: 500
//             }}
//           >
//             {expandedView ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
//             {expandedView ? 'Compact' : 'Fullscreen'}
//           </button>
//           <button onClick={fetchModelComparison} style={{
//             display: 'flex',
//             alignItems: 'center',
//             gap: '0.5rem',
//             padding: '8px 16px',
//             background: 'white',
//             border: '1px solid #e2e8f0',
//             borderRadius: '8px',
//             color: '#475569',
//             cursor: 'pointer',
//             fontSize: '14px',
//             fontWeight: 500
//           }}>
//             <RefreshCw size={16} />
//             Refresh
//           </button>
//           <button onClick={onClose} style={{
//             display: 'flex',
//             alignItems: 'center',
//             gap: '0.5rem',
//             padding: '8px 16px',
//             background: '#fee2e2',
//             border: '1px solid #fecaca',
//             borderRadius: '8px',
//             color: '#dc2626',
//             cursor: 'pointer',
//             fontSize: '14px',
//             fontWeight: 500
//           }}>
//             <X size={16} />
//             Close
//           </button>
//         </div>
//       </div>

//       {/* Best Model Banner */}
//       {bestModel && (
//         <div style={{
//           background: 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)',
//           border: '1px solid #fde047',
//           borderRadius: '16px',
//           padding: '1.5rem',
//           marginBottom: '2rem',
//           boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
//         }}>
//           <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
//             <div style={{
//               background: '#fef08a',
//               borderRadius: '50%',
//               padding: '1rem',
//               display: 'flex',
//               alignItems: 'center',
//               justifyContent: 'center'
//             }}>
//               <Trophy size={48} color="#ca8a04" />
//             </div>
//             <div>
//               <div style={{ fontSize: '0.85rem', color: '#854d0e', marginBottom: '0.25rem' }}>
//                 🏆 Best Performing Model 
//                 {/* (by F1-Score) */}
//               </div>
//               <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ca8a04', marginBottom: '0.25rem' }}>
//                 {bestModel.best_model?.toUpperCase()}
//               </div>
//               <div style={{ fontSize: '0.9rem', color: '#854d0e' }}>
//                 {/* Selected for deployment in production */}
//               </div>
//             </div>
//             <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
//               <div style={{ fontSize: '0.7rem', color: '#854d0e' }}>
//                 Last updated: {new Date().toLocaleString()}
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Metrics Summary Cards */}
//       <div style={{
//         display: 'grid',
//         gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
//         gap: '1.5rem',
//         marginBottom: '2rem'
//       }}>
//         {comparisonData?.map((model, idx) => (
//           <div key={idx} style={{
//             background: 'white',
//             borderRadius: '12px',
//             padding: '1.25rem',
//             boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
//             borderTop: `3px solid ${model.model === bestModel?.best_model?.toUpperCase() ? '#eab308' : '#e2e8f0'}`
//           }}>
//             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
//               <span style={{ fontWeight: 600, fontSize: '1.1rem', color: '#1e293b' }}>{model.model}</span>
//               {model.model === bestModel?.best_model?.toUpperCase() && (
//                 <span style={{ fontSize: '0.7rem', color: '#ca8a04' }}>🏆 BEST</span>
//               )}
//             </div>
//             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
//               <div>
//                 <div style={{ fontSize: '0.7rem', color: '#64748b' }}>F1-Score</div>
//                 <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#10b981' }}>
//                   {(model.f1_score * 100).toFixed(1)}%
//                 </div>
//               </div>
//               <div>
//                 <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Accuracy</div>
//                 <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#3b82f6' }}>
//                   {(model.accuracy * 100).toFixed(1)}%
//                 </div>
//               </div>
//               <div>
//                 <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Training Time</div>
//                 <div style={{ fontSize: '1rem', fontWeight: 500, color: '#475569' }}>
//                   {model.training_time_seconds?.toFixed(1)}s
//                 </div>
//               </div>
//               <div>
//                 <div style={{ fontSize: '0.7rem', color: '#64748b' }}>ROC-AUC</div>
//                 <div style={{ fontSize: '1rem', fontWeight: 500, color: '#475569' }}>
//                   {(model.roc_auc * 100).toFixed(1)}%
//                 </div>
//               </div>
//             </div>
//           </div>
//         ))}
//       </div>

//       {/* Metric Selector */}
//       <div style={{
//         background: 'white',
//         borderRadius: '12px',
//         padding: '1rem 1.5rem',
//         marginBottom: '2rem',
//         boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
//       }}>
//         <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
//           <span style={{ fontWeight: 600, color: '#1e293b' }}>Select Metric:</span>
//           <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
//             {metrics.map(metric => (
//               <button
//                 key={metric.key}
//                 onClick={() => setSelectedMetric(metric.key)}
//                 style={{
//                   padding: '6px 12px',
//                   background: selectedMetric === metric.key ? metric.color : '#f1f5f9',
//                   border: 'none',
//                   borderRadius: '6px',
//                   color: selectedMetric === metric.key ? 'white' : '#475569',
//                   cursor: 'pointer',
//                   fontSize: '0.85rem',
//                   transition: 'all 0.2s',
//                   fontWeight: selectedMetric === metric.key ? 500 : 400
//                 }}
//               >
//                 {metric.label}
//               </button>
//             ))}
//           </div>
//         </div>
//       </div>

//       {/* Main Comparison Chart */}
//       <div style={{
//         display: 'grid',
//         gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
//         gap: '1.5rem',
//         marginBottom: '2rem'
//       }}>
//         <div style={{
//           background: 'white',
//           borderRadius: '12px',
//           padding: '1.5rem',
//           boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
//           gridColumn: 'span 2'
//         }}>
//           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
//             <div>
//               <h3 style={{ margin: 0, color: '#1e293b' }}>Performance Comparison Chart</h3>
//               <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748b' }}>Model performance across key metrics</p>
//             </div>
//             <TrendingUp size={20} color="#10b981" />
//           </div>
//           <div style={{ height: '400px' }}>
//             <ResponsiveContainer width="100%" height="100%">
//               <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
//                 <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
//                 <XAxis dataKey="model" stroke="#64748b" />
//                 <YAxis stroke="#64748b" tickFormatter={(value) => `${value}%`} />
//                 <Tooltip
//                   contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px' }}
//                   formatter={(value) => [`${value.toFixed(2)}%`, '']}
//                 />
//                 <Legend />
//                 <Bar 
//                   dataKey={selectedMetric} 
//                   name={metrics.find(m => m.key === selectedMetric)?.label || selectedMetric}
//                   fill={metrics.find(m => m.key === selectedMetric)?.color || '#8884d8'}
//                   radius={[4, 4, 0, 0]}
//                 />
//               </BarChart>
//             </ResponsiveContainer>
//           </div>
//         </div>

//         {/* Pie Chart - Best Model Distribution */}
//         <div style={{
//           background: 'white',
//           borderRadius: '12px',
//           padding: '1.5rem',
//           boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
//         }}>
//           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
//             <div>
//               <h3 style={{ margin: 0, color: '#1e293b' }}>F1-Score Distribution</h3>
//               <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748b' }}>Model performance comparison</p>
//             </div>
//             <Activity size={20} color="#eab308" />
//           </div>
//           <div style={{ height: '300px' }}>
//             <ResponsiveContainer width="100%" height="100%">
//               <PieChart>
//                 <Pie
//                   data={pieData}
//                   cx="50%"
//                   cy="50%"
//                   labelLine={false}
//                   label={(entry) => `${entry.name}: ${entry.value.toFixed(1)}%`}
//                   outerRadius={80}
//                   fill="#8884d8"
//                   dataKey="value"
//                 >
//                   {pieData.map((entry, index) => (
//                     <Cell 
//                       key={`cell-${index}`} 
//                       fill={entry.isBest ? '#eab308' : COLORS[index % COLORS.length]}
//                       stroke={entry.isBest ? '#fef08a' : 'none'}
//                       strokeWidth={entry.isBest ? 2 : 0}
//                     />
//                   ))}
//                 </Pie>
//                 <Tooltip formatter={(value) => [`${value.toFixed(2)}%`, 'F1-Score']} />
//               </PieChart>
//             </ResponsiveContainer>
//           </div>
//         </div>
//       </div>

//       {/* Detailed Metrics Table */}
//       <div style={{
//         background: 'white',
//         borderRadius: '12px',
//         padding: '1.5rem',
//         boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
//         marginBottom: '2rem'
//       }}>
//         <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
//           <div>
//             <h3 style={{ margin: 0, color: '#1e293b' }}>Detailed Model Metrics</h3>
//             <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748b' }}>Complete performance breakdown for each model</p>
//           </div>
//           <Cpu size={20} color="#ef4444" />
//         </div>
//         <div style={{ overflowX: 'auto' }}>
//           <table style={{ width: '100%', borderCollapse: 'collapse' }}>
//             <thead>
//               <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
//                 <th style={{ textAlign: 'left', padding: '12px', color: '#475569', fontWeight: 600 }}>Model</th>
//                 <th style={{ textAlign: 'center', padding: '12px', color: '#475569', fontWeight: 600 }}>Accuracy</th>
//                 <th style={{ textAlign: 'center', padding: '12px', color: '#475569', fontWeight: 600 }}>Precision</th>
//                 <th style={{ textAlign: 'center', padding: '12px', color: '#475569', fontWeight: 600 }}>Recall</th>
//                 <th style={{ textAlign: 'center', padding: '12px', color: '#475569', fontWeight: 600 }}>F1-Score</th>
//                 <th style={{ textAlign: 'center', padding: '12px', color: '#475569', fontWeight: 600 }}>ROC-AUC</th>
//                 <th style={{ textAlign: 'center', padding: '12px', color: '#475569', fontWeight: 600 }}>Training Time</th>
//                </tr>
//             </thead>
//             <tbody>
//               {comparisonData?.map((model, idx) => (
//                 <tr 
//                   key={idx} 
//                   style={{
//                     background: model.model === bestModel?.best_model?.toUpperCase() 
//                       ? '#fefce8' : 'white',
//                     borderBottom: '1px solid #f1f5f9'
//                   }}
//                 >
//                   <td style={{ fontWeight: 600, padding: '12px', color: '#1e293b' }}>
//                     {model.model}
//                     {model.model === bestModel?.best_model?.toUpperCase() && (
//                       <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', color: '#ca8a04' }}>🏆</span>
//                     )}
//                    </td>
//                   <td style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>
//                     {(model.accuracy * 100).toFixed(2)}%
//                    </td>
//                   <td style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>
//                     {(model.precision * 100).toFixed(2)}%
//                    </td>
//                   <td style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>
//                     {(model.recall * 100).toFixed(2)}%
//                    </td>
//                   <td style={{ 
//                     textAlign: 'center', 
//                     fontWeight: 700,
//                     padding: '12px',
//                     color: model.f1_score === Math.max(...comparisonData.map(m => m.f1_score))
//                       ? '#ca8a04' : '#475569'
//                   }}>
//                     {(model.f1_score * 100).toFixed(2)}%
//                    </td>
//                   <td style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>
//                     {(model.roc_auc * 100).toFixed(2)}%
//                    </td>
//                   <td style={{ textAlign: 'center', padding: '12px', color: '#475569' }}>
//                     {model.training_time_seconds?.toFixed(1)}s
//                    </td>
//                  </tr>
//               ))}
//             </tbody>
//            </table>
//         </div>
//       </div>

//       {/* Info Note */}
//       <div style={{
//         background: '#f0fdf4',
//         borderRadius: '12px',
//         padding: '1.25rem',
//         border: '1px solid #bbf7d0'
//       }}>
//         <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
//           <AlertTriangle size={20} color="#eab308" style={{ flexShrink: 0, marginTop: '2px' }} />
//           <div>
//             <h4 style={{ marginBottom: '0.5rem', color: '#166534' }}>About Model Selection</h4>
//             <p style={{ fontSize: '0.85rem', color: '#166534', marginBottom: '0.5rem' }}>
//               <strong>F1-Score</strong> is the primary selection metric because swarming events are rare (class imbalance). 
//               A high F1-Score indicates good balance between:
//             </p>
//             <ul style={{ fontSize: '0.8rem', color: '#166534', marginLeft: '1rem' }}>
//               <li><strong>Precision</strong> - Not raising false alarms (minimizing unnecessary interventions)</li>
//               <li><strong>Recall</strong> - Catching actual swarming events (preventing colony loss)</li>
//             </ul>
//             <p style={{ fontSize: '0.8rem', color: '#166534', marginTop: '0.5rem' }}>
//               The best model is automatically selected and deployed for real-time predictions in the dashboard.
//             </p>
//           </div>
//         </div>
//       </div>

//       <style>{`
//         @keyframes spin {
//           from { transform: rotate(0deg); }
//           to { transform: rotate(360deg); }
//         }
//       `}</style>
//     </div>
//   );
// }


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
  Cell
} from 'recharts';
import { 
  Download, Trophy, TrendingUp, AlertTriangle, 
  RefreshCw, BarChart2, Activity, Cpu,
  Maximize2, Minimize2, X
} from 'lucide-react';

export default function ModelComparisonPage({ onClose }) {
  const [comparisonData, setComparisonData] = useState(null);
  const [bestModel, setBestModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedView, setExpandedView] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState('f1_score');

  // Fetch model comparison data
  const fetchModelComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:5000/api/swarming/model-comparison');
      if (!response.ok) throw new Error('Failed to fetch model comparison data');
      const data = await response.json();
      
      // Filter out LSTM - only keep Random Forest and XGBoost
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

  // Export function
  const handleExport = () => {
    if (!comparisonData) return;
    const dataStr = JSON.stringify({ 
      models: comparisonData, 
      best_model: bestModel,
      export_date: new Date().toISOString()
    }, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `model_comparison_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Prepare chart data
  const chartData = comparisonData?.map(model => ({
    model: model.model,
    accuracy: model.accuracy * 100,
    precision: model.precision * 100,
    recall: model.recall * 100,
    f1_score: model.f1_score * 100,
    roc_auc: model.roc_auc * 100
  })) || [];

  // Prepare pie chart data
  const pieData = comparisonData?.map(model => ({
    name: model.model,
    value: model.f1_score * 100,
    isBest: model.model === bestModel?.best_model
  })) || [];

  const COLORS = ['#3b82f6', '#10b981'];

  // Metric selector options
  const metrics = [
    { key: 'f1_score', label: 'F1-Score', color: '#10b981' },
    { key: 'accuracy', label: 'Accuracy', color: '#3b82f6' },
    { key: 'precision', label: 'Precision', color: '#f59e0b' },
    { key: 'recall', label: 'Recall', color: '#ef4444' },
    { key: 'roc_auc', label: 'ROC-AUC', color: '#8b5cf6' }
  ];

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: '#f8fafc'
      }}>
        <div style={{ textAlign: 'center' }}>
          <RefreshCw size={48} style={{ animation: 'spin 1s linear infinite', marginBottom: '1rem', color: '#3b82f6' }} />
          <p style={{ color: '#64748b' }}>Loading model comparison data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: '#f8fafc'
      }}>
        <div className="card" style={{ textAlign: 'center', maxWidth: '500px', background: 'white', borderRadius: '12px', padding: '2rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <AlertTriangle size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
          <h3 style={{ color: '#1e293b' }}>Error Loading Model Comparison</h3>
          <p style={{ color: '#64748b', marginTop: '0.5rem' }}>{error}</p>
          <button 
            onClick={fetchModelComparison}
            style={{
              marginTop: '1rem',
              padding: '8px 16px',
              background: '#ef4444',
              border: 'none',
              borderRadius: '6px',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
          <button 
            onClick={onClose}
            style={{
              marginTop: '1rem',
              marginLeft: '0.5rem',
              padding: '8px 16px',
              background: 'transparent',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              color: '#64748b',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ 
      padding: expandedView ? '1rem' : '2rem',
      maxWidth: expandedView ? '100%' : '1400px',
      margin: '0 auto',
      width: '100%',
      background: '#f8fafc',
      minHeight: '100vh'
    }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '2rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h1 style={{ margin: 0, fontSize: '1.75rem', color: '#1e293b' }}>
            <BarChart2 size={28} style={{ display: 'inline', marginRight: '0.5rem', verticalAlign: 'middle', color: '#3b82f6' }} />
            Model Comparison: RF vs XGBoost
          </h1>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={() => setExpandedView(!expandedView)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '8px 16px',
              background: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              color: '#475569',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 500
            }}
          >
            {expandedView ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            {expandedView ? 'Compact' : 'Fullscreen'}
          </button>
          <button onClick={handleExport} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '8px 16px',
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            color: '#475569',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 500
          }}>
            <Download size={16} />
            Export Results
          </button>
          <button onClick={fetchModelComparison} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '8px 16px',
            background: 'white',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            color: '#475569',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 500
          }}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button onClick={onClose} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '8px 16px',
            background: '#fee2e2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            color: '#dc2626',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 500
          }}>
            <X size={16} />
            Close
          </button>
        </div>
      </div>

      {/* Best Model Banner */}
      {bestModel && comparisonData && (
        <div style={{
          background: 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)',
          border: '1px solid #fde047',
          borderRadius: '16px',
          padding: '1.5rem',
          marginBottom: '2rem',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
            <div style={{
              background: '#fef08a',
              borderRadius: '50%',
              padding: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Trophy size={48} color="#ca8a04" />
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', color: '#854d0e', marginBottom: '0.25rem' }}>
                Best Performing Model
              </div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#ca8a04', marginBottom: '0.25rem' }}>
                {bestModel.best_model?.toUpperCase()}
              </div>
              {/* <div style={{ fontSize: '0.9rem', color: '#854d0e' }}>
                F1-Score: {(bestModel.best_model_f1_score * 100).toFixed(2)}% • Selected for Production
              </div> */}
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <div style={{ fontSize: '0.7rem', color: '#854d0e' }}>
                Last updated: {new Date().toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Metrics Summary Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        {comparisonData?.map((model, idx) => (
          <div key={idx} style={{
            background: 'white',
            borderRadius: '12px',
            padding: '1.5rem',
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            borderTop: `4px solid ${model.model === bestModel?.best_model ? '#eab308' : '#e2e8f0'}`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <span style={{ fontWeight: 700, fontSize: '1.25rem', color: '#1e293b' }}>{model.model}</span>
              {model.model === bestModel?.best_model && (
                <span style={{ fontSize: '0.7rem', padding: '2px 8px', background: '#fef08a', borderRadius: '20px', color: '#854d0e' }}>🏆 BEST</span>
              )}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>F1-Score</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#10b981' }}>
                  {(model.f1_score * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Accuracy</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 700, color: '#3b82f6' }}>
                  {(model.accuracy * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Precision</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f59e0b' }}>
                  {(model.precision * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Recall</div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: '#ef4444' }}>
                  {(model.recall * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>ROC-AUC</div>
                <div style={{ fontSize: '1rem', fontWeight: 500, color: '#8b5cf6' }}>
                  {(model.roc_auc * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Training Time</div>
                <div style={{ fontSize: '1rem', fontWeight: 500, color: '#475569' }}>
                  {(model.training_time_seconds / 60).toFixed(1)} min
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Metric Selector */}
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '1rem 1.5rem',
        marginBottom: '2rem',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 600, color: '#1e293b' }}>Select Metric to Compare:</span>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {metrics.map(metric => (
              <button
                key={metric.key}
                onClick={() => setSelectedMetric(metric.key)}
                style={{
                  padding: '6px 16px',
                  background: selectedMetric === metric.key ? metric.color : '#f1f5f9',
                  border: 'none',
                  borderRadius: '20px',
                  color: selectedMetric === metric.key ? 'white' : '#475569',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  transition: 'all 0.2s',
                  fontWeight: selectedMetric === metric.key ? 500 : 400
                }}
              >
                {metric.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Comparison Chart */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '1.5rem',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h3 style={{ margin: 0, color: '#1e293b' }}>Performance Comparison Chart</h3>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748b' }}>
                Comparing {metrics.find(m => m.key === selectedMetric)?.label}
              </p>
            </div>
            <TrendingUp size={20} color="#10b981" />
          </div>
          <div style={{ height: '400px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="model" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" tickFormatter={(value) => `${value}%`} />
                <Tooltip
                  contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px' }}
                  formatter={(value) => [`${value.toFixed(2)}%`, metrics.find(m => m.key === selectedMetric)?.label]}
                />
                <Legend />
                <Bar 
                  dataKey={selectedMetric} 
                  name={metrics.find(m => m.key === selectedMetric)?.label || selectedMetric}
                  fill={metrics.find(m => m.key === selectedMetric)?.color || '#8884d8'}
                  radius={[8, 8, 0, 0]}
                  label={{ position: 'top', formatter: (value) => `${value.toFixed(1)}%` }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* F1-Score Comparison Pie Chart */}
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '1.5rem',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <h3 style={{ margin: 0, color: '#1e293b' }}>F1-Score Distribution</h3>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748b' }}>Weighted performance comparison</p>
            </div>
            <Activity size={20} color="#eab308" />
          </div>
          <div style={{ height: '350px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  label={(entry) => `${entry.name}: ${entry.value.toFixed(1)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.isBest ? '#eab308' : COLORS[index % COLORS.length]}
                      stroke="white"
                      strokeWidth={2}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`${value.toFixed(2)}%`, 'F1-Score']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Detailed Metrics Table */}
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '1.5rem',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        marginBottom: '2rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, color: '#1e293b' }}>Detailed Model Metrics</h3>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#64748b' }}>Complete performance breakdown: Random Forest vs XGBoost</p>
          </div>
          <Cpu size={20} color="#ef4444" />
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                <th style={{ textAlign: 'left', padding: '14px', color: '#475569', fontWeight: 600 }}>Model</th>
                <th style={{ textAlign: 'center', padding: '14px', color: '#475569', fontWeight: 600 }}>Accuracy</th>
                <th style={{ textAlign: 'center', padding: '14px', color: '#475569', fontWeight: 600 }}>Precision</th>
                <th style={{ textAlign: 'center', padding: '14px', color: '#475569', fontWeight: 600 }}>Recall</th>
                <th style={{ textAlign: 'center', padding: '14px', color: '#475569', fontWeight: 600 }}>F1-Score</th>
                <th style={{ textAlign: 'center', padding: '14px', color: '#475569', fontWeight: 600 }}>ROC-AUC</th>
                <th style={{ textAlign: 'center', padding: '14px', color: '#475569', fontWeight: 600 }}>Training Time</th>
                </tr>
            </thead>
            <tbody>
              {comparisonData?.map((model, idx) => (
                <tr 
                  key={idx} 
                  style={{
                    background: model.model === bestModel?.best_model 
                      ? '#fefce8' : 'white',
                    borderBottom: '1px solid #f1f5f9'
                  }}
                >
                  <td style={{ fontWeight: 700, padding: '14px', color: '#1e293b', fontSize: '1rem' }}>
                    {model.model}
                    {model.model === bestModel?.best_model && (
                      <span style={{ marginLeft: '0.5rem', fontSize: '0.7rem', padding: '2px 8px', background: '#fef08a', borderRadius: '20px', color: '#854d0e' }}>🏆 BEST</span>
                    )}
                   </td>
                  <td style={{ textAlign: 'center', padding: '14px', fontWeight: 600, color: '#3b82f6', fontSize: '1.1rem' }}>
                    {(model.accuracy * 100).toFixed(2)}%
                   </td>
                  <td style={{ textAlign: 'center', padding: '14px', fontWeight: 600, color: '#f59e0b', fontSize: '1.1rem' }}>
                    {(model.precision * 100).toFixed(2)}%
                   </td>
                  <td style={{ textAlign: 'center', padding: '14px', fontWeight: 600, color: '#ef4444', fontSize: '1.1rem' }}>
                    {(model.recall * 100).toFixed(2)}%
                   </td>
                  <td style={{ 
                    textAlign: 'center', 
                    fontWeight: 800,
                    padding: '14px',
                    fontSize: '1.1rem',
                    color: model.f1_score === Math.max(...comparisonData.map(m => m.f1_score))
                      ? '#ca8a04' : '#475569'
                  }}>
                    {(model.f1_score * 100).toFixed(2)}%
                   </td>
                  <td style={{ textAlign: 'center', padding: '14px', fontWeight: 600, color: '#8b5cf6', fontSize: '1.1rem' }}>
                    {(model.roc_auc * 100).toFixed(2)}%
                   </td>
                  <td style={{ textAlign: 'center', padding: '14px', color: '#475569' }}>
                    {(model.training_time_seconds / 60).toFixed(1)} min
                   </td>
                 </tr>
              ))}
            </tbody>
           </table>
        </div>
      </div>

      {/* Winner Summary */}
      {bestModel && comparisonData && (
        <div style={{
          background: 'linear-gradient(135deg, #dbeafe 0%, #eff6ff 100%)',
          borderRadius: '12px',
          padding: '1.5rem',
          marginBottom: '2rem',
          border: '1px solid #bfdbfe'
        }}>
          {/* <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <Trophy size={32} color="#ca8a04" />
            <div>
              <h4 style={{ margin: 0, color: '#1e40af' }}>🏆 Winner: {bestModel.best_model}</h4>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#1e40af' }}>
                {bestModel.best_model === 'Random Forest' 
                  ? 'Random Forest achieves 96.35% F1-Score, outperforming XGBoost by 2.74% with faster training time (10.6 min vs 19.3 min)'
                  : 'Selected based on highest F1-Score performance'
                }
              </p>
            </div>
          </div> */}
        </div>
      )}

      {/* Info Note */}
      <div style={{
        background: '#f0fdf4',
        borderRadius: '12px',
        padding: '1.25rem',
        border: '1px solid #bbf7d0'
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
          <AlertTriangle size={20} color="#eab308" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h4 style={{ marginBottom: '0.5rem', color: '#166534' }}>About Model Selection</h4>
            <p style={{ fontSize: '0.85rem', color: '#166534', marginBottom: '0.5rem' }}>
              <strong>F1-Score</strong> is the primary selection metric because swarming events are rare (class imbalance). 
              A high F1-Score indicates good balance between:
            </p>
            <ul style={{ fontSize: '0.8rem', color: '#166534', marginLeft: '1rem' }}>
              <li><strong>Precision (93.54% for RF)</strong> - Not raising false alarms (minimizing unnecessary interventions)</li>
              <li><strong>Recall (99.35% for RF)</strong> - Catching actual swarming events (preventing colony loss)</li>
            </ul>
            <p style={{ fontSize: '0.8rem', color: '#166534', marginTop: '0.5rem' }}>
              {/* <strong>Random Forest</strong> is automatically selected and deployed for real-time predictions in the dashboard. */}
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}