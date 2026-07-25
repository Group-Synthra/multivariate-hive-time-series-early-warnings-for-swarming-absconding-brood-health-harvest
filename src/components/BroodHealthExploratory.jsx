import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Droplets,
  Heart,
  Info,
  Minus,
  Scale,
  Shield,
  Thermometer,
  TrendingDown,
  TrendingUp,
  Wind,
} from "lucide-react";
import { useBroodHealthData } from "../hooks/useBroodHealthData";
import {
  ApiaryBarChart,
  HealthTimelineChart,
  RodTrendChart,
} from "./BroodHealthCharts";
import {
  getTotalWindows,
  getWindowData,
  getWindowDescription,
} from "../utils/broodHealthHelpers";
import {
  HEALTH_COLORS,
  HEALTH_LEVELS,
  STABILITY_COLORS,
} from "../utils/broodHealthConstants";

const TREND_ICONS = {
  "Rapid Improving": <TrendingUp size={16} color="#10b981" />,
  "Slow Improving": <TrendingUp size={16} color="#34d399" />,
  Stable: <Minus size={16} color="#6b7280" />,
  "Slow Declining": <TrendingDown size={16} color="#f59e0b" />,
  "Rapid Declining": <TrendingDown size={16} color="#ef4444" />,
};

const SENSOR_CARDS = [
  {
    key: "temp",
    label: "Internal Temperature",
    unit: "°C",
    decimals: 2,
    icon: Thermometer,
    accent: "var(--accent-crimson)",
  },
  {
    key: "humidity",
    label: "Internal Humidity",
    unit: "% RH",
    decimals: 2,
    icon: Droplets,
    accent: "var(--accent-cyan)",
  },
  {
    key: "co2",
    label: "CO₂ Concentration",
    unit: "ppm",
    decimals: 0,
    icon: Wind,
    accent: "var(--accent-gold)",
  },
  {
    key: "weight",
    label: "Hive Weight",
    unit: "kg",
    decimals: 3,
    icon: Scale,
    accent: "var(--accent-emerald)",
  },
];

function formatValue(value, decimals) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(decimals) : "—";
}

function formatTimestamp(value) {
  if (!value) return "Timestamp unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleString();
}

