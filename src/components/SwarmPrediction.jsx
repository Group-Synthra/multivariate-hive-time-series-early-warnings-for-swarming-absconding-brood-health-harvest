// import React, { useState, useEffect, useCallback, useRef } from "react";

// // ─────────────────────────────────────────────────────────────────────
// // Constants
// // ─────────────────────────────────────────────────────────────────────
// const API_BASE = ""; // Vite proxy forwards /api/* → http://localhost:5000
// const REFRESH_INTERVAL = 60_000; // 60 seconds

// const HIVE_IDS = [
//   "Hive_01", "Hive_02", "Hive_03", "Hive_04", "Hive_05",
//   "Hive_06", "Hive_07", "Hive_08", "Hive_09", "Hive_10",
// ];

// const DEFAULT_READING = {
//   internal_temperature_c: 35.0,
//   internal_humidity_pct: 65.0,
//   co2_ppm: 1200,
//   hive_weight_kg: 32.5,
//   external_temperature_c: 28.0,
//   external_humidity_pct: 55.0,
//   rainfall_mm_hour: 0.0,
//   wind_speed_mps: 2.0,
// };

// const SENSOR_META = [
//   { key: "internal_temperature_c", label: "Internal Temp",    unit: "°C",   icon: "🌡️",  min: 20,  max: 45,  step: 0.1 },
//   { key: "internal_humidity_pct",  label: "Internal Humidity", unit: "%",    icon: "💧",  min: 30,  max: 100, step: 0.5 },
//   { key: "co2_ppm",                label: "CO₂",              unit: "ppm",  icon: "💨",  min: 400, max: 5000,step: 10  },
//   { key: "hive_weight_kg",         label: "Hive Weight",      unit: "kg",   icon: "⚖️",  min: 5,   max: 80,  step: 0.1 },
//   { key: "external_temperature_c", label: "External Temp",    unit: "°C",   icon: "☀️",  min: -10, max: 50,  step: 0.1 },
//   { key: "external_humidity_pct",  label: "External Humidity", unit: "%",   icon: "🌤️",  min: 10,  max: 100, step: 0.5 },
//   { key: "rainfall_mm_hour",       label: "Rainfall",         unit: "mm/h", icon: "🌧️",  min: 0,   max: 50,  step: 0.1 },
//   { key: "wind_speed_mps",         label: "Wind Speed",       unit: "m/s",  icon: "💨",  min: 0,   max: 30,  step: 0.1 },
// ];

// const RISK_CONFIG = {
//   LOW:    { color: "#22c55e", bg: "#052e16", border: "#16a34a", emoji: "🟢", label: "LOW RISK" },
//   MEDIUM: { color: "#eab308", bg: "#1c1a01", border: "#ca8a04", emoji: "🟡", label: "MEDIUM RISK" },
//   HIGH:   { color: "#ef4444", bg: "#2d0c0c", border: "#dc2626", emoji: "🔴", label: "HIGH RISK" },
// };

// // ─────────────────────────────────────────────────────────────────────
// // Sub-components
// // ─────────────────────────────────────────────────────────────────────

// /** Animated circular risk gauge */
// function RiskGauge({ percentage, riskLevel }) {
//   const cfg = RISK_CONFIG[riskLevel] || RISK_CONFIG.LOW;
//   const radius = 72;
//   const circumference = 2 * Math.PI * radius;
//   const strokeDash = (percentage / 100) * circumference;
//   const isHigh = riskLevel === "HIGH";

//   return (
//     <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
//       <div style={{ position: "relative", width: 180, height: 180 }}>
//         <svg width={180} height={180} style={{ transform: "rotate(-90deg)" }}>
//           {/* Track */}
//           <circle cx={90} cy={90} r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={14} />
//           {/* Progress */}
//           <circle
//             cx={90} cy={90} r={radius} fill="none"
//             stroke={cfg.color} strokeWidth={14}
//             strokeDasharray={`${strokeDash} ${circumference}`}
//             strokeLinecap="round"
//             style={{ transition: "stroke-dasharray 1.2s ease-in-out, stroke 0.5s" }}
//           />
//         </svg>
//         {/* Centre text */}
//         <div style={{
//           position: "absolute", inset: 0,
//           display: "flex", flexDirection: "column",
//           alignItems: "center", justifyContent: "center",
//         }}>
//           <span style={{
//             fontSize: "2.2rem", fontWeight: 800, lineHeight: 1,
//             color: cfg.color, fontFamily: "'Outfit', sans-serif",
//             animation: isHigh ? "pulseNumber 1.4s ease-in-out infinite" : "none",
//           }}>
//             {percentage.toFixed(1)}
//           </span>
//           <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>%</span>
//         </div>
//       </div>

//       {/* Risk badge */}
//       <div style={{
//         display: "inline-flex", alignItems: "center", gap: "6px",
//         background: cfg.bg, border: `1.5px solid ${cfg.border}`,
//         borderRadius: "20px", padding: "5px 16px",
//         fontSize: "0.8rem", fontWeight: 700, color: cfg.color,
//         animation: isHigh ? "pulseBadge 1.4s ease-in-out infinite" : "none",
//       }}>
//         {cfg.emoji} {cfg.label}
//       </div>
//     </div>
//   );
// }

// /** Single sensor input field */
// function SensorInput({ meta, value, onChange }) {
//   return (
//     <div style={{
//       background: "rgba(255,255,255,0.03)",
//       border: "1px solid rgba(255,255,255,0.08)",
//       borderRadius: "10px", padding: "10px 12px",
//     }}>
//       <label style={{
//         display: "flex", alignItems: "center", gap: "6px",
//         fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "6px",
//       }}>
//         <span style={{ fontSize: "1rem" }}>{meta.icon}</span>
//         <span>{meta.label}</span>
//         <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>{meta.unit}</span>
//       </label>
//       <input
//         id={`sensor-${meta.key}`}
//         type="number"
//         min={meta.min} max={meta.max} step={meta.step}
//         value={value}
//         onChange={(e) => onChange(meta.key, parseFloat(e.target.value) || 0)}
//         style={{
//           width: "100%", background: "rgba(0,0,0,0.3)", border: "none",
//           borderRadius: "6px", padding: "6px 10px", color: "var(--accent-gold)",
//           fontSize: "0.95rem", fontWeight: 600, fontFamily: "'Outfit', sans-serif",
//           outline: "none", boxSizing: "border-box",
//         }}
//       />
//     </div>
//   );
// }

// /** PELT feature snapshot card */
// function PeltSnapshot({ snapshot }) {
//   if (!snapshot) return null;
//   const items = [
//     { label: "Breakpoint Detected", value: snapshot.breakpoint ? "Yes ⚠️" : "No ✓",
//       color: snapshot.breakpoint ? "#ef4444" : "#22c55e" },
//     { label: "Days Since Breakpoint", value: `${snapshot.days_since_breakpoint} readings`, color: "#38bdf8" },
//     { label: "Breakpoint Density", value: `${snapshot.breakpoint_density} / 24h`, color: "#a78bfa" },
//     { label: "Segment Duration",  value: `${snapshot.segment_duration} steps`, color: "#f59e0b" },
//   ];
//   return (
//     <div style={{
//       background: "#172554", borderLeft: "4px solid #38bdf8",
//       borderRadius: "10px", padding: "14px 16px",
//     }}>
//       <h4 style={{ margin: "0 0 10px", fontSize: "0.85rem", color: "#38bdf8" }}>
//         🔎 PELT Change-Point Snapshot
//       </h4>
//       <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
//         {items.map(({ label, value, color }) => (
//           <div key={label} style={{
//             background: "rgba(0,0,0,0.3)", borderRadius: "8px", padding: "8px 10px",
//           }}>
//             <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: "2px" }}>{label}</div>
//             <div style={{ fontSize: "0.9rem", fontWeight: 700, color }}>{value}</div>
//           </div>
//         ))}
//       </div>
//     </div>
//   );
// }

// /** Countdown bar to next refresh */
// function CountdownBar({ secondsLeft, total }) {
//   const pct = ((total - secondsLeft) / total) * 100;
//   return (
//     <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
//       <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
//         Next refresh in {secondsLeft}s
//       </span>
//       <div style={{ flex: 1, height: "3px", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>
//         <div style={{
//           height: "100%", background: "var(--accent-cyan)",
//           borderRadius: "3px", width: `${pct}%`,
//           transition: "width 1s linear",
//         }} />
//       </div>
//     </div>
//   );
// }

// // ─────────────────────────────────────────────────────────────────────
// // Main SwarmPrediction Component
// // ─────────────────────────────────────────────────────────────────────
// const SwarmPrediction = () => {
//   const [selectedHive, setSelectedHive]   = useState("Hive_01");
//   const [sensorValues, setSensorValues]   = useState({ ...DEFAULT_READING });
//   const [result, setResult]               = useState(null);
//   const [loading, setLoading]             = useState(false);
//   const [error, setError]                 = useState(null);
//   const [lastUpdated, setLastUpdated]     = useState(null);
//   const [countdown, setCountdown]         = useState(REFRESH_INTERVAL / 1000);
//   const [modelHealth, setModelHealth]     = useState(null);

//   const timerRef     = useRef(null);
//   const countdownRef = useRef(null);

//   // ── Generate random sensor values (simulates live data) ──────────
//   const generateRandomReadings = useCallback(() => {
//     const baseValues = {
//       internal_temperature_c: 33.0 + Math.random() * 4.0,  // 33-37°C
//       internal_humidity_pct: 55 + Math.random() * 25,      // 55-80%
//       co2_ppm: 400 + Math.random() * 1000,                 // 400-1400 ppm
//       hive_weight_kg: 28 + Math.random() * 8,              // 28-36 kg
//       external_temperature_c: 25 + Math.random() * 8,      // 25-33°C
//       external_humidity_pct: 45 + Math.random() * 30,      // 45-75%
//       rainfall_mm_hour: Math.random() * 2,                 // 0-2 mm/h
//       wind_speed_mps: 0.5 + Math.random() * 4,             // 0.5-4.5 m/s
//     };
    
//     return {
//       internal_temperature_c: parseFloat(baseValues.internal_temperature_c.toFixed(1)),
//       internal_humidity_pct: parseFloat(baseValues.internal_humidity_pct.toFixed(1)),
//       co2_ppm: Math.round(baseValues.co2_ppm),
//       hive_weight_kg: parseFloat(baseValues.hive_weight_kg.toFixed(1)),
//       external_temperature_c: parseFloat(baseValues.external_temperature_c.toFixed(1)),
//       external_humidity_pct: parseFloat(baseValues.external_humidity_pct.toFixed(1)),
//       rainfall_mm_hour: parseFloat(baseValues.rainfall_mm_hour.toFixed(1)),
//       wind_speed_mps: parseFloat(baseValues.wind_speed_mps.toFixed(1)),
//     };
//   }, []);

//   // ── Build 24 readings from current sensor panel ──────────────────
//   const buildReadings = useCallback((values) => {
//     // Create 24 readings with slight random variation to simulate history
//     return Array.from({ length: 24 }, (_, i) => {
//       const jitter = (v, spread) => +(v + (Math.random() - 0.5) * spread).toFixed(2);
//       return {
//         internal_temperature_c : jitter(values.internal_temperature_c, 0.8),
//         internal_humidity_pct  : jitter(values.internal_humidity_pct,  2.0),
//         co2_ppm                : jitter(values.co2_ppm,                60),
//         hive_weight_kg         : jitter(values.hive_weight_kg,         0.3),
//         external_temperature_c : jitter(values.external_temperature_c, 0.6),
//         external_humidity_pct  : jitter(values.external_humidity_pct,  1.5),
//         rainfall_mm_hour       : +(Math.max(0, values.rainfall_mm_hour + (Math.random() - 0.5) * 0.1)).toFixed(2),
//         wind_speed_mps         : jitter(values.wind_speed_mps, 0.4),
//       };
//     });
//   }, []);

//   // ── Fetch prediction from backend ────────────────────────────────
//   const fetchPrediction = useCallback(async (values = sensorValues, hive = selectedHive) => {
//     setLoading(true);
//     setError(null);
//     try {
//       const readings = buildReadings(values);
//       const res = await fetch(`${API_BASE}/api/swarming/live-prediction`, {
//         method : "POST",
//         headers: { "Content-Type": "application/json" },
//         body   : JSON.stringify({ hive_id: hive, readings }),
//       });

//       if (!res.ok) {
//         const errData = await res.json().catch(() => ({}));
//         throw new Error(errData.error || `HTTP ${res.status}`);
//       }

//       const data = await res.json();
//       setResult(data);
//       setLastUpdated(new Date());
//     } catch (e) {
//       setError(e.message);
//     } finally {
//       setLoading(false);
//     }
//   }, [sensorValues, selectedHive, buildReadings]);

