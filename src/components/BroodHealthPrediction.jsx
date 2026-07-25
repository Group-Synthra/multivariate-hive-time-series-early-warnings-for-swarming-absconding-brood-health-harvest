import React, { useEffect, useMemo, useState } from "react";
import {
  Battery,
  Clock3,
  Database,
  Droplets,
  Loader,
  RefreshCw,
  Scale,
  Thermometer,
  Wifi,
  WifiOff,
  Wind,
  Zap,
} from "lucide-react";
import {
  LIVE_REFRESH_MS,
  useBroodHealthIoTData,
} from "../hooks/useBroodHealthData";
import { LiveEarlyWarningTimeline } from "./BroodHealthCharts";
import {
  BHSIVisual,
  BroodHealthGauge,
  EarlyWarningPanel,
  RoDVisual,
} from "./BroodHealthLiveGauges";

const LIVE_HISTORY_HOURS = 168;
const TIMELINE_POINTS = 144;

const SENSOR_CARDS = [
  {
    key: "internal_temperature_c",
    label: "Internal Temperature",
    unit: "°C",
    decimals: 2,
    Icon: Thermometer,
    role: "Model input",
  },
  {
    key: "internal_humidity_pct",
    label: "Internal Humidity",
    unit: "% RH",
    decimals: 2,
    Icon: Droplets,
    role: "Model input",
  },
  {
    key: "internal_co2_ppm",
    label: "Internal CO₂",
    unit: "ppm",
    decimals: 0,
    Icon: Wind,
    role: "Model input",
  },
  {
    key: "hive_weight_kg",
    label: "Total Hive Weight",
    unit: "kg",
    decimals: 3,
    Icon: Scale,
    role: "Model input",
  },
  {
    key: "external_temperature_c",
    label: "External Temperature",
    unit: "°C",
    decimals: 2,
    Icon: Thermometer,
    role: "External context input",
  },
  {
    key: "external_humidity_pct",
    label: "External Humidity",
    unit: "% RH",
    decimals: 2,
    Icon: Droplets,
    role: "External context input",
  },
];

function formatNumber(value, decimals = 2) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(decimals) : "—";
}

function formatDateTime(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? String(value)
    : parsed.toLocaleString();
}