export default function BroodHealthExploratory() {
  const [selectedHive, setSelectedHive] = useState(null);
  const { data, loading, error } = useBroodHealthData({ hive: selectedHive });
  const [showExplanation, setShowExplanation] = useState(false);
  const [windowSize, setWindowSize] = useState(200);
  const [windowNumber, setWindowNumber] = useState(0);

  const metrics = data?.metrics || [];
  const summary = data?.summary || [];
  const scoreLevels = useMemo(() => {
    if (!Array.isArray(data?.healthLevels) || data.healthLevels.length === 0) {
      return HEALTH_LEVELS;
    }
    return data.healthLevels
      .slice()
      .sort((a, b) => Number(b.minimum) - Number(a.minimum))
      .map((level) => {
        const fallback = HEALTH_LEVELS.find(
          (item) => item.level === level.level,
        );
        return {
          level: level.level,
          displayRange: level.display_range,
          rule: level.rule,
          color: HEALTH_COLORS[level.level],
          description: fallback?.description || "",
        };
      });
  }, [data?.healthLevels]);

  const hives = useMemo(() => summary.map((record) => record.hive), [summary]);
  const currentHive = selectedHive || data?.defaultHive || hives[0] || null;

  useEffect(() => {
    if (selectedHive && !hives.includes(selectedHive)) {
      setSelectedHive(null);
      setWindowNumber(0);
    }
  }, [hives, selectedHive]);

  const fullHiveMetrics = useMemo(
    () =>
      metrics
        .filter((record) => record.hive === currentHive)
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)),
    [metrics, currentHive],
  );

  // These cards always show the latest available record for the selected hive.
  const currentRecord =
    fullHiveMetrics.length > 0
      ? fullHiveMetrics[fullHiveMetrics.length - 1]
      : null;

  const totalRecords = fullHiveMetrics.length;
  const totalWindows = getTotalWindows(totalRecords, windowSize);

  useEffect(() => {
    if (totalWindows > 0 && windowNumber >= totalWindows) {
      setWindowNumber(totalWindows - 1);
    }
  }, [totalWindows, windowNumber]);

  const windowData = useMemo(
    () => getWindowData(fullHiveMetrics, windowNumber, windowSize),
    [fullHiveMetrics, windowNumber, windowSize],
  );

  const windowDescription = getWindowDescription(
    fullHiveMetrics,
    windowNumber,
    windowSize,
  );

  const barData = useMemo(
    () =>
      summary
        .map((record) => ({
          hive: record.hive,
          score: Number(record.current_score),
          health: record.health_level,
        }))
        .filter((record) => Number.isFinite(record.score))
        .sort((a, b) => b.score - a.score),
    [summary],
  );

  const handlePreviousWindow = () => {
    if (windowNumber + 1 < totalWindows) {
      setWindowNumber((value) => value + 1);
    }
  };

  const handleNextWindow = () => {
    if (windowNumber > 0) {
      setWindowNumber((value) => value - 1);
    }
  };

  if (loading)
    return <div className="loader">Loading brood health analytics...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!data) return null;
  if (!currentHive || !currentRecord) {
    return (
      <div className="card">No usable brood-health records were found.</div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div className="dashboard-grid">
        <div
          className="card welcome-card"
          style={{ borderLeft: "4px solid var(--accent-emerald)" }}
        >
          <div className="welcome-content">
            <div className="welcome-text">
              <h2>🐝 Brood Health Status Prediction</h2>
              <p>
                Exploratory current-condition indices and stability trends; not
                a substitute for independently observed brood-health ground
                truth.
              </p>
            </div>
            <Heart size={48} color="var(--accent-emerald)" />
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: "0.75rem 1.25rem" }}>
        <div
          style={{
            display: "flex",
            gap: "1rem",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontWeight: 600 }}>Select Hive:</span>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {hives.map((hive) => (
              <button
                type="button"
                key={hive}
                onClick={() => {
                  setSelectedHive(hive);
                  setWindowNumber(0);
                }}
                className={`badge ${currentHive === hive ? "active" : ""}`}
                style={{
                  padding: "0.3rem 0.9rem",
                  background:
                    currentHive === hive
                      ? "var(--accent-emerald)"
                      : "rgba(255,255,255,0.05)",
                  color:
                    currentHive === hive ? "#0f172a" : "var(--text-secondary)",
                  border: "none",
                  borderRadius: "20px",
                  cursor: "pointer",
                }}
              >
                {String(hive).toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      <section>
        <div className="chart-header" style={{ marginBottom: "0.75rem" }}>
          <div>
            <h3 style={{ marginBottom: "0.2rem" }}>
              Latest Input Variables — {String(currentHive).toUpperCase()}
            </h3>
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>
              Latest sensor timestamp:{" "}
              {formatTimestamp(currentRecord.timestamp)}
            </p>
          </div>
        </div>
        <div className="dashboard-grid">
          {SENSOR_CARDS.map(
            ({ key, label, unit, decimals, icon: Icon, accent }) => (
              <div
                className="card"
                key={key}
                style={{ borderTop: `3px solid ${accent}` }}
              >
                <div className="stat-header">
                  <span>{label}</span>
                  <Icon size={18} color={accent} />
                </div>
                <div className="stat-value">
                  {formatValue(currentRecord[key], decimals)}
                  <span className="stat-unit">{unit}</span>
                </div>
                <div className="stat-footer">
                  Input used by the brood-health module
                </div>
              </div>
            ),
          )}
        </div>
      </section>

      <section>
        <div className="chart-header" style={{ marginBottom: "0.75rem" }}>
          <h3>Current Brood-Health Indicators</h3>
        </div>
        <div className="dashboard-grid">
          <div
            className="card"
            style={{
              background: `linear-gradient(135deg, ${HEALTH_COLORS[currentRecord.health_level]}20, transparent)`,
            }}
          >
            <div className="stat-header">
              <span>Brood Health Score</span>
              <Shield size={16} />
            </div>
            <div
              className="stat-value"
              style={{ color: HEALTH_COLORS[currentRecord.health_level] }}
            >
              {formatValue(currentRecord.brood_health_score, 2)}
            </div>
            <div className="stat-footer">{currentRecord.health_level}</div>
          </div>
          <div className="card">
            <div className="stat-header">
              <span>BHSI (Stability)</span>
              <Activity size={16} />
            </div>
            <div
              className="stat-value"
              style={{ color: STABILITY_COLORS[currentRecord.stability_level] }}
            >
              {formatValue(currentRecord.bhsi, 2)}
            </div>
            <div className="stat-footer">
              {currentRecord.stability_level} Stability
            </div>
          </div>
          <div className="card">
            <div className="stat-header">
              <span>Rate of Deterioration</span>
              {TREND_ICONS[currentRecord.trend_label] || <Minus size={16} />}
            </div>
            <div className="stat-value">
              {formatValue(currentRecord.rod, 1)}
              <span className="stat-unit">pts/hr</span>
            </div>
            <div className="stat-footer">{currentRecord.trend_label}</div>
          </div>
        </div>
      </section>

      <div className="card" style={{ padding: "1rem" }}>
        <div className="chart-header" style={{ marginBottom: "0.75rem" }}>
          <div>
            <h3>📊 Brood Health Score — Non-overlapping Ranges</h3>
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>
              Boundary example: a score of 40.00 belongs to Poor, 60.00 belongs
              to Good, and 80.00 belongs to Excellent.
            </p>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "1rem",
            justifyContent: "space-between",
          }}
        >
          {scoreLevels.map((item) => (
            <div
              key={item.level}
              style={{
                flex: 1,
                minWidth: "190px",
                background: `${item.color}10`,
                borderRadius: "8px",
                padding: "0.75rem",
                borderLeft: `4px solid ${item.color}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "0.75rem",
                }}
              >
                <strong style={{ color: item.color }}>{item.level}</strong>
                <span>{item.displayRange}</span>
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  marginTop: "0.35rem",
                }}
              >
                {item.rule}
              </div>
              <p
                style={{
                  fontSize: "0.75rem",
                  margin: "0.35rem 0 0",
                  color: "var(--text-secondary)",
                }}
              >
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      <section>
        <div className="chart-header" style={{ marginBottom: "0.75rem" }}>
          <h3>Historical Window Analytics</h3>
        </div>
        <div
          className="card"
          style={{
            padding: "0.5rem 1rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "0.5rem",
          }}
        >
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button
              type="button"
              onClick={handlePreviousWindow}
              disabled={windowNumber + 1 >= totalWindows}
              style={{
                background: "#2d3748",
                border: "none",
                padding: "0.4rem 0.8rem",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              <ChevronLeft size={18} />
            </button>
            <span style={{ fontSize: "0.85rem", fontFamily: "monospace" }}>
              {windowDescription}
            </span>
            <button
              type="button"
              onClick={handleNextWindow}
              disabled={windowNumber === 0}
              style={{
                background: "#2d3748",
                border: "none",
                padding: "0.4rem 0.8rem",
                borderRadius: "6px",
                cursor: "pointer",
              }}
            >
              <ChevronRight size={18} />
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.8rem" }}>Window size:</span>
            <select
              value={windowSize}
              onChange={(event) => {
                setWindowSize(Number(event.target.value));
                setWindowNumber(0);
              }}
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                padding: "0.2rem 0.5rem",
                borderRadius: "4px",
              }}
            >
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
              <option value={1000}>1000</option>
            </select>
          </div>
        </div>
      </section>

      <HealthTimelineChart data={windowData} />
      <div className="dashboard-grid">
        <RodTrendChart data={windowData} />
        <ApiaryBarChart data={barData} colors={HEALTH_COLORS} />
      </div>

      <div className="card" style={{ padding: 0 }}>
        <button
          type="button"
          onClick={() => setShowExplanation((value) => !value)}
          style={{
            width: "100%",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "1rem",
            background: "rgba(255,255,255,0.02)",
            border: "none",
            cursor: "pointer",
            fontSize: "1rem",
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          <span>
            <Info
              size={18}
              style={{ marginRight: "0.5rem", verticalAlign: "middle" }}
            />
            How are these scores calculated?
          </span>
          {showExplanation ? (
            <ChevronUp size={18} />
          ) : (
            <ChevronDown size={18} />
          )}
        </button>

        {showExplanation && (
          <div
            style={{
              padding: "1rem",
              borderTop: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            <div style={{ marginBottom: "1rem" }}>
              <h4 style={{ color: "var(--accent-emerald)" }}>
                🐝 Brood Health Score (0-100)
              </h4>
              <p>
                <strong>What it measures:</strong> how close the hive's current
                readings are to that hive's own recent baseline.
              </p>
              <ul
                style={{
                  marginLeft: "1.25rem",
                  color: "var(--text-secondary)",
                }}
              >
                <li>
                  Temperature, humidity, CO₂ and weight are compared with a
                  past-only seven-day baseline.
                </li>
                <li>
                  A z-score measures how unusual each current value is relative
                  to that baseline.
                </li>
                <li>
                  Directional penalties reduce the sub-score for cold
                  temperature, high CO₂ and weight loss.
                </li>
                <li>
                  The provisional research-prior coefficients are 40%
                  temperature, 25% humidity, 20% CO₂ and 15% weight.
                </li>
                <li>
                  These coefficients are initial hypotheses and must be
                  validated against independent brood observations.
                </li>
              </ul>
              <p style={{ color: "var(--text-secondary)" }}>
                Classes use exact decimal rules: Critical is below 40; Poor
                starts at 40; Good starts at 60; Excellent starts at 80.
              </p>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <h4 style={{ color: "var(--accent-cyan)" }}>
                📊 Brood Health Stability Index (BHSI)
              </h4>
              <p>
                <strong>What it measures:</strong> environmental consistency
                during the latest six-hour window. The index uses the average
                coefficient of variation for temperature, humidity and CO₂.
                Temperature is converted to Kelvin before its coefficient of
                variation is calculated.
              </p>
            </div>

            <div>
              <h4 style={{ color: "var(--accent-crimson)" }}>
                ⏱️ Rate of Deterioration (RoD)
              </h4>
              <p>
                <strong>What it measures:</strong> the linear slope of the
                health score over the previous four hours, in points per hour.
                Negative values indicate decline.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