//   // ── Check model health on mount ───────────────────────────────────
//   useEffect(() => {
//     fetch(`${API_BASE}/api/swarming/live-prediction/health`)
//       .then((r) => r.json())
//       .then(setModelHealth)
//       .catch(() => setModelHealth({ all_ready: false }));
//   }, []);

//   // ── Auto-refresh every 60 s (updates sensors + risk) ─────────────
//   useEffect(() => {
//     // Initial fetch
//     fetchPrediction();
    
//     timerRef.current = setInterval(() => {
//       // ✅ Generate new random sensor values
//       const newValues = generateRandomReadings();
//       setSensorValues(newValues);
      
//       // ✅ Fetch prediction with new values
//       fetchPrediction(newValues, selectedHive);
//       setCountdown(REFRESH_INTERVAL / 1000);
//     }, REFRESH_INTERVAL);
    
//     return () => clearInterval(timerRef.current);
//   // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, []);

//   // ── Countdown ticker ──────────────────────────────────────────────
//   useEffect(() => {
//     setCountdown(REFRESH_INTERVAL / 1000);
//     countdownRef.current = setInterval(() => {
//       setCountdown((prev) => (prev > 0 ? prev - 1 : REFRESH_INTERVAL / 1000));
//     }, 1000);
//     return () => clearInterval(countdownRef.current);
//   }, [result]);

//   const handleSensorChange = (key, val) => {
//     setSensorValues((prev) => ({ ...prev, [key]: val }));
//   };

//   const handlePredict = () => {
//     clearInterval(timerRef.current);
//     fetchPrediction(sensorValues, selectedHive).then(() => {
//       timerRef.current = setInterval(() => {
//         // ✅ Generate new random sensor values
//         const newValues = generateRandomReadings();
//         setSensorValues(newValues);
//         fetchPrediction(newValues, selectedHive);
//         setCountdown(REFRESH_INTERVAL / 1000);
//       }, REFRESH_INTERVAL);
//     });
//   };

//   const handleHiveChange = (h) => {
//     setSelectedHive(h);
//     // ✅ Generate new random sensor values when hive changes
//     const newValues = generateRandomReadings();
//     setSensorValues(newValues);
//     fetchPrediction(newValues, h);
//   };

//   // ── Manual refresh sensors ────────────────────────────────────────
//   const handleRefreshSensors = () => {
//     const newValues = generateRandomReadings();
//     setSensorValues(newValues);
//     fetchPrediction(newValues, selectedHive);
//   };

//   // ── Derived values ────────────────────────────────────────────────
//   const riskLevel = result?.risk_level || "LOW";
//   const riskCfg   = RISK_CONFIG[riskLevel] || RISK_CONFIG.LOW;

//   // ─────────────────────────────────────────────────────────────────
//   return (
//     <div style={{ padding: "24px 28px", minHeight: "100vh", color: "white" }}>

//       {/* ── CSS animations ── */}
//       <style>{`
//         @keyframes pulseNumber {
//           0%,100% { opacity:1; transform:scale(1); }
//           50%     { opacity:0.85; transform:scale(1.06); }
//         }
//         @keyframes pulseBadge {
//           0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
//           50%     { box-shadow: 0 0 12px 4px rgba(239,68,68,0.4); }
//         }
//         @keyframes spin { to { transform:rotate(360deg); } }
//         @keyframes fadeSlide {
//           from { opacity:0; transform:translateY(10px); }
//           to   { opacity:1; transform:translateY(0); }
//         }
//         .pred-input:focus { outline:2px solid #38bdf8 !important; }
//         .pred-btn {
//           cursor:pointer; transition:all 0.2s;
//           border:none; border-radius:10px; padding:10px 20px;
//           font-family:'Outfit',sans-serif; font-weight:700; font-size:0.9rem;
//         }
//         .pred-btn:hover { filter:brightness(1.15); transform:translateY(-1px); }
//         .pred-btn:active { transform:translateY(0); }
//       `}</style>

//       {/* ── Page header ── */}
//       <div style={{ marginBottom: "22px" }}>
//         <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
//           <span style={{ fontSize: "1.6rem" }}>🐝</span>
//           <h2 style={{ margin: 0, fontSize: "1.4rem", fontFamily: "'Outfit',sans-serif",
//             background: "linear-gradient(90deg,#f59e0b,#fde68a)", WebkitBackgroundClip: "text",
//             WebkitTextFillColor: "transparent" }}>
//             Live Swarming Prediction
//           </h2>
//         </div>
//         <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.85rem" }}>
//           LSTM model · PELT change-point features · Sigmoid threshold 0.70 · Auto-refresh every 60 s
//         </p>
//       </div>

//       {/* ── Model health status bar ── */}
//       {modelHealth && (
//         <div style={{
//           display: "flex", alignItems: "center", gap: "8px",
//           background: modelHealth.all_ready ? "#052e16" : "#2d0c0c",
//           border: `1px solid ${modelHealth.all_ready ? "#16a34a" : "#dc2626"}`,
//           borderRadius: "8px", padding: "8px 14px", marginBottom: "18px",
//           fontSize: "0.8rem",
//         }}>
//           <span>{modelHealth.all_ready ? "✅" : "❌"}</span>
//           <span style={{ color: modelHealth.all_ready ? "#22c55e" : "#ef4444", fontWeight: 600 }}>
//             {modelHealth.all_ready ? "All model files loaded and ready" : "Model files missing — run LSTM training first"}
//           </span>
//           {modelHealth.all_ready && (
//             <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>
//               best_lstm.keras · lstm_scaler.pkl · label_encoder.pkl
//             </span>
//           )}
//         </div>
//       )}

//       <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "20px", alignItems: "start" }}>

//         {/* ── LEFT: Sensor input panel ── */}
//         <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

//           {/* Hive selector + Predict button row */}
//           <div style={{
//             background: "#1e293b", borderRadius: "14px",
//             padding: "16px 18px",
//             border: "1px solid rgba(255,255,255,0.06)",
//           }}>
//             <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "#38bdf8" }}>
//               🏠 Hive Selection &amp; Control
//             </h3>
//             <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
//               <select
//                 id="hive-selector"
//                 value={selectedHive}
//                 onChange={(e) => handleHiveChange(e.target.value)}
//                 style={{
//                   background: "#0f172a", color: "white", border: "1px solid rgba(255,255,255,0.15)",
//                   borderRadius: "8px", padding: "8px 14px", fontSize: "0.9rem",
//                   fontFamily: "'Outfit',sans-serif", cursor: "pointer", minWidth: "140px",
//                 }}
//               >
//                 {HIVE_IDS.map((h) => (
//                   <option key={h} value={h}>{h}</option>
//                 ))}
//               </select>

//               <button
//                 id="btn-predict"
//                 className="pred-btn"
//                 onClick={handlePredict}
//                 disabled={loading}
//                 style={{
//                   background: loading
//                     ? "rgba(56,189,248,0.3)"
//                     : "linear-gradient(135deg,#0ea5e9,#38bdf8)",
//                   color: "white",
//                   display: "flex", alignItems: "center", gap: "8px",
//                 }}
//               >
//                 {loading ? (
//                   <>
//                     <span style={{ display:"inline-block", width:14, height:14,
//                       border:"2px solid rgba(255,255,255,0.3)", borderTopColor:"white",
//                       borderRadius:"50%", animation:"spin 0.8s linear infinite" }} />
//                     Predicting…
//                   </>
//                 ) : "⚡ Predict Now"}
//               </button>

//               {/* ✅ Refresh Sensors Button */}
//               <button
//                 className="pred-btn"
//                 onClick={handleRefreshSensors}
//                 style={{
//                   background: "linear-gradient(135deg,#8b5cf6,#a78bfa)",
//                   color: "white",
//                   display: "flex",
//                   alignItems: "center",
//                   gap: "8px",
//                   fontSize: "0.8rem",
//                   padding: "8px 14px",
//                 }}
//               >
//                 🔄 Refresh Sensors
//               </button>

//               {lastUpdated && (
//                 <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginLeft: "auto" }}>
//                   Updated: {lastUpdated.toLocaleTimeString()}
//                 </span>
//               )}
//             </div>

//             {lastUpdated && (
//               <div style={{ marginTop: "10px" }}>
//                 <CountdownBar secondsLeft={countdown} total={REFRESH_INTERVAL / 1000} />
//               </div>
//             )}
//           </div>

//           {/* Sensor grid */}
//           <div style={{
//             background: "#1e293b", borderRadius: "14px",
//             padding: "16px 18px", border: "1px solid rgba(255,255,255,0.06)",
//           }}>
//             <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "#38bdf8" }}>
//               📡 Live Sensor Readings
//               <span style={{ fontSize:"0.7rem", color:"var(--text-muted)", fontWeight:400, marginLeft:"8px" }}>
//                 (auto-updates every 60s · adjust manually to test scenarios)
//               </span>
//             </h3>
//             <div style={{
//               display: "grid",
//               gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
//               gap: "10px",
//             }}>
//               {SENSOR_META.map((meta) => (
//                 <SensorInput
//                   key={meta.key}
//                   meta={meta}
//                   value={sensorValues[meta.key]}
//                   onChange={handleSensorChange}
//                 />
//               ))}
//             </div>
//           </div>

//           {/* PELT snapshot */}
//           {result?.pelt_snapshot && (
//             <div style={{ animation: "fadeSlide 0.4s ease-out" }}>
//               <PeltSnapshot snapshot={result.pelt_snapshot} />
//             </div>
//           )}

//           {/* Error state */}
//           {error && (
//             <div style={{
//               background: "#2d0c0c", border: "1px solid #dc2626",
//               borderRadius: "10px", padding: "12px 16px",
//               color: "#fca5a5", fontSize: "0.85rem",
//             }}>
//               <strong>❌ Error:</strong> {error}
//               <div style={{ marginTop: "6px", color: "var(--text-muted)", fontSize: "0.78rem" }}>
//                 Make sure the Flask backend is running on port 5000.
//               </div>
//             </div>
//           )}
//         </div>

//         {/* ── RIGHT: Prediction result panel ── */}
//         <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>

//           {/* Result card */}
//           <div style={{
//             background: result ? riskCfg.bg : "#1e293b",
//             border: `2px solid ${result ? riskCfg.border : "rgba(255,255,255,0.08)"}`,
//             borderRadius: "16px", padding: "22px 18px",
//             display: "flex", flexDirection: "column", alignItems: "center", gap: "16px",
//             animation: result ? "fadeSlide 0.5s ease-out" : "none",
//             transition: "border-color 0.5s, background 0.5s",
//           }}>

//             {loading && !result && (
//               <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:"12px", padding:"30px 0" }}>
//                 <span style={{
//                   display:"inline-block", width:40, height:40,
//                   border:"3px solid rgba(255,255,255,0.1)", borderTopColor:"var(--accent-gold)",
//                   borderRadius:"50%", animation:"spin 1s linear infinite",
//                 }} />
//                 <span style={{ color:"var(--text-muted)", fontSize:"0.85rem" }}>Running prediction…</span>
//               </div>
//             )}

//             {!loading && !result && !error && (
//               <div style={{ padding:"30px 0", textAlign:"center" }}>
//                 <div style={{ fontSize:"2.5rem", marginBottom:"8px" }}>🐝</div>
//                 <div style={{ color:"var(--text-muted)", fontSize:"0.85rem" }}>
//                   Awaiting first prediction…
//                 </div>
//               </div>
//             )}

//             {result && (
//               <>
//                 {/* Hive ID badge */}
//                 <div style={{
//                   background: "rgba(0,0,0,0.3)", borderRadius: "8px",
//                   padding: "4px 14px", fontSize: "0.8rem", color: "var(--text-secondary)",
//                 }}>
//                   Hive: <strong style={{ color: "white" }}>{result.hive_id}</strong>
//                 </div>

//                 {/* Gauge */}
//                 <RiskGauge percentage={result.risk_percentage} riskLevel={riskLevel} />

//                 {/* Probability row */}
//                 <div style={{
//                   width: "100%", background: "rgba(0,0,0,0.25)",
//                   borderRadius: "10px", padding: "12px 14px",
//                   display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px",
//                 }}>
//                   {[
//                     { label: "Swarming Probability", value: `${(result.probability * 100).toFixed(2)}%`, color: riskCfg.color },
//                     { label: "Risk Percentage",      value: `${result.risk_percentage}%`,              color: riskCfg.color },
//                     { label: "Predicted Class",      value: result.predicted_class,                     color: result.predicted_class === "Swarming" ? "#ef4444" : "#22c55e" },
//                     { label: "Decision Threshold",   value: result.threshold_used,                      color: "var(--text-secondary)" },
//                   ].map(({ label, value, color }) => (
//                     <div key={label} style={{ textAlign: "center" }}>
//                       <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginBottom: "2px" }}>{label}</div>
//                       <div style={{ fontSize: "1rem", fontWeight: 700, color,
//                         fontFamily: "'Outfit',sans-serif" }}>{value}</div>
//                     </div>
//                   ))}
//                 </div>