function formatCountdown(milliseconds) {
  const seconds = Math.max(0, Math.ceil(milliseconds / 1000));
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

export default function BroodHealthPrediction() {
  const [selectedHive, setSelectedHive] = useState(null);
  const [now, setNow] = useState(Date.now());

  const { data, loading, loadingDashboard, error, refetch } =
    useBroodHealthIoTData({
      hive: selectedHive,
      historyHours: LIVE_HISTORY_HOURS,
      timelinePoints: TIMELINE_POINTS,
      pollIntervalMs: LIVE_REFRESH_MS,
    });

  const hives = data?.hives || [];
  const currentHive = selectedHive || data?.defaultHive || null;
  const dashboard = data?.dashboard || null;
  const databaseStatus = data?.databaseStatus || null;
  const lastRefresh = data?.lastSuccessfulRefresh || null;

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const nextRefreshIn = useMemo(() => {
    if (!lastRefresh) return null;
    return Math.max(0, lastRefresh.getTime() + LIVE_REFRESH_MS - now);
  }, [lastRefresh, now]);

  const latestInputs = dashboard?.latest_inputs || {};
  const timeline = dashboard?.timeline || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div
        className="card"
        style={{ borderLeft: "4px solid var(--accent-gold)" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "1rem",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2 style={{ marginBottom: "0.35rem" }}>
              🐝 Live Brood Health Early Warning
            </h2>
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>
              The selected best model forecasts the future Brood Health Score
              and health status from actual PostgreSQL sensor readings. BHSI and
              RoD provide early warnings before the score reaches Poor or
              Critical conditions.
            </p>
          </div>
          <Zap size={46} color="var(--accent-gold)" />
        </div>
      </div>

      <div
        className="card"
        style={{
          borderLeft: `4px solid ${databaseStatus?.connected ? "var(--accent-emerald)" : "var(--accent-crimson)"}`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            flexWrap: "wrap",
          }}
        >
          {databaseStatus?.connected ? (
            <Wifi size={22} color="var(--accent-emerald)" />
          ) : (
            <WifiOff size={22} color="var(--accent-crimson)" />
          )}
          <div style={{ flex: 1 }}>
            <strong>
              {databaseStatus?.connected
                ? "Live PostgreSQL connection active"
                : "Live PostgreSQL connection unavailable"}
            </strong>
            <p
              style={{
                margin: "0.25rem 0 0",
                color: "var(--text-secondary)",
                fontSize: "0.85rem",
              }}
            >
              {databaseStatus?.connected
                ? `Source: ${databaseStatus.schema}.${databaseStatus.table} · Automatic refresh every 10 minutes`
                : "Check backend/.env, Supabase permissions and network access."}
            </p>
          </div>
          <Database size={22} color="var(--text-secondary)" />
        </div>
      </div>

      {error && (
        <div
          className="card"
          style={{ borderLeft: "4px solid var(--accent-crimson)" }}
        >
          <strong>Live early-warning error:</strong> {error}
        </div>
      )}

      <div className="card" style={{ padding: "0.75rem 1.25rem" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <strong>Select Live Hive:</strong>
          <div
            style={{
              display: "flex",
              gap: "0.5rem",
              flexWrap: "wrap",
              flex: 1,
            }}
          >
            {hives.map((record) => {
              const active = String(record.hive) === String(currentHive);
              return (
                <button
                  type="button"
                  key={record.hive}
                  onClick={() => setSelectedHive(record.hive)}
                  style={{
                    padding: "0.35rem 0.9rem",
                    background: active
                      ? "var(--accent-gold)"
                      : "rgba(255,255,255,0.05)",
                    color: active ? "#0f172a" : "var(--text-secondary)",
                    border: "none",
                    borderRadius: 20,
                    cursor: "pointer",
                  }}
                >
                  {String(record.hive).toUpperCase()}
                </button>
              );
            })}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              color: "var(--text-secondary)",
              fontSize: "0.82rem",
            }}
          >
            <Clock3 size={16} />
            {nextRefreshIn === null
              ? "Waiting for first update"
              : `Next update ${formatCountdown(nextRefreshIn)}`}
          </div>
          <button
            type="button"
            onClick={refetch}
            title="Refresh database readings and prediction now"
            disabled={loadingDashboard}
            style={{
              background: "#2d3748",
              border: "none",
              borderRadius: 7,
              padding: "0.55rem",
              cursor: "pointer",
            }}
          >
            <RefreshCw size={17} className={loadingDashboard ? "spin" : ""} />
          </button>
        </div>
      </div>

      {loading && !dashboard && (
        <div className="card" style={{ textAlign: "center", padding: "2rem" }}>
          <Loader size={34} className="spin" color="var(--accent-cyan)" />
          <p style={{ color: "var(--text-secondary)" }}>
            Reading public.beehive_readings and applying the selected model...
          </p>
        </div>
      )}

      {dashboard && (
        <>
          <EarlyWarningPanel warning={dashboard.early_warning} />

          <div className="dashboard-grid" style={{ alignItems: "stretch" }}>
            <BroodHealthGauge
              score={dashboard.predicted_score}
              healthLevel={dashboard.predicted_health_level}
              forecastHorizonHours={dashboard.forecast_horizon_hours}
            />
            <BHSIVisual
              value={dashboard.bhsi}
              stabilityLevel={dashboard.stability_level}
            />
            <RoDVisual
              value={dashboard.rod}
              trendLabel={dashboard.trend_label}
            />
          </div>

          <div className="card">
            <div className="chart-header">
              <div>
                <h3>Current and Forecast Interpretation</h3>
                <p>
                  Current index uses the latest sensor history; forecast risk
                  comes from {dashboard.model_name}.
                </p>
              </div>
            </div>
            <div className="dashboard-grid">
              <div>
                <strong>Current health score</strong>
                <div className="stat-value">
                  {formatNumber(dashboard.current_score, 1)}
                </div>
                <div className="stat-footer">
                  {dashboard.current_health_level}
                </div>
              </div>
              <div>
                <strong>Predicted future score</strong>
                <div className="stat-value">
                  {formatNumber(dashboard.predicted_score, 1)}
                </div>
                <div className="stat-footer">
                  {dashboard.predicted_health_level} ·{" "}
                  {dashboard.forecast_horizon_hours}h forecast
                </div>
              </div>
              <div>
                <strong>Forecast time</strong>
                <div style={{ marginTop: "0.8rem", fontWeight: 600 }}>
                  {formatDateTime(dashboard.forecast_timestamp)}
                </div>
                <div className="stat-footer">
                  Latest sensor:{" "}
                  {formatDateTime(dashboard.latest_sensor_timestamp)}
                </div>
              </div>
            </div>
          </div>

          <section>
            <div className="chart-header" style={{ marginBottom: "0.75rem" }}>
              <div>
                <h3>Actual Inputs for {String(currentHive).toUpperCase()}</h3>
                <p>
                  All six biological/environmental values are used by the model.
                  Battery voltage is shown only for device health.
                </p>
              </div>
            </div>

            <div className="dashboard-grid">
              {SENSOR_CARDS.map(
                ({ key, label, unit, decimals, Icon, role }) => (
                  <div className="card" key={key}>
                    <div className="stat-header">
                      <span>{label}</span>
                      <Icon size={18} />
                    </div>
                    <div className="stat-value">
                      {formatNumber(latestInputs[key], decimals)}
                      <span className="stat-unit">{unit}</span>
                    </div>
                    <div className="stat-footer">{role}</div>
                  </div>
                ),
              )}
            </div>

            <div className="card" style={{ marginTop: "1rem" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.65rem",
                  flexWrap: "wrap",
                }}
              >
                <Battery size={18} />
                <strong>Device battery:</strong>
                <span style={{ color: "var(--text-secondary)" }}>
                  {formatNumber(latestInputs.battery_voltage, 3)} V — monitored
                  for sensor reliability, not used as a biological predictor.
                </span>
              </div>
            </div>
          </section>

          <LiveEarlyWarningTimeline data={timeline} />

          {(dashboard.domain_shift_warnings || []).length > 0 && (
            <div
              className="card"
              style={{ borderLeft: "4px solid var(--accent-gold)" }}
            >
              <h3 style={{ marginTop: 0 }}>Local Calibration Warnings</h3>
              <ul
                style={{
                  color: "var(--text-secondary)",
                  paddingLeft: "1.2rem",
                }}
              >
                {dashboard.domain_shift_warnings.map((warning) => (
                  <li key={warning.sensor}>{warning.message}</li>
                ))}
              </ul>
            </div>
          )}

          <div
            className="card"
            style={{ color: "var(--text-secondary)", fontSize: "0.84rem" }}
          >
            <strong style={{ color: "var(--text-primary)" }}>
              Data and model trace:
            </strong>{" "}
            {dashboard.raw_database_rows} PostgreSQL rows from the latest{" "}
            {dashboard.requested_history_hours} hours ·{" "}
            {dashboard.hourly_observations_used} hourly model observations ·
            model {dashboard.model_name} · prediction inputs:{" "}
            {(dashboard.model_inputs || []).join(", ")}.
          </div>
        </>
      )}
    </div>
  );
}