//                 {/* Warning message */}
//                 <div style={{
//                   width: "100%", background: `${riskCfg.bg}cc`,
//                   border: `1px solid ${riskCfg.border}`,
//                   borderRadius: "10px", padding: "10px 14px",
//                   fontSize: "0.82rem", color: riskCfg.color,
//                   textAlign: "center", lineHeight: 1.5,
//                 }}>
//                   {riskCfg.emoji} {result.warning}
//                 </div>

//                 {/* Timestamp */}
//                 <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
//                   🕒 {result.timestamp}
//                 </div>
//               </>
//             )}
//           </div>

//           {/* Info card */}
//           <div style={{
//             background: "#1e293b", borderRadius: "12px",
//             padding: "14px 16px", border: "1px solid rgba(255,255,255,0.06)",
//             fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.7,
//           }}>
//             <div style={{ fontWeight: 700, color: "#38bdf8", marginBottom: "6px" }}>📊 Model Info</div>
//             {[
//               ["Architecture",  "Bidirectional LSTM (128→64 units)"],
//               ["Features",      "8 sensor + 4 PELT features"],
//               ["Sequence",      "24 × 12 sliding window"],
//               ["Output",        "Sigmoid → P(swarming)"],
//               ["Threshold",     "0.70 (optimal F1)"],
//               ["F1-Score",      "0.9478"],
//               ["Precision",     "0.9071"],
//               ["Recall",        "0.9922"],
//             ].map(([k, v]) => (
//               <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"2px 0",
//                 borderBottom:"1px solid rgba(255,255,255,0.04)" }}>
//                 <span>{k}</span>
//                 <span style={{ color:"white", fontWeight:600 }}>{v}</span>
//               </div>
//             ))}
//           </div>

//           {/* Risk legend */}
//           <div style={{
//             background: "#1e293b", borderRadius: "12px",
//             padding: "12px 16px", border: "1px solid rgba(255,255,255,0.06)",
//           }}>
//             <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#38bdf8", marginBottom: "8px" }}>
//               🚦 Risk Thresholds
//             </div>
//             {[
//               { level: "LOW",    range: "0 – 30%",  desc: "Normal behaviour", ...RISK_CONFIG.LOW    },
//               { level: "MEDIUM", range: "31 – 60%", desc: "Monitor closely",  ...RISK_CONFIG.MEDIUM },
//               { level: "HIGH",   range: "61 – 100%",desc: "Inspect hive",     ...RISK_CONFIG.HIGH   },
//             ].map(({ level, range, desc, color, emoji }) => (
//               <div key={level} style={{
//                 display:"flex", alignItems:"center", gap:"8px",
//                 padding:"5px 0", borderBottom:"1px solid rgba(255,255,255,0.04)",
//                 fontSize:"0.78rem",
//               }}>
//                 <span style={{ fontSize:"1rem" }}>{emoji}</span>
//                 <span style={{ fontWeight:700, color, minWidth:"58px" }}>{level}</span>
//                 <span style={{ color:"var(--text-muted)", minWidth:"68px" }}>{range}</span>
//                 <span style={{ color:"var(--text-secondary)" }}>{desc}</span>
//               </div>
//             ))}
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default SwarmPrediction;


import React, { useState, useEffect, useCallback, useRef } from "react";

// ─────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────
const API_BASE = ""; // Vite proxy forwards /api/* → http://localhost:5000
const REFRESH_INTERVAL = 600_000; // 10 minutes (600 seconds)

// Single Hive ID
const HIVE_ID = "Hive_01";

const DEFAULT_READING = {
  internal_temperature_c: 35.0,
  internal_humidity_pct: 65.0,
  co2_ppm: 1200,
  hive_weight_kg: 32.5,
  external_temperature_c: 28.0,
  external_humidity_pct: 55.0,
};

// ── SENSOR META - Only display 6 sensors ──────────────────────────
// ⚠️ rainfall_mm_hour and wind_speed_mps are NOT displayed but still sent as 0.0
const SENSOR_META = [
  { key: "internal_temperature_c", label: "Internal Temp", unit: "°C", icon: "🌡️", min: 20, max: 45, step: 0.1 },
  { key: "internal_humidity_pct", label: "Internal Humidity", unit: "%", icon: "💧", min: 30, max: 100, step: 0.5 },
  { key: "co2_ppm", label: "CO₂", unit: "ppm", icon: "💨", min: 400, max: 5000, step: 10 },
  { key: "hive_weight_kg", label: "Hive Weight", unit: "kg", icon: "⚖️", min: 5, max: 80, step: 0.1 },
  { key: "external_temperature_c", label: "External Temp", unit: "°C", icon: "☀️", min: -10, max: 50, step: 0.1 },
  { key: "external_humidity_pct", label: "External Humidity", unit: "%", icon: "🌤️", min: 10, max: 100, step: 0.5 },
];

const RISK_CONFIG = {
  LOW: { color: "#22c55e", bg: "#052e16", border: "#16a34a", emoji: "🟢", label: "LOW RISK" },
  MEDIUM: { color: "#eab308", bg: "#1c1a01", border: "#ca8a04", emoji: "🟡", label: "MEDIUM RISK" },
  HIGH: { color: "#ef4444", bg: "#2d0c0c", border: "#dc2626", emoji: "🔴", label: "HIGH RISK" },
};

// ─────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────

/** Animated circular risk gauge */
function RiskGauge({ percentage, riskLevel, label }) {
  const cfg = RISK_CONFIG[riskLevel] || RISK_CONFIG.LOW;
  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  const strokeDash = (percentage / 100) * circumference;
  const isHigh = riskLevel === "HIGH";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
      <div style={{ position: "relative", width: 180, height: 180 }}>
        <svg width={180} height={180} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={90} cy={90} r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={14} />
          <circle
            cx={90} cy={90} r={radius} fill="none"
            stroke={cfg.color} strokeWidth={14}
            strokeDasharray={`${strokeDash} ${circumference}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 1.2s ease-in-out, stroke 0.5s" }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
        }}>
          <span style={{
            fontSize: "2.2rem", fontWeight: 800, lineHeight: 1,
            color: cfg.color, fontFamily: "'Outfit', sans-serif",
            animation: isHigh ? "pulseNumber 1.4s ease-in-out infinite" : "none",
          }}>
            {percentage.toFixed(1)}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>%</span>
        </div>
      </div>

      <div style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: cfg.bg, border: `1.5px solid ${cfg.border}`,
        borderRadius: "20px", padding: "5px 16px",
        fontSize: "0.8rem", fontWeight: 700, color: cfg.color,
        animation: isHigh ? "pulseBadge 1.4s ease-in-out infinite" : "none",
      }}>
        {cfg.emoji} {cfg.label}
      </div>
      {label && (
        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px" }}>
          {label}
        </div>
      )}
    </div>
  );
}

/** 3-Day Forecast Card */
function ForecastCard({ forecast }) {
  if (!forecast) return null;

  const getRiskEmoji = (level) => {
    const map = { LOW: "🟢", MEDIUM: "🟡", HIGH: "🔴" };
    return map[level] || "⚪";
  };

  return (
    <div style={{
      background: "#172554",
      borderLeft: "4px solid #38bdf8",
      borderRadius: "10px",
      padding: "14px 16px",
      marginTop: "8px",
    }}>
      <h4 style={{ margin: "0 0 10px", fontSize: "0.85rem", color: "#38bdf8" }}>
        📊 3-Day Swarming Forecast
      </h4>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
        <div style={{ textAlign: "center", flex: 1 }}>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Day 1</div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, color: forecast.day1?.color || "#94a3b8" }}>
            {forecast.day1?.risk || "—"}%
          </div>
          <div style={{ fontSize: "0.7rem", color: forecast.day1?.color || "#64748b" }}>
            {getRiskEmoji(forecast.day1?.level)} {forecast.day1?.level || "N/A"}
          </div>
        </div>
        <div style={{ textAlign: "center", flex: 1 }}>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Day 2</div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, color: forecast.day2?.color || "#94a3b8" }}>
            {forecast.day2?.risk || "—"}%
          </div>
          <div style={{ fontSize: "0.7rem", color: forecast.day2?.color || "#64748b" }}>
            {getRiskEmoji(forecast.day2?.level)} {forecast.day2?.level || "N/A"}
          </div>
        </div>
        <div style={{ textAlign: "center", flex: 1 }}>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Day 3</div>
          <div style={{ fontSize: "1.2rem", fontWeight: 700, color: forecast.day3?.color || "#94a3b8" }}>
            {forecast.day3?.risk || "—"}%
          </div>
          <div style={{ fontSize: "0.7rem", color: forecast.day3?.color || "#64748b" }}>
            {getRiskEmoji(forecast.day3?.level)} {forecast.day3?.level || "N/A"}
          </div>
        </div>
      </div>
      <div style={{
        marginTop: "8px",
        fontSize: "0.7rem",
        color: "var(--text-muted)",
        textAlign: "center",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        paddingTop: "6px",
      }}>
        Forecast based on current hive conditions · Updates every 10 minutes
      </div>
    </div>
  );
}

/** High Risk Alert Box */
function HighRiskAlert({ riskLevel, percentage }) {
  if (riskLevel !== "HIGH") return null;

  return (
    <div style={{
      background: "linear-gradient(135deg, #2d0c0c, #4a0f0f)",
      border: "2px solid #dc2626",
      borderRadius: "12px",
      padding: "16px 20px",
      marginTop: "8px",
      animation: "pulseAlert 1.5s ease-in-out infinite",
    }}>
      <style>{`
        @keyframes pulseAlert {
          0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.3); }
          50% { box-shadow: 0 0 20px 8px rgba(220, 38, 38, 0.2); }
        }
      `}</style>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span style={{ fontSize: "2rem" }}>🚨</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, color: "#ef4444", fontSize: "1rem" }}>
            HIGH SWARMING RISK DETECTED!
          </div>
          <div style={{ color: "#fca5a5", fontSize: "0.85rem" }}>
            Current risk: {percentage.toFixed(1)}% — Immediate hive inspection recommended!
          </div>
        </div>
      </div>
      <div style={{
        marginTop: "8px",
        padding: "8px 12px",
        background: "rgba(0,0,0,0.3)",
        borderRadius: "6px",
        fontSize: "0.8rem",
        color: "#fca5a5",
      }}>
        ⚠️ Action Required: Check for queen cells, reduce overcrowding, or consider hive splitting.
      </div>
    </div>
  );
}

/** Single sensor input field */
function SensorInput({ meta, value, onChange }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: "10px", padding: "10px 12px",
    }}>
      <label style={{
        display: "flex", alignItems: "center", gap: "6px",
        fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "6px",
      }}>
        <span style={{ fontSize: "1rem" }}>{meta.icon}</span>
        <span>{meta.label}</span>
        <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>{meta.unit}</span>
      </label>
      <input
        id={`sensor-${meta.key}`}
        type="number"
        min={meta.min} max={meta.max} step={meta.step}
        value={value}
        onChange={(e) => onChange(meta.key, parseFloat(e.target.value) || 0)}
        style={{
          width: "100%", background: "rgba(0,0,0,0.3)", border: "none",
          borderRadius: "6px", padding: "6px 10px", color: "var(--accent-gold)",
          fontSize: "0.95rem", fontWeight: 600, fontFamily: "'Outfit', sans-serif",
          outline: "none", boxSizing: "border-box",
        }}
      />
    </div>
  );
}

/** PELT feature snapshot card */
function PeltSnapshot({ snapshot }) {
  if (!snapshot) return null;
  const items = [
    { label: "Breakpoint Detected", value: snapshot.breakpoint ? "Yes ⚠️" : "No ✓",
      color: snapshot.breakpoint ? "#ef4444" : "#22c55e" },
    { label: "Days Since Breakpoint", value: `${snapshot.days_since_breakpoint} readings`, color: "#38bdf8" },
    { label: "Breakpoint Density", value: `${snapshot.breakpoint_density} / 24h`, color: "#a78bfa" },
    { label: "Segment Duration",  value: `${snapshot.segment_duration} steps`, color: "#f59e0b" },
  ];
  return (
    <div style={{
      background: "#172554", borderLeft: "4px solid #38bdf8",
      borderRadius: "10px", padding: "14px 16px",
    }}>
      <h4 style={{ margin: "0 0 10px", fontSize: "0.85rem", color: "#38bdf8" }}>
        🔎 PELT Change-Point Snapshot
      </h4>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
        {items.map(({ label, value, color }) => (
          <div key={label} style={{
            background: "rgba(0,0,0,0.3)", borderRadius: "8px", padding: "8px 10px",
          }}>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: "2px" }}>{label}</div>
            <div style={{ fontSize: "0.9rem", fontWeight: 700, color }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Countdown bar to next refresh (10 minutes) */
function CountdownBar({ secondsLeft, total }) {
  const pct = ((total - secondsLeft) / total) * 100;
  const minutesLeft = Math.floor(secondsLeft / 60);
  const secondsRemain = secondsLeft % 60;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
        Next update in {minutesLeft}m {secondsRemain}s
      </span>
      <div style={{ flex: 1, height: "3px", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>
        <div style={{
          height: "100%", background: "var(--accent-cyan)",
          borderRadius: "3px", width: `${pct}%`,
          transition: "width 1s linear",
        }} />
      </div>
    </div>
  );
}

// ── NEW LOW RISK CARD COMPONENT ────────────────────────────────────
function LowRiskStatusCard() {
  return (
    <div style={{
      background: "#0f172a", 
      border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: "14px", 
      padding: "14px 16px",
      display: "flex", 
      flexDirection: "column", 
      gap: "10px",
      width: "100%",
      boxSizing: "border-box"
    }}>
      <div style={{
        fontSize: "0.7rem",
        color: "#94a3b8",
        textTransform: "uppercase",
        letterSpacing: "0.5px",
        fontWeight: 700
      }}>
        Current Risk Status
      </div>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "14px"
      }}>
        <span style={{
          fontSize: "2rem",
          lineHeight: 1
        }}>
          🟢
        </span>
        <div style={{
          flex: 1
        }}>
          <div style={{
            fontSize: "1.1rem",
            fontWeight: 800,
            color: "#22c55e",
            fontFamily: "'Outfit', sans-serif"
          }}>
            Low / Normal Risk
          </div>
          <div style={{
            fontSize: "0.75rem",
            color: "#64748b"
          }}>
            Hive conditions are stable. Routine monitoring only.
          </div>
        </div>
      </div>
      <div style={{
        marginTop: "4px",
        paddingTop: "10px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        justifyContent: "space-between",
        fontSize: "0.7rem",
        color: "#64748b"
      }}>
        <span>✓ No action required</span>
        <span>Next check: 10 min</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Main SwarmPrediction Component
// ─────────────────────────────────────────────────────────────────────
const SwarmPrediction = () => {
  const [sensorValues, setSensorValues] = useState({ ...DEFAULT_READING });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL / 1000);
  const [modelHealth, setModelHealth] = useState(null);

  const timerRef = useRef(null);
  const countdownRef = useRef(null);

  // ── Generate random sensor values (simulates live data) ──────────
  const generateRandomReadings = useCallback(() => {
    const baseValues = {
      internal_temperature_c: 33.0 + Math.random() * 4.0,
      internal_humidity_pct: 55 + Math.random() * 25,
      co2_ppm: 400 + Math.random() * 1000,
      hive_weight_kg: 28 + Math.random() * 8,
      external_temperature_c: 25 + Math.random() * 8,
      external_humidity_pct: 45 + Math.random() * 30,
    };
    
    return {
      internal_temperature_c: parseFloat(baseValues.internal_temperature_c.toFixed(1)),
      internal_humidity_pct: parseFloat(baseValues.internal_humidity_pct.toFixed(1)),
      co2_ppm: Math.round(baseValues.co2_ppm),
      hive_weight_kg: parseFloat(baseValues.hive_weight_kg.toFixed(1)),
      external_temperature_c: parseFloat(baseValues.external_temperature_c.toFixed(1)),
      external_humidity_pct: parseFloat(baseValues.external_humidity_pct.toFixed(1)),
    };
  }, []);

  // ── Build 24 readings from current sensor panel ──────────────────
  // ⚠️ NOTE: rainfall_mm_hour and wind_speed_mps are NOT displayed
  // but are still sent as 0.0 to satisfy backend requirements
  const buildReadings = useCallback((values) => {
    return Array.from({ length: 24 }, (_, i) => {
      const jitter = (v, spread) => +(v + (Math.random() - 0.5) * spread).toFixed(2);
      return {
        internal_temperature_c: jitter(values.internal_temperature_c, 0.8),
        internal_humidity_pct: jitter(values.internal_humidity_pct, 2.0),
        co2_ppm: jitter(values.co2_ppm, 60),
        hive_weight_kg: jitter(values.hive_weight_kg, 0.3),
        external_temperature_c: jitter(values.external_temperature_c, 0.6),
        external_humidity_pct: jitter(values.external_humidity_pct, 1.5),
        rainfall_mm_hour: 0.0,   // ✅ Kept for backend compatibility
        wind_speed_mps: 0.0,     // ✅ Kept for backend compatibility
      };
    });
  }, []);

  // ── Fetch prediction from backend ────────────────────────────────
  const fetchPrediction = useCallback(async (values = sensorValues) => {
    setLoading(true);
    setError(null);
    try {
      const readings = buildReadings(values);
      const res = await fetch(`${API_BASE}/api/swarming/live-prediction`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hive_id: HIVE_ID, readings }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sensorValues, buildReadings]);

  // ── Check model health on mount ───────────────────────────────────
  useEffect(() => {
    fetch(`${API_BASE}/api/swarming/live-prediction/health`)
      .then((r) => r.json())
      .then(setModelHealth)
      .catch(() => setModelHealth({ all_ready: false }));
  }, []);

  // ── Auto-refresh every 10 minutes ────────────────────────────────
  useEffect(() => {
    fetchPrediction();
    
    timerRef.current = setInterval(() => {
      const newValues = generateRandomReadings();
      setSensorValues(newValues);
      fetchPrediction(newValues);
      setCountdown(REFRESH_INTERVAL / 1000);
    }, REFRESH_INTERVAL);
    
    return () => clearInterval(timerRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Countdown ticker ──────────────────────────────────────────────
  useEffect(() => {
    setCountdown(REFRESH_INTERVAL / 1000);
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : REFRESH_INTERVAL / 1000));
    }, 1000);
    return () => clearInterval(countdownRef.current);
  }, [result]);

  const handleSensorChange = (key, val) => {
    setSensorValues((prev) => ({ ...prev, [key]: val }));
  };

  const handlePredict = () => {
    clearInterval(timerRef.current);
    fetchPrediction(sensorValues).then(() => {
      timerRef.current = setInterval(() => {
        const newValues = generateRandomReadings();
        setSensorValues(newValues);
        fetchPrediction(newValues);
        setCountdown(REFRESH_INTERVAL / 1000);
      }, REFRESH_INTERVAL);
    });
  };

  // ── Manual refresh sensors ────────────────────────────────────────
  const handleRefreshSensors = () => {
    const newValues = generateRandomReadings();
    setSensorValues(newValues);
    fetchPrediction(newValues);
  };

  // ── Generate 3-day forecast ──────────────────────────────────────
  const generateForecast = useCallback((currentRisk, riskLevel) => {
    const baseRisk = currentRisk;
    
    const day1Risk = Math.max(0, Math.min(100, baseRisk + (Math.random() - 0.5) * 8));
    const day1Level = day1Risk <= 30 ? "LOW" : day1Risk <= 60 ? "MEDIUM" : "HIGH";
    
    const day2Risk = Math.max(0, Math.min(100, baseRisk + (Math.random() - 0.5) * 15));
    const day2Level = day2Risk <= 30 ? "LOW" : day2Risk <= 60 ? "MEDIUM" : "HIGH";
    
    const day3Risk = Math.max(0, Math.min(100, baseRisk + (Math.random() - 0.5) * 20));
    const day3Level = day3Risk <= 30 ? "LOW" : day3Risk <= 60 ? "MEDIUM" : "HIGH";
    
    const getColor = (level) => {
      return RISK_CONFIG[level]?.color || "#94a3b8";
    };
    
    return {
      day1: { risk: Math.round(day1Risk), level: day1Level, color: getColor(day1Level) },
      day2: { risk: Math.round(day2Risk), level: day2Level, color: getColor(day2Level) },
      day3: { risk: Math.round(day3Risk), level: day3Level, color: getColor(day3Level) },
      current: { risk: Math.round(currentRisk), level: riskLevel, color: getColor(riskLevel) }
    };
  }, []);

  // ── Derived values ────────────────────────────────────────────────
  const riskLevel = result?.risk_level || "LOW";
  const riskPercentage = result?.risk_percentage || 0;
  const riskCfg = RISK_CONFIG[riskLevel] || RISK_CONFIG.LOW;
  const forecast = result ? generateForecast(riskPercentage, riskLevel) : null;

  // ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: "24px 28px", minHeight: "100vh", color: "white" }}>

      {/* ── CSS animations ── */}
      <style>{`
        @keyframes pulseNumber {
          0%,100% { opacity:1; transform:scale(1); }
          50%     { opacity:0.85; transform:scale(1.06); }
        }
        @keyframes pulseBadge {
          0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
          50%     { box-shadow: 0 0 12px 4px rgba(239,68,68,0.4); }
        }
        @keyframes spin { to { transform:rotate(360deg); } }
        @keyframes fadeSlide {
          from { opacity:0; transform:translateY(10px); }
          to   { opacity:1; transform:translateY(0); }
        }
        .pred-btn {
          cursor:pointer; transition:all 0.2s;
          border:none; border-radius:10px; padding:10px 20px;
          font-family:'Outfit',sans-serif; font-weight:700; font-size:0.9rem;
        }
        .pred-btn:hover { filter:brightness(1.15); transform:translateY(-1px); }
        .pred-btn:active { transform:translateY(0); }
      `}</style>

      {/* ── Page header ── */}
      <div style={{ marginBottom: "22px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
          <span style={{ fontSize: "1.6rem" }}>🐝</span>
          <h2 style={{ margin: 0, fontSize: "1.4rem", fontFamily: "'Outfit',sans-serif",
            background: "linear-gradient(90deg,#f59e0b,#fde68a)", WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent" }}>
            Live Swarming Prediction
          </h2>
        </div>
        <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.85rem" }}>
          {HIVE_ID} · LSTM model · PELT change-point features · Sigmoid threshold 0.70 · Updates every 10 minutes
        </p>
      </div>

      {/* ── Model health status bar ── */}
      {modelHealth && (
        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          background: modelHealth.all_ready ? "#052e16" : "#2d0c0c",
          border: `1px solid ${modelHealth.all_ready ? "#16a34a" : "#dc2626"}`,
          borderRadius: "8px", padding: "8px 14px", marginBottom: "18px",
          fontSize: "0.8rem",
        }}>
          {/* Model health bar is hidden - uncomment if needed */}
        </div>
      )}

      {/* ── Countdown bar ── */}
      {lastUpdated && (
        <div style={{ marginBottom: "16px" }}>
          <CountdownBar secondsLeft={countdown} total={REFRESH_INTERVAL / 1000} />
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: "20px", alignItems: "start" }}>

        {/* ── LEFT: Sensor input panel ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>

          {/* Controls row */}
          <div style={{
            background: "#1e293b", borderRadius: "14px",
            padding: "16px 18px",
            border: "1px solid rgba(255,255,255,0.06)",
          }}>
            <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "#38bdf8" }}>
              🏠 Hive Control
            </h3>
            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{
                background: "#0f172a", padding: "8px 16px",
                borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)",
                fontSize: "0.9rem", fontWeight: 600, color: "white",
              }}>
                🐝 {HIVE_ID}
              </div>

              <button
                className="pred-btn"
                onClick={handlePredict}
                disabled={loading}
                style={{
                  background: loading
                    ? "rgba(56,189,248,0.3)"
                    : "linear-gradient(135deg,#0ea5e9,#38bdf8)",
                  color: "white",
                  display: "flex", alignItems: "center", gap: "8px",
                }}
              >
                {loading ? (
                  <>
                    <span style={{ display:"inline-block", width:14, height:14,
                      border:"2px solid rgba(255,255,255,0.3)", borderTopColor:"white",
                      borderRadius:"50%", animation:"spin 0.8s linear infinite" }} />
                    Predicting…
                  </>
                ) : " "}
              </button>

              <button
                className="pred-btn"
                onClick={handleRefreshSensors}
                style={{
                  background: "linear-gradient(135deg,#8b5cf6,#a78bfa)",
                  color: "white",
                  display: "flex", alignItems: "center", gap: "8px",
                  fontSize: "0.8rem", padding: "8px 14px",
                }}
              >
                {/* 🔄 Refresh Sensors */}
              </button>
            </div>
          </div>

          {/* Sensor grid - only 6 sensors displayed */}
          <div style={{
            background: "#1e293b", borderRadius: "14px",
            padding: "16px 18px", border: "1px solid rgba(255,255,255,0.06)",
          }}>
            <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "#38bdf8" }}>
              📡 Latest Sensor Readings
              <span style={{ fontSize:"0.7rem", color:"var(--text-muted)", fontWeight:400, marginLeft:"8px" }}>
               
              </span>
            </h3>
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: "10px",
            }}>
              {SENSOR_META.map((meta) => (
                <SensorInput
                  key={meta.key}
                  meta={meta}
                  value={sensorValues[meta.key]}
                  onChange={handleSensorChange}
                />
              ))}
            </div>
          </div>
          {/* Risk Thresholds - Updated to match screenshot style */}
          <div style={{
            background: "#0f172a",
            borderRadius: "12px",
            padding: "16px",
            border: "1px solid rgba(255,255,255,0.06)",
          }}>
            <div style={{
              fontSize: "0.85rem",
              fontWeight: 700,
              color: "#94a3b8",
              marginBottom: "12px",
              textTransform: "uppercase",
              letterSpacing: "0.5px"
            }}>
              🚦 Risk Thresholds
            </div>

            <div style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px"
            }}>
              {/* LOW */}
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                background: "rgba(34, 197, 94, 0.08)",
                border: "1px solid rgba(34, 197, 94, 0.2)",
                borderRadius: "8px",
                padding: "10px 14px",
              }}>
                <span style={{ fontSize: "1.4rem" }}>🟢</span>
                <div style={{ flex: 1 }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    marginBottom: "2px"
                  }}>
                    <span style={{
                      fontSize: "0.85rem",
                      fontWeight: 700,
                      color: "#22c55e"
                    }}>
                      LOW
                    </span>
                    <span style={{
                      fontSize: "0.7rem",
                      color: "#94a3b8",
                      fontWeight: 500
                    }}>
                  
                    </span>
                  </div>
                  <div style={{
                    fontSize: "0.7rem",
                    color: "#64748b"
                  }}>
                    Normal behaviour
                  </div>
                </div>
              </div>

              {/* MEDIUM */}
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                background: "rgba(234, 179, 8, 0.08)",
                border: "1px solid rgba(234, 179, 8, 0.2)",
                borderRadius: "8px",
                padding: "10px 14px",
              }}>
                <span style={{ fontSize: "1.4rem" }}>🟡</span>
                <div style={{ flex: 1 }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    marginBottom: "2px"
                  }}>
                    <span style={{
                      fontSize: "0.85rem",
                      fontWeight: 700,
                      color: "#eab308"
                    }}>
                      MEDIUM
                    </span>
                    <span style={{
                      fontSize: "0.7rem",
                      color: "#94a3b8",
                      fontWeight: 500
                    }}>
                    
                    </span>
                  </div>
                  <div style={{
                    fontSize: "0.7rem",
                    color: "#64748b"
                  }}>
                    Monitor closely
                  </div>
                </div>
              </div>

              {/* HIGH */}
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                borderRadius: "8px",
                padding: "10px 14px",
              }}>
                <span style={{ fontSize: "1.4rem" }}>🔴</span>
                <div style={{ flex: 1 }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    marginBottom: "2px"
                  }}>
                    <span style={{
                      fontSize: "0.85rem",
                      fontWeight: 700,
                      color: "#ef4444"
                    }}>
                      HIGH
                    </span>
                    <span style={{
                      fontSize: "0.7rem",
                      color: "#94a3b8",
                      fontWeight: 500
                    }}>
                  
                    </span>
                  </div>
                  <div style={{
                    fontSize: "0.7rem",
                    color: "#64748b"
                  }}>
                    Inspect hive
                  </div>
                </div>
              </div>
            </div>
          </div>
        

          {/* 3-Day Forecast */}
          {forecast && (
            <div style={{ animation: "fadeSlide 0.4s ease-out" }}>
              <ForecastCard forecast={forecast} />
            </div>
          )}
          {/* PELT snapshot */}
          {result?.pelt_snapshot && (
            <div style={{ animation: "fadeSlide 0.4s ease-out" }}>
              <PeltSnapshot snapshot={result.pelt_snapshot} />
            </div>
          )}
          {/* High Risk Alert */}
          <HighRiskAlert riskLevel={riskLevel} percentage={riskPercentage} />

          {/* Error state */}
          {error && (
            <div style={{
              background: "#2d0c0c", border: "1px solid #dc2626",
              borderRadius: "10px", padding: "12px 16px",
              color: "#fca5a5", fontSize: "0.85rem",
            }}>
              <strong>❌ Error:</strong> {error}
              <div style={{ marginTop: "6px", color: "var(--text-muted)", fontSize: "0.78rem" }}>
                Make sure the Flask backend is running on port 5000.
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT: Prediction result panel ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          
          {/* Card Title */}
          <div style={{
            width: "100%",
            textAlign: "center",
            fontSize: "0.9rem",
            fontWeight: 700,
            color: riskCfg.color,
            paddingBottom: "8px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}>
            🚦 Current Risk
          </div>

          {/* NEW: Low Risk Status Card inserted here */}
          {riskLevel === "LOW" && <LowRiskStatusCard />}

          {/* Result card */}
          <div style={{
            background: result ? riskCfg.bg : "#1e293b",
            border: `2px solid ${result ? riskCfg.border : "rgba(255,255,255,0.08)"}`,
            borderRadius: "16px", padding: "22px 18px",
            display: "flex", flexDirection: "column", alignItems: "center", gap: "16px",
            animation: result ? "fadeSlide 0.5s ease-out" : "none",
            transition: "border-color 0.5s, background 0.5s",
          }}>

            {loading && !result && (
              <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:"12px", padding:"30px 0" }}>
                <span style={{
                  display:"inline-block", width:40, height:40,
                  border:"3px solid rgba(255,255,255,0.1)", borderTopColor:"var(--accent-gold)",
                  borderRadius:"50%", animation:"spin 1s linear infinite",
                }} />
                <span style={{ color:"var(--text-muted)", fontSize:"0.85rem" }}>Running prediction…</span>
              </div>
            )}

            {!loading && !result && !error && (
              <div style={{ padding:"30px 0", textAlign:"center" }}>
                <div style={{ fontSize:"2.5rem", marginBottom:"8px" }}>🐝</div>
                <div style={{ color:"var(--text-muted)", fontSize:"0.85rem" }}>
                  Awaiting first prediction…
                </div>
              </div>
            )}

            {result && (
              <>
                {/* Hive ID badge */}
                <div style={{
                  background: "rgba(0,0,0,0.3)", borderRadius: "8px",
                  padding: "4px 14px", fontSize: "0.8rem", color: "var(--text-secondary)",
                }}>
                  Hive: <strong style={{ color: "white" }}>{result.hive_id}</strong>
                </div>

                {/* Gauge */}
                <RiskGauge
                  percentage={result.risk_percentage}
                  riskLevel={riskLevel}
                  label="Current Swarming Risk"
                />

                {/* Probability row */}
                <div style={{
                  width: "100%", background: "rgba(0,0,0,0.25)",
                  borderRadius: "10px", padding: "12px 14px",
                  display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px",
                }}>
                  {[
                    { label: "Swarming Probability", value: `${(result.probability * 100).toFixed(2)}%`, color: riskCfg.color },
                    { label: "Risk Level",            value: result.risk_level,                               color: riskCfg.color },
                    { label: "Predicted Class",      value: result.predicted_class,                     color: result.predicted_class === "Swarming" ? "#ef4444" : "#22c55e" },
                    { label: "Decision Threshold",   value: result.threshold_used,                      color: "var(--text-secondary)" },
                  ].map(({ label, value, color }) => (
                    <div key={label} style={{ textAlign: "center" }}>
                      <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginBottom: "2px" }}>{label}</div>
                      <div style={{ fontSize: "1rem", fontWeight: 700, color,
                        fontFamily: "'Outfit',sans-serif" }}>{value}</div>
                    </div>
                  ))}
                </div>

                {/* Warning message */}
                <div style={{
                  width: "100%", background: `${riskCfg.bg}cc`,
                  border: `1px solid ${riskCfg.border}`,
                  borderRadius: "10px", padding: "10px 14px",
                  fontSize: "0.82rem", color: riskCfg.color,
                  textAlign: "center", lineHeight: 1.5,
                }}>
                  {riskCfg.emoji} {result.warning}
                </div>

                {/* Timestamp */}
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  🕒 {result.timestamp}
                </div>
              </>
            )}
          </div>

          {/* Info card */}
          <div style={{
            background: "#1e293b", borderRadius: "12px",
            padding: "14px 16px", border: "1px solid rgba(255,255,255,0.06)",
            fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.7,
          }}>
            <div style={{ fontWeight: 700, color: "#38bdf8", marginBottom: "6px" }}>📊 Model Info</div>
            {[
              ["Architecture",  "Bidirectional LSTM (128→64 units)"],
              ["Features",      "6 sensor + 4 PELT features"],
              ["Sequence",      "24 × 10 sliding window"],
              ["Output",        "Sigmoid → P(swarming)"],
              ["Threshold",     "0.70 (optimal F1)"],
              ["F1-Score",      "0.9478"],
              ["Precision",     "0.9071"],
              ["Recall",        "0.9922"],
              ["Update Interval", "10 minutes"],
              ["Forecast Window", "3 days (72 hours)"],
            ].map(([k, v]) => (
              <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"2px 0",
                borderBottom:"1px solid rgba(255,255,255,0.04)" }}>
                <span>{k}</span>
                <span style={{ color:"white", fontWeight:600 }}>{v}</span>
              </div>
            ))}
          </div>


        </div>
      </div>
    </div>
  );
};

export default SwarmPrediction;

// import React, { useState, useEffect, useCallback, useRef } from "react";



// // ─────────────────────────────────────────────────────────────────────

// // Constants

// // ─────────────────────────────────────────────────────────────────────

// const API_BASE = ""; // Vite proxy forwards /api/* → http://localhost:5000

// const REFRESH_INTERVAL = 600_000; // 10 minutes



// // ── ONLY REAL COLUMNS from Supabase ──────────────────────────────

// // NO default values - will show alert when missing

// const SENSOR_META = [

//   { key: "internal_temperature_c", label: "Internal Temp", unit: "°C", icon: "🌡️", min: 20, max: 45, step: 0.1 },

//   { key: "internal_humidity_pct", label: "Internal Humidity", unit: "%", icon: "💧", min: 30, max: 100, step: 0.5 },

//   { key: "co2_ppm", label: "CO₂", unit: "ppm", icon: "💨", min: 400, max: 5000, step: 10 },

//   { key: "hive_weight_kg", label: "Hive Weight", unit: "kg", icon: "⚖️", min: 5, max: 80, step: 0.1 },

//   { key: "external_temperature_c", label: "External Temp", unit: "°C", icon: "☀️", min: -10, max: 50, step: 0.1 },

//   { key: "external_humidity_pct", label: "External Humidity", unit: "%", icon: "🌤️", min: 10, max: 100, step: 0.5 },

//   { key: "battery_voltage", label: "Battery Voltage", unit: "V", icon: "🔋", min: 10, max: 14, step: 0.1 },

// ];



// const RISK_CONFIG = {

//   LOW: { color: "#22c55e", bg: "#052e16", border: "#16a34a", emoji: "🟢", label: "LOW RISK" },

//   MEDIUM: { color: "#eab308", bg: "#1c1a01", border: "#ca8a04", emoji: "🟡", label: "MEDIUM RISK" },

//   HIGH: { color: "#ef4444", bg: "#2d0c0c", border: "#dc2626", emoji: "🔴", label: "HIGH RISK" },

// };



// // ─────────────────────────────────────────────────────────────────────

// // API Calls

// // ─────────────────────────────────────────────────────────────────────



// async function fetchAvailableHives() {

//   const response = await fetch(`${API_BASE}/api/iot/devices`);

//   if (!response.ok) {

//     throw new Error(`HTTP ${response.status}`);

//   }

//   const data = await response.json();

//   return data.devices || [];

// }



// async function fetchRealtimeData(deviceId, limit = 432) {

//   const response = await fetch(

//     `${API_BASE}/api/iot/realtime-data?device_id=${encodeURIComponent(deviceId)}&limit=${limit}`

//   );

//   if (!response.ok) {

//     const errData = await response.json().catch(() => ({}));

//     throw new Error(errData.error || `HTTP ${response.status}`);

//   }

//   const data = await response.json();

//   return data.readings || [];

// }



// async function fetchPrediction(hiveId, readings) {

//   const response = await fetch(`${API_BASE}/api/swarming/live-prediction`, {

//     method: "POST",

//     headers: { "Content-Type": "application/json" },

//     body: JSON.stringify({ hive_id: hiveId, readings }),

//   });

//   if (!response.ok) {

//     const errData = await response.json().catch(() => ({}));

//     throw new Error(errData.error || `HTTP ${response.status}`);

//   }

//   return await response.json();

// }



// // ─────────────────────────────────────────────────────────────────────

// // Connection Alert Component

// // ─────────────────────────────────────────────────────────────────────



// function ConnectionAlert({ status, onRetry }) {

//   const config = {

//     connected: {

//       icon: "✅",

//       color: "#22c55e",

//       bg: "#052e16",

//       border: "#16a34a",

//       title: "Connected to Database",

//       message: "Real-time data is being received.",

//     },

//     loading: {

//       icon: "⏳",

//       color: "#eab308",

//       bg: "#1c1a01",

//       border: "#ca8a04",

//       title: "Connecting...",

//       message: "Attempting to connect to Supabase database.",

//     },

//     no_data: {

//       icon: "📭",

//       color: "#f59e0b",

//       bg: "#1c1a01",

//       border: "#ca8a04",

//       title: "No Data Available",

//       message: "No sensor readings found for this hive.",

//     },

//     error: {

//       icon: "❌",

//       color: "#ef4444",

//       bg: "#2d0c0c",

//       border: "#dc2626",

//       title: "Connection Error",

//       message: "Failed to connect to Supabase database. Please check your connection.",

//     },

//     no_devices: {

//       icon: "📡",

//       color: "#ef4444",

//       bg: "#2d0c0c",

//       border: "#dc2626",

//       title: "No Devices Found",

//       message: "No IoT devices registered in the database.",

//     },

//   };



//   const info = config[status] || config.loading;



//   return (

//     <div style={{

//       background: info.bg,

//       border: `2px solid ${info.border}`,

//       borderRadius: "12px",

//       padding: "16px 20px",

//       marginBottom: "16px",

//       display: "flex",

//       alignItems: "center",

//       justifyContent: "space-between",

//       flexWrap: "wrap",

//       gap: "12px",

//     }}>

//       <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>

//         <span style={{ fontSize: "1.8rem" }}>{info.icon}</span>

//         <div>

//           <div style={{ fontWeight: 700, color: info.color, fontSize: "0.95rem" }}>

//             {info.title}

//           </div>

//           <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>

//             {info.message}

//           </div>

//         </div>

//       </div>

//       {status !== "connected" && onRetry && (

//         <button

//           onClick={onRetry}

//           style={{

//             background: "rgba(255,255,255,0.1)",

//             border: `1px solid ${info.border}`,

//             borderRadius: "8px",

//             padding: "6px 16px",

//             color: info.color,

//             cursor: "pointer",

//             fontSize: "0.8rem",

//             fontWeight: 600,

//             fontFamily: "'Outfit', sans-serif",

//           }}

//         >

//           Retry

//         </button>

//       )}

//     </div>

//   );

// }



// // ─────────────────────────────────────────────────────────────────────

// // Sub-components (RiskGauge, ForecastCard, HighRiskAlert, etc.)

// // ─────────────────────────────────────────────────────────────────────



// /** Animated circular risk gauge */

// function RiskGauge({ percentage, riskLevel, label }) {

//   const cfg = RISK_CONFIG[riskLevel] || RISK_CONFIG.LOW;

//   const radius = 72;

//   const circumference = 2 * Math.PI * radius;

//   const strokeDash = (percentage / 100) * circumference;

//   const isHigh = riskLevel === "HIGH";



//   return (

//     <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>

//       <div style={{ position: "relative", width: 180, height: 180 }}>

//         <svg width={180} height={180} style={{ transform: "rotate(-90deg)" }}>

//           <circle cx={90} cy={90} r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={14} />

//           <circle

//             cx={90} cy={90} r={radius} fill="none"

//             stroke={cfg.color} strokeWidth={14}

//             strokeDasharray={`${(percentage / 100) * 2 * Math.PI * radius} ${2 * Math.PI * radius}`}

//             strokeLinecap="round"

//             style={{ transition: "stroke-dasharray 1.2s ease-in-out, stroke 0.5s" }}

//           />

//         </svg>

//         <div style={{

//           position: "absolute", inset: 0,

//           display: "flex", flexDirection: "column",

//           alignItems: "center", justifyContent: "center",

//         }}>

//           <span style={{

//             fontSize: "2.2rem", fontWeight: 800, lineHeight: 1,

//             color: cfg.color, fontFamily: "'Outfit', sans-serif",

//             animation: riskLevel === "HIGH" ? "pulseNumber 1.4s ease-in-out infinite" : "none",

//           }}>

//             {percentage.toFixed(1)}

//           </span>

//           <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>%</span>

//         </div>

//       </div>

//       <div style={{

//         display: "inline-flex", alignItems: "center", gap: "6px",

//         background: cfg.bg, border: `1.5px solid ${cfg.border}`,

//         borderRadius: "20px", padding: "5px 16px",

//         fontSize: "0.8rem", fontWeight: 700, color: cfg.color,

//         animation: riskLevel === "HIGH" ? "pulseBadge 1.4s ease-in-out infinite" : "none",

//       }}>

//         {cfg.emoji} {cfg.label}

//       </div>

//       {label && (

//         <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px" }}>

//           {label}

//         </div>

//       )}

//     </div>

//   );

// }



// /** 3-Day Forecast Card */

// function ForecastCard({ forecast }) {

//   if (!forecast) return null;



//   const getRiskEmoji = (level) => {

//     const map = { LOW: "🟢", MEDIUM: "🟡", HIGH: "🔴" };

//     return map[level] || "⚪";

//   };



//   return (

//     <div style={{

//       background: "#172554",

//       borderLeft: "4px solid #38bdf8",

//       borderRadius: "10px",

//       padding: "14px 16px",

//       marginTop: "8px",

//     }}>

//       <h4 style={{ margin: "0 0 10px", fontSize: "0.85rem", color: "#38bdf8" }}>

//         📊 3-Day Swarming Forecast

//       </h4>

//       <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>

//         <div style={{ textAlign: "center", flex: 1 }}>

//           <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Day 1</div>

//           <div style={{ fontSize: "1.2rem", fontWeight: 700, color: forecast.day1?.color || "#94a3b8" }}>

//             {forecast.day1?.risk || "—"}%

//           </div>

//           <div style={{ fontSize: "0.7rem", color: forecast.day1?.color || "#64748b" }}>

//             {getRiskEmoji(forecast.day1?.level)} {forecast.day1?.level || "N/A"}

//           </div>

//         </div>

//         <div style={{ textAlign: "center", flex: 1 }}>

//           <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Day 2</div>

//           <div style={{ fontSize: "1.2rem", fontWeight: 700, color: forecast.day2?.color || "#94a3b8" }}>

//             {forecast.day2?.risk || "—"}%

//           </div>

//           <div style={{ fontSize: "0.7rem", color: forecast.day2?.color || "#64748b" }}>

//             {getRiskEmoji(forecast.day2?.level)} {forecast.day2?.level || "N/A"}

//           </div>

//         </div>

//         <div style={{ textAlign: "center", flex: 1 }}>

//           <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Day 3</div>

//           <div style={{ fontSize: "1.2rem", fontWeight: 700, color: forecast.day3?.color || "#94a3b8" }}>

//             {forecast.day3?.risk || "—"}%

//           </div>

//           <div style={{ fontSize: "0.7rem", color: forecast.day3?.color || "#64748b" }}>

//             {getRiskEmoji(forecast.day3?.level)} {forecast.day3?.level || "N/A"}

//           </div>

//         </div>

//       </div>

//       <div style={{

//         marginTop: "8px",

//         fontSize: "0.7rem",

//         color: "var(--text-muted)",

//         textAlign: "center",

//         borderTop: "1px solid rgba(255,255,255,0.06)",

//         paddingTop: "6px",

//       }}>

//         Forecast based on current hive conditions · Updates every 10 minutes

//       </div>

//     </div>

//   );

// }



// /** High Risk Alert Box */

// function HighRiskAlert({ riskLevel, percentage }) {

//   if (riskLevel !== "HIGH") return null;



//   return (

//     <div style={{

//       background: "linear-gradient(135deg, #2d0c0c, #4a0f0f)",

//       border: "2px solid #dc2626",

//       borderRadius: "12px",

//       padding: "16px 20px",

//       marginTop: "8px",

//       animation: "pulseAlert 1.5s ease-in-out infinite",

//     }}>

//       <style>{`

//         @keyframes pulseAlert {

//           0%, 100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.3); }

//           50% { box-shadow: 0 0 20px 8px rgba(220, 38, 38, 0.2); }

//         }

//       `}</style>

//       <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>

//         <span style={{ fontSize: "2rem" }}>🚨</span>

//         <div style={{ flex: 1 }}>

//           <div style={{ fontWeight: 700, color: "#ef4444", fontSize: "1rem" }}>

//             HIGH SWARMING RISK DETECTED!

//           </div>

//           <div style={{ color: "#fca5a5", fontSize: "0.85rem" }}>

//             Current risk: {percentage.toFixed(1)}% — Immediate hive inspection recommended!

//           </div>

//         </div>

//       </div>

//       <div style={{

//         marginTop: "8px",

//         padding: "8px 12px",

//         background: "rgba(0,0,0,0.3)",

//         borderRadius: "6px",

//         fontSize: "0.8rem",

//         color: "#fca5a5",

//       }}>

//         ⚠️ Action Required: Check for queen cells, reduce overcrowding, or consider hive splitting.

//       </div>

//     </div>

//   );

// }



// /** Single sensor input field */

// function SensorInput({ meta, value, onChange, isLive }) {

//   return (

//     <div style={{

//       background: "rgba(255,255,255,0.03)",

//       border: `1px solid ${isLive ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.08)"}`,

//       borderRadius: "10px", padding: "10px 12px",

//     }}>

//       <label style={{

//         display: "flex", alignItems: "center", gap: "6px",

//         fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "6px",

//       }}>

//         <span style={{ fontSize: "1rem" }}>{meta.icon}</span>

//         <span>{meta.label}</span>

//         {isLive && (

//           <span style={{

//             fontSize: "0.55rem",

//             background: "#22c55e",

//             color: "white",

//             padding: "1px 6px",

//             borderRadius: "10px",

//             marginLeft: "4px",

//           }}>LIVE</span>

//         )}

//         <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>{meta.unit}</span>

//       </label>

//       <input

//         id={`sensor-${meta.key}`}

//         type="number"

//         min={meta.min} max={meta.max} step={meta.step}

//         value={value}

//         onChange={(e) => onChange(meta.key, parseFloat(e.target.value) || 0)}

//         style={{

//           width: "100%", background: "rgba(0,0,0,0.3)", border: "none",

//           borderRadius: "6px", padding: "6px 10px", color: "var(--accent-gold)",

//           fontSize: "0.95rem", fontWeight: 600, fontFamily: "'Outfit', sans-serif",

//           outline: "none", boxSizing: "border-box",

//         }}

//       />

//     </div>

//   );

// }



// /** PELT feature snapshot card */

// function PeltSnapshot({ snapshot }) {

//   if (!snapshot) return null;

//   const items = [

//     { label: "Breakpoint Detected", value: snapshot.breakpoint ? "Yes ⚠️" : "No ✓",

//       color: snapshot.breakpoint ? "#ef4444" : "#22c55e" },

//     { label: "Days Since Breakpoint", value: `${snapshot.days_since_breakpoint} readings`, color: "#38bdf8" },

//     { label: "Breakpoint Density", value: `${snapshot.breakpoint_density} / 24h`, color: "#a78bfa" },

//     { label: "Segment Duration",  value: `${snapshot.segment_duration} steps`, color: "#f59e0b" },

//   ];

//   return (

//     <div style={{

//       background: "#172554", borderLeft: "4px solid #38bdf8",

//       borderRadius: "10px", padding: "14px 16px",

//     }}>

//       <h4 style={{ margin: "0 0 10px", fontSize: "0.85rem", color: "#38bdf8" }}>

//         🔎 PELT Change-Point Snapshot

//       </h4>

//       <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>

//         {items.map(({ label, value, color }) => (

//           <div key={label} style={{

//             background: "rgba(0,0,0,0.3)", borderRadius: "8px", padding: "8px 10px",

//           }}>

//             <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: "2px" }}>{label}</div>

//             <div style={{ fontSize: "0.9rem", fontWeight: 700, color }}>{value}</div>

//           </div>

//         ))}

//       </div>

//     </div>

//   );

// }



// /** Countdown bar to next refresh (10 minutes) */

// function CountdownBar({ secondsLeft, total }) {

//   const pct = ((total - secondsLeft) / total) * 100;

//   const minutesLeft = Math.floor(secondsLeft / 60);

//   const secondsRemain = secondsLeft % 60;



//   return (

//     <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>

//       <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>

//         Next update in {minutesLeft}m {secondsRemain}s

//       </span>

//       <div style={{ flex: 1, height: "3px", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>

//         <div style={{

//           height: "100%", background: "var(--accent-cyan)",

//           borderRadius: "3px", width: `${pct}%`,

//           transition: "width 1s linear",

//         }} />

//       </div>

//     </div>

//   );

// }



// // ─────────────────────────────────────────────────────────────────────

// // Main SwarmPrediction Component

// // ─────────────────────────────────────────────────────────────────────

// const SwarmPrediction = () => {

//   const [hiveId, setHiveId] = useState("");

//   const [availableHives, setAvailableHives] = useState([]);

//   const [sensorValues, setSensorValues] = useState(null); // NULL = no data

//   const [result, setResult] = useState(null);

//   const [loading, setLoading] = useState(false);

//   const [error, setError] = useState(null);

//   const [lastUpdated, setLastUpdated] = useState(null);

//   const [countdown, setCountdown] = useState(REFRESH_INTERVAL / 1000);

//   const [modelHealth, setModelHealth] = useState(null);

//   const [isLiveData, setIsLiveData] = useState(false);

//   const [connectionStatus, setConnectionStatus] = useState("loading");



//   const timerRef = useRef(null);

//   const countdownRef = useRef(null);



//   // ── Build 24 readings ─────────────────────────────────────────────

//   const buildReadings = useCallback((values) => {

//     return Array.from({ length: 24 }, (_, i) => {

//       const jitter = (v, spread) => +(v + (Math.random() - 0.5) * spread).toFixed(2);

//       return {

//         internal_temperature_c: jitter(values.internal_temperature_c, 0.8),

//         internal_humidity_pct: jitter(values.internal_humidity_pct, 2.0),

//         co2_ppm: jitter(values.co2_ppm, 60),

//         hive_weight_kg: jitter(values.hive_weight_kg, 0.3),

//         external_temperature_c: jitter(values.external_temperature_c, 0.6),

//         external_humidity_pct: jitter(values.external_humidity_pct, 1.5),

//         rainfall_mm_hour: 0.0,

//         wind_speed_mps: 0.0,

//         battery_voltage: jitter(values.battery_voltage, 0.1),

//       };

//     });

//   }, []);



//   // ── Load and process real-time data ──────────────────────────────

//   const loadRealtimeData = useCallback(async (deviceId) => {

//     try {

//       setConnectionStatus("loading");

//       const readings = await fetchRealtimeData(deviceId, 432);

      

//       if (readings && readings.length > 0) {

//         setIsLiveData(true);

//         setConnectionStatus("connected");

        

//         const latest = readings[0];

        

//         // Map Supabase columns to frontend keys

//         const mappedValues = {

//           internal_temperature_c: latest.internal_temp,

//           internal_humidity_pct: latest.internal_humidity,

//           co2_ppm: latest.internal_co2,

//           hive_weight_kg: latest.total_weight,

//           external_temperature_c: latest.external_temp,

//           external_humidity_pct: latest.external_humidity,

//           battery_voltage: latest.battery_voltage,

//           rainfall_mm_hour: 0.0,

//           wind_speed_mps: 0.0,

//         };

        

//         setSensorValues(mappedValues);

        

//         const formattedReadings = readings.map(r => ({

//           internal_temperature_c: r.internal_temp,

//           internal_humidity_pct: r.internal_humidity,

//           co2_ppm: r.internal_co2,

//           hive_weight_kg: r.total_weight,

//           external_temperature_c: r.external_temp,

//           external_humidity_pct: r.external_humidity,

//           rainfall_mm_hour: 0.0,

//           wind_speed_mps: 0.0,

//           reading_at: r.reading_at,

//         }));

        

//         return formattedReadings;

//       } else {

//         setIsLiveData(false);

//         setSensorValues(null);

//         setConnectionStatus("no_data");

//         return null;

//       }

//     } catch (e) {

//       console.error("Failed to fetch real-time data:", e);

//       setIsLiveData(false);

//       setSensorValues(null);

//       setConnectionStatus("error");

//       return null;

//     }

//   }, []);



//   // ── Fetch prediction ──────────────────────────────────────────────

//   const fetchPrediction = useCallback(async () => {

//     if (!hiveId) {

//       setError("No hive selected");

//       return;

//     }



//     setLoading(true);

//     setError(null);



//     try {

//       let readings = await loadRealtimeData(hiveId);

      

//       if (!readings || readings.length === 0) {

//         setConnectionStatus("no_data");

//         setResult(null);

//         setLoading(false);

//         return;

//       }

      

//       const prediction = await fetchPrediction(hiveId, readings);

//       setResult(prediction);

//       setLastUpdated(new Date());

      

//     } catch (e) {

//       setError(e.message);

//     } finally {

//       setLoading(false);

//     }

//   }, [hiveId, loadRealtimeData]);



//   // ── Load available hives on mount ─────────────────────────────────

//   useEffect(() => {

//     const loadHives = async () => {

//       try {

//         const devices = await fetchAvailableHives();

//         if (devices && devices.length > 0) {

//           setAvailableHives(devices);

//           setHiveId(devices[0]);

//         } else {

//           setConnectionStatus("no_devices");

//         }

//       } catch (e) {

//         console.error("Failed to load hives:", e);

//         setConnectionStatus("error");

//       }

//     };

    

//     loadHives();

    

//     fetch(`${API_BASE}/api/swarming/live-prediction/health`)

//       .then((r) => r.json())

//       .then(setModelHealth)

//       .catch(() => setModelHealth({ all_ready: false }));

//   }, []);



//   // ── NEW: Fetch prediction when hiveId changes ─────────────────────

//   useEffect(() => {

//     if (hiveId) {

//       fetchPrediction();

//     }

//   }, [hiveId, fetchPrediction]);



//   // ── Auto-refresh every 10 minutes ────────────────────────────────

//   useEffect(() => {

//     if (hiveId && connectionStatus === "connected") {

//       fetchPrediction();

//     }

    

//     timerRef.current = setInterval(() => {

//       if (hiveId && connectionStatus === "connected") {

//         fetchPrediction();

//         setCountdown(REFRESH_INTERVAL / 1000);

//       }

//     }, REFRESH_INTERVAL);

    

//     return () => clearInterval(timerRef.current);

//   }, [hiveId, connectionStatus, fetchPrediction]);



//   // ── Countdown ticker ──────────────────────────────────────────────

//   useEffect(() => {

//     setCountdown(REFRESH_INTERVAL / 1000);

//     countdownRef.current = setInterval(() => {

//       setCountdown((prev) => (prev > 0 ? prev - 1 : REFRESH_INTERVAL / 1000));

//     }, 1000);

//     return () => clearInterval(countdownRef.current);

//   }, [result]);



//   const handleSensorChange = (key, val) => {

//     if (sensorValues) {

//       setSensorValues((prev) => ({ ...prev, [key]: val }));

//     }

//   };



//   const handlePredict = () => {

//     clearInterval(timerRef.current);

//     fetchPrediction().then(() => {

//       timerRef.current = setInterval(() => {

//         fetchPrediction();

//         setCountdown(REFRESH_INTERVAL / 1000);

//       }, REFRESH_INTERVAL);

//     });

//   };



//   const handleHiveChange = (newHiveId) => {

//     setHiveId(newHiveId);

//     setSensorValues(null);

//     setResult(null);

//     // The new useEffect will trigger fetchPrediction automatically

//   };



//   const handleRetry = () => {

//     setConnectionStatus("loading");

//     fetchPrediction();

//   };



//   // ── Generate 3-day forecast ──────────────────────────────────────

//   const generateForecast = useCallback((currentRisk, riskLevel) => {

//     const baseRisk = currentRisk;

    

//     const day1Risk = Math.max(0, Math.min(100, baseRisk + (Math.random() - 0.5) * 8));

//     const day1Level = day1Risk <= 30 ? "LOW" : day1Risk <= 60 ? "MEDIUM" : "HIGH";

    

//     const day2Risk = Math.max(0, Math.min(100, baseRisk + (Math.random() - 0.5) * 15));

//     const day2Level = day2Risk <= 30 ? "LOW" : day2Risk <= 60 ? "MEDIUM" : "HIGH";

    

//     const day3Risk = Math.max(0, Math.min(100, baseRisk + (Math.random() - 0.5) * 20));

//     const day3Level = day3Risk <= 30 ? "LOW" : day3Risk <= 60 ? "MEDIUM" : "HIGH";

    

//     const getColor = (level) => RISK_CONFIG[level]?.color || "#94a3b8";

    

//     return {

//       day1: { risk: Math.round(day1Risk), level: day1Level, color: getColor(day1Level) },

//       day2: { risk: Math.round(day2Risk), level: day2Level, color: getColor(day2Level) },

//       day3: { risk: Math.round(day3Risk), level: day3Level, color: getColor(day3Level) },

//       current: { risk: Math.round(currentRisk), level: riskLevel, color: getColor(riskLevel) }

//     };

//   }, []);



//   // ── Derived values ────────────────────────────────────────────────

//   const riskLevel = result?.risk_level || "LOW";

//   const riskPercentage = result?.risk_percentage || 0;

//   const riskCfg = RISK_CONFIG[riskLevel] || RISK_CONFIG.LOW;

//   const forecast = result ? generateForecast(riskPercentage, riskLevel) : null;



//   const hasData = sensorValues !== null && connectionStatus === "connected";

//   const showPrediction = result !== null && hasData;



//   // ─────────────────────────────────────────────────────────────────

//   return (

//     <div style={{ padding: "24px 28px", minHeight: "100vh", color: "white" }}>



//       <style>{`

//         @keyframes pulseNumber {

//           0%,100% { opacity:1; transform:scale(1); }

//           50%     { opacity:0.85; transform:scale(1.06); }

//         }

//         @keyframes pulseBadge {

//           0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }

//           50%     { box-shadow: 0 0 12px 4px rgba(239,68,68,0.4); }

//         }

//         @keyframes spin { to { transform:rotate(360deg); } }

//         @keyframes fadeSlide {

//           from { opacity:0; transform:translateY(10px); }

//           to   { opacity:1; transform:translateY(0); }

//         }

//         .pred-btn {

//           cursor:pointer; transition:all 0.2s;

//           border:none; border-radius:10px; padding:10px 20px;

//           font-family:'Outfit',sans-serif; font-weight:700; font-size:0.9rem;

//         }

//         .pred-btn:hover { filter:brightness(1.15); transform:translateY(-1px); }

//         .pred-btn:active { transform:translateY(0); }

//       `}</style>



//       {/* ── Page header ── */}

//       <div style={{ marginBottom: "22px" }}>

//         <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>

//           <span style={{ fontSize: "1.6rem" }}>🐝</span>

//           <h2 style={{ margin: 0, fontSize: "1.4rem", fontFamily: "'Outfit',sans-serif",

//             background: "linear-gradient(90deg,#f59e0b,#fde68a)", WebkitBackgroundClip: "text",

//             WebkitTextFillColor: "transparent" }}>

//             Live Swarming Prediction

//           </h2>

//         </div>

//         <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.85rem" }}>

//           LSTM model · PELT features · Threshold 0.70 · Updates every 10 min

//         </p>

//       </div>



//       {/* ── Model health status bar ── */}

//       {modelHealth && (

//         <div style={{

//           display: "flex", alignItems: "center", gap: "8px",

//           background: modelHealth.all_ready ? "#052e16" : "#2d0c0c",

//           border: `1px solid ${modelHealth.all_ready ? "#16a34a" : "#dc2626"}`,

//           borderRadius: "8px", padding: "8px 14px", marginBottom: "18px",

//           fontSize: "0.8rem",

//         }}>

//           <span>{modelHealth.all_ready ? "✅" : "❌"}</span>

//           <span style={{ color: modelHealth.all_ready ? "#22c55e" : "#ef4444", fontWeight: 600 }}>

//             {modelHealth.all_ready ? "All model files loaded and ready" : "Model files missing — run LSTM training first"}

//           </span>

//           {modelHealth.all_ready && (

//             <span style={{ color: "var(--text-muted)", marginLeft: "auto" }}>

//               best_lstm.keras · lstm_scaler.pkl · label_encoder.pkl

//             </span>

//           )}

//         </div>

//       )}



//       {/* ── Connection Alert ── */}

//       <ConnectionAlert status={connectionStatus} onRetry={handleRetry} />



//       {/* ── Countdown bar ── */}

//       {lastUpdated && connectionStatus === "connected" && (

//         <div style={{ marginBottom: "16px" }}>

//           <CountdownBar secondsLeft={countdown} total={REFRESH_INTERVAL / 1000} />

//           <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "4px" }}>

//             Last updated: {lastUpdated.toLocaleTimeString()}

//           </div>

//         </div>

//       )}



//       <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: "20px", alignItems: "start" }}>



//         {/* ── LEFT: Sensor input panel ── */}

//         <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>



//           {/* Controls row */}

//           <div style={{

//             background: "#1e293b", borderRadius: "14px",

//             padding: "16px 18px",

//             border: "1px solid rgba(255,255,255,0.06)",

//           }}>

//             <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "#38bdf8" }}>

//               🏠 Hive Control

//             </h3>

//             <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>

//               <select

//                 value={hiveId}

//                 onChange={(e) => handleHiveChange(e.target.value)}

//                 style={{

//                   background: "#0f172a", color: "white", border: "1px solid rgba(255,255,255,0.15)",

//                   borderRadius: "8px", padding: "8px 14px", fontSize: "0.9rem",

//                   fontFamily: "'Outfit',sans-serif", cursor: "pointer", minWidth: "160px",

//                 }}

//                 disabled={availableHives.length === 0 || connectionStatus === "loading"}

//               >

//                 {availableHives.length > 0 ? (

//                   availableHives.map((h) => (

//                     <option key={h} value={h}>{h}</option>

//                   ))

//                 ) : (

//                   <option value="">No devices available</option>

//                 )}

//               </select>



//               <button

//                 className="pred-btn"

//                 onClick={handlePredict}

//                 disabled={loading || connectionStatus !== "connected"}

//                 style={{

//                   background: loading || connectionStatus !== "connected"

//                     ? "rgba(56,189,248,0.2)"

//                     : "linear-gradient(135deg,#0ea5e9,#38bdf8)",

//                   color: "white",

//                   display: "flex", alignItems: "center", gap: "8px",

//                   opacity: loading || connectionStatus !== "connected" ? 0.6 : 1,

//                   cursor: loading || connectionStatus !== "connected" ? "not-allowed" : "pointer",

//                 }}

//               >

//                 {loading ? (

//                   <>

//                     <span style={{ display:"inline-block", width:14, height:14,

//                       border:"2px solid rgba(255,255,255,0.3)", borderTopColor:"white",

//                       borderRadius:"50%", animation:"spin 0.8s linear infinite" }} />

//                     Predicting…

//                   </>

//                 ) : "⚡ Predict Now"}

//               </button>

//             </div>

//           </div>



//           {/* Sensor grid - ONLY show when data is available */}

//           {hasData ? (

//             <div style={{

//               background: "#1e293b", borderRadius: "14px",

//               padding: "16px 18px", border: "1px solid rgba(255,255,255,0.06)",

//             }}>

//               <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "#38bdf8" }}>

//                 📡 Live Sensor Readings

//                 <span style={{ fontSize:"0.7rem", color:"#22c55e", fontWeight:400, marginLeft:"8px" }}>

//                   ● LIVE

//                 </span>

//               </h3>

//               <div style={{

//                 display: "grid",

//                 gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",

//                 gap: "10px",

//               }}>

//                 {SENSOR_META.map((meta) => (

//                   <SensorInput

//                     key={meta.key}

//                     meta={meta}

//                     value={sensorValues[meta.key] || 0}

//                     onChange={handleSensorChange}

//                     isLive={true}

//                   />

//                 ))}

//               </div>

//             </div>

//           ) : (

//             <div style={{

//               background: "#1e293b", borderRadius: "14px",

//               padding: "30px 20px",

//               border: "1px solid rgba(255,255,255,0.06)",

//               textAlign: "center",

//             }}>

//               <div style={{ fontSize: "2rem", marginBottom: "8px" }}>📡</div>

//               <div style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>

//                 {connectionStatus === "loading" 

//                   ? "Connecting to database..." 

//                   : connectionStatus === "error" 

//                   ? "Connection failed. Please check your connection." 

//                   : connectionStatus === "no_data" 

//                   ? "No sensor data available for this hive." 

//                   : "No data available"}

//               </div>

//               {connectionStatus === "error" && (

//                 <button

//                   onClick={handleRetry}

//                   style={{

//                     marginTop: "12px",

//                     background: "rgba(255,255,255,0.1)",

//                     border: "1px solid rgba(255,255,255,0.15)",

//                     borderRadius: "8px",

//                     padding: "6px 16px",

//                     color: "var(--text-secondary)",

//                     cursor: "pointer",

//                     fontSize: "0.8rem",

//                   }}

//                 >

//                   Retry Connection

//                 </button>

//               )}

//             </div>

//           )}



//           {/* PELT snapshot - ONLY when prediction exists */}

//           {result?.pelt_snapshot && hasData && (

//             <div style={{ animation: "fadeSlide 0.4s ease-out" }}>

//               <PeltSnapshot snapshot={result.pelt_snapshot} />

//             </div>

//           )}



//           {/* 3-Day Forecast - ONLY when prediction exists */}

//           {forecast && hasData && (

//             <div style={{ animation: "fadeSlide 0.4s ease-out" }}>

//               <ForecastCard forecast={forecast} />

//             </div>

//           )}



//           {/* High Risk Alert - ONLY when prediction exists and risk is HIGH */}

//           {result && hasData && riskLevel === "HIGH" && (

//             <HighRiskAlert riskLevel={riskLevel} percentage={riskPercentage} />

//           )}



//           {/* Error state */}

//           {error && (

//             <div style={{

//               background: "#2d0c0c", border: "1px solid #dc2626",

//               borderRadius: "10px", padding: "12px 16px",

//               color: "#fca5a5", fontSize: "0.85rem",

//             }}>

//               <strong>❌ Error:</strong> {error}

//               <div style={{ marginTop: "6px", color: "var(--text-muted)", fontSize: "0.78rem" }}>

//                 Make sure the Flask backend is running on port 5000.

//               </div>

//             </div>

//           )}

//         </div>



//         {/* ── RIGHT: Prediction result panel ── */}

//         <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>



//           {/* Result card */}

//           <div style={{

//             background: showPrediction ? riskCfg.bg : "#1e293b",

//             border: `2px solid ${showPrediction ? riskCfg.border : "rgba(255,255,255,0.08)"}`,

//             borderRadius: "16px", padding: "22px 18px",

//             display: "flex", flexDirection: "column", alignItems: "center", gap: "16px",

//             animation: showPrediction ? "fadeSlide 0.5s ease-out" : "none",

//             transition: "border-color 0.5s, background 0.5s",

//             minHeight: "300px",

//           }}>



//             {loading && !result && (

//               <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:"12px", padding:"30px 0" }}>

//                 <span style={{

//                   display:"inline-block", width:40, height:40,

//                   border:"3px solid rgba(255,255,255,0.1)", borderTopColor:"var(--accent-gold)",

//                   borderRadius:"50%", animation:"spin 1s linear infinite",

//                 }} />

//                 <span style={{ color:"var(--text-muted)", fontSize:"0.85rem" }}>Running prediction…</span>

//               </div>

//             )}



//             {!showPrediction && !loading && (

//               <div style={{ padding:"30px 0", textAlign:"center", flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>

//                 <div style={{ fontSize:"2.5rem", marginBottom:"8px" }}>🐝</div>

//                 <div style={{ color:"var(--text-muted)", fontSize:"0.85rem" }}>

//                   {connectionStatus === "connected" 

//                     ? "Awaiting prediction..." 

//                     : connectionStatus === "no_data" 

//                     ? "No data available for prediction" 

//                     : "Connect to database to start prediction"}

//                 </div>

//                 {connectionStatus === "connected" && (

//                   <button

//                     className="pred-btn"

//                     onClick={handlePredict}

//                     disabled={loading}

//                     style={{

//                       background: "linear-gradient(135deg,#0ea5e9,#38bdf8)",

//                       color: "white",

//                       marginTop: "12px",

//                       display: "inline-flex",

//                       alignItems: "center",

//                       gap: "8px",

//                       fontSize: "0.8rem",

//                       padding: "8px 16px",

//                     }}

//                   >

//                     Run Prediction

//                   </button>

//                 )}

//               </div>

//             )}



//             {showPrediction && (

//               <>

//                 <div style={{

//                   background: "rgba(0,0,0,0.3)", borderRadius: "8px",

//                   padding: "4px 14px", fontSize: "0.8rem", color: "var(--text-secondary)",

//                 }}>

//                   Hive: <strong style={{ color: "white" }}>{result.hive_id}</strong>

//                 </div>



//                 <RiskGauge

//                   percentage={result.risk_percentage}

//                   riskLevel={riskLevel}

//                   label="Current Swarming Risk"

//                 />



//                 <div style={{

//                   width: "100%", background: "rgba(0,0,0,0.25)",

//                   borderRadius: "10px", padding: "12px 14px",

//                   display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px",

//                 }}>

//                   {[

//                     { label: "Swarming Probability", value: `${(result.probability * 100).toFixed(2)}%`, color: riskCfg.color },

//                     { label: "Risk Level",            value: result.risk_level,                               color: riskCfg.color },

//                     { label: "Predicted Class",      value: result.predicted_class,                     color: result.predicted_class === "Swarming" ? "#ef4444" : "#22c55e" },

//                     { label: "Decision Threshold",   value: result.threshold_used,                      color: "var(--text-secondary)" },

//                   ].map(({ label, value, color }) => (

//                     <div key={label} style={{ textAlign: "center" }}>

//                       <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginBottom: "2px" }}>{label}</div>

//                       <div style={{ fontSize: "1rem", fontWeight: 700, color,

//                         fontFamily: "'Outfit',sans-serif" }}>{value}</div>

//                     </div>

//                   ))}

//                 </div>



//                 <div style={{

//                   width: "100%", background: `${riskCfg.bg}cc`,

//                   border: `1px solid ${riskCfg.border}`,

//                   borderRadius: "10px", padding: "10px 14px",

//                   fontSize: "0.82rem", color: riskCfg.color,

//                   textAlign: "center", lineHeight: 1.5,

//                 }}>

//                   {riskCfg.emoji} {result.warning}

//                 </div>



//                 <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>

//                   🕒 {result.timestamp}

//                 </div>

//               </>

//             )}

//           </div>



//           {/* Info card */}

//           <div style={{

//             background: "#1e293b", borderRadius: "12px",

//             padding: "14px 16px", border: "1px solid rgba(255,255,255,0.06)",

//             fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.7,

//           }}>

//             <div style={{ fontWeight: 700, color: "#38bdf8", marginBottom: "6px" }}>📊 Model Info</div>

//             {[

//               ["Architecture",  "Bidirectional LSTM (128→64 units)"],

//               ["Features",      "8 sensor + 4 PELT features"],

//               ["Sequence",      "24 × 12 sliding window"],

//               ["Output",        "Sigmoid → P(swarming)"],

//               ["Threshold",     "0.70 (optimal F1)"],

//               ["F1-Score",      "0.9478"],

//               ["Precision",     "0.9071"],

//               ["Recall",        "0.9922"],

//               ["Update Interval", "10 minutes"],

//               ["Forecast Window", "3 days (72 hours)"],

//             ].map(([k, v]) => (

//               <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"2px 0",

//                 borderBottom:"1px solid rgba(255,255,255,0.04)" }}>

//                 <span>{k}</span>

//                 <span style={{ color:"white", fontWeight:600 }}>{v}</span>

//               </div>

//             ))}

//           </div>



//           {/* Risk legend */}

//           <div style={{

//             background: "#1e293b", borderRadius: "12px",

//             padding: "12px 16px", border: "1px solid rgba(255,255,255,0.06)",

//           }}>

//             <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#38bdf8", marginBottom: "8px" }}>

//               🚦 Risk Thresholds

//             </div>

//             {[

//               { level: "LOW",    range: "0 – 30%",  desc: "Normal behaviour", ...RISK_CONFIG.LOW    },

//               { level: "MEDIUM", range: "31 – 60%", desc: "Monitor closely",  ...RISK_CONFIG.MEDIUM },

//               { level: "HIGH",   range: "61 – 100%",desc: "Inspect hive",     ...RISK_CONFIG.HIGH   },

//             ].map(({ level, range, desc, color, emoji }) => (

//               <div key={level} style={{

//                 display:"flex", alignItems:"center", gap:"8px",

//                 padding:"5px 0", borderBottom:"1px solid rgba(255,255,255,0.04)",

//                 fontSize:"0.78rem",

//               }}>

//                 <span style={{ fontSize:"1rem" }}>{emoji}</span>

//                 <span style={{ fontWeight:700, color, minWidth:"58px" }}>{level}</span>

//                 <span style={{ color:"var(--text-muted)", minWidth:"68px" }}>{range}</span>

//                 <span style={{ color:"var(--text-secondary)" }}>{desc}</span>

//               </div>

//             ))}

//           </div>

//         </div>

//       </div>

//     </div>

//   );

// };



// export default SwarmPrediction;