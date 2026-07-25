import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import {
  BarChart3,
  CheckCircle,
  Loader,
  Play,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { BROOD_HEALTH_API_BASE } from "../hooks/useBroodHealthData";

const MODEL_LABELS = [
  "Ridge Regression",
  "XGBoost",
  "Random Forest",
  "Extra Trees",
  "Histogram Gradient Boosting",
  "Dummy Median",
];

function valueOrDash(value, decimals = 3) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(decimals) : "—";
}

export default function BroodHealthTraining() {
  const [status, setStatus] = useState("loading");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [currentStep, setCurrentStep] = useState("");
  const [horizonHours, setHorizonHours] = useState(6);
  const [fastMode, setFastMode] = useState(false);
  const pollingRef = useRef(null);

  function stopPolling() {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }

  async function checkStatus() {
    try {
      const response = await axios.get(
        `${BROOD_HEALTH_API_BASE}/brood_health/train/status`,
      );
      const payload = response.data || {};

      setProgress(Number(payload.progress) || 0);
      setMessage(payload.message || "");
      setCurrentStep(payload.current_step || "");

      if (payload.running) {
        setStatus("running");
        return;
      }

      if (payload.error) {
        setStatus("error");
        setError(payload.error);
        stopPolling();
        return;
      }

      if (payload.result) {
        setStatus("completed");
        setResult(payload.result);
        setProgress(100);
        stopPolling();
        return;
      }

      setStatus("idle");
      stopPolling();
    } catch (requestError) {
      setStatus("error");
      setError(requestError?.response?.data?.error || requestError.message);
      stopPolling();
    }
  }

  function beginPolling() {
    stopPolling();
    pollingRef.current = setInterval(checkStatus, 1500);
  }

  async function startTraining() {
    setStatus("running");
    setResult(null);
    setError(null);
    setProgress(0);
    setCurrentStep("Initialising");
    setMessage("Starting training...");

    try {
      await axios.post(`${BROOD_HEALTH_API_BASE}/brood_health/train`, {
        horizon_hours: Number(horizonHours),
        fast_mode: fastMode,
      });
      beginPolling();
      await checkStatus();
    } catch (requestError) {
      setStatus("error");
      setError(
        requestError?.response?.data?.error ||
          requestError?.response?.data?.message ||
          requestError.message,
      );
    }
  }

  useEffect(() => {
    checkStatus();
    return stopPolling;
  }, []);

  const allModels = result?.all_models || {};
  const orderedModels = MODEL_LABELS.filter((name) => allModels[name]).map(
    (name) => [name, allModels[name]],
  );
  const extraModels = Object.entries(allModels).filter(
    ([name]) => !MODEL_LABELS.includes(name),
  );
  const models = [...orderedModels, ...extraModels];

  if (status === "loading") {
    return <div className="loader">Loading model-training status...</div>;
  }

  if (status === "error") {
    return (
      <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
        <XCircle size={48} color="var(--accent-crimson)" />
        <h3>Training Request Failed</h3>
        <p style={{ color: "var(--text-secondary)" }}>{error}</p>
        <button type="button" className="upload-btn" onClick={checkStatus}>
          <RefreshCw size={17} /> Try Again
        </button>
      </div>
    );
  }

  if (status === "running") {
    return (
      <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
        <Loader
          size={42}
          color="var(--accent-cyan)"
          style={{ animation: "spin 1s linear infinite" }}
        />
        <h3>Training in Progress</h3>
        <div
          style={{
            width: "85%",
            margin: "1rem auto",
            background: "#2d3748",
            borderRadius: "10px",
            height: "11px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${Math.min(100, Math.max(0, progress))}%`,
              background: "var(--accent-emerald)",
              height: "100%",
              transition: "width 0.3s ease",
            }}
          />
        </div>
        <p>{message}</p>
        {currentStep && (
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
            Current step: {currentStep}
          </p>
        )}
      </div>
    );
  }

  if (status === "completed" && result) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <div
          className="card"
          style={{ borderLeft: "4px solid var(--accent-emerald)" }}
        >
          <div
            style={{
              display: "flex",
              gap: "1rem",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <CheckCircle size={34} color="var(--accent-emerald)" />
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: 0 }}>Model Comparison Complete</h3>
              <p
                style={{
                  margin: "0.35rem 0 0",
                  color: "var(--text-secondary)",
                }}
              >
                Selected model: <strong>{result.best_model}</strong> · Forecast
                horizon: <strong>{result.horizon_hours} hours</strong>
              </p>
            </div>
            <button
              type="button"
              className="upload-btn"
              onClick={() => setStatus("idle")}
            >
              Train Again
            </button>
          </div>
        </div>

        {result.target_warning && (
          <div
            className="card"
            style={{ borderLeft: "4px solid var(--accent-gold)" }}
          >
            <strong>Research limitation:</strong> {result.target_warning}
          </div>
        )}

        <div className="card">
          <div className="chart-header">
            <h3>📊 Model Performance Comparison</h3>
            <p>
              Selection prioritises minimum Critical recall, then lower holdout
              MAE and RMSE.
            </p>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                minWidth: "850px",
                borderCollapse: "collapse",
                textAlign: "center",
              }}
            >
              <thead>
                <tr>
                  <th style={{ padding: "0.75rem", textAlign: "left" }}>
                    Model
                  </th>
                  <th>MAE ↓</th>
                  <th>RMSE ↓</th>
                  <th>R² ↑</th>
                  <th>Level Accuracy ↑</th>
                  <th>Critical Recall ↑</th>
                  <th>CV MAE ↓</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {models.map(([name, metrics]) => {
                  const selected = name === result.best_model;
                  const failed = metrics.status === "failed";
                  return (
                    <tr
                      key={name}
                      style={{
                        background: selected
                          ? "rgba(16,185,129,0.13)"
                          : "transparent",
                      }}
                    >
                      <td
                        style={{
                          padding: "0.75rem",
                          textAlign: "left",
                          fontWeight: selected ? 700 : 400,
                        }}
                      >
                        {name}{" "}
                        {selected && (
                          <CheckCircle
                            size={14}
                            style={{
                              display: "inline",
                              color: "var(--accent-emerald)",
                            }}
                          />
                        )}
                      </td>
                      {failed ? (
                        <td
                          colSpan={6}
                          style={{ color: "var(--accent-crimson)" }}
                        >
                          {metrics.error}
                        </td>
                      ) : (
                        <>
                          <td>{valueOrDash(metrics.test_mae)}</td>
                          <td>{valueOrDash(metrics.test_rmse)}</td>
                          <td>{valueOrDash(metrics.test_r2)}</td>
                          <td>{valueOrDash(metrics.health_level_accuracy)}</td>
                          <td>{valueOrDash(metrics.critical_recall)}</td>
                          <td>{valueOrDash(metrics.cv_mae_mean)}</td>
                        </>
                      )}
                      <td>{metrics.status || "unknown"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="stat-footer" style={{ marginTop: "1rem" }}>
            Train rows: {result.train_samples} · Test rows:{" "}
            {result.test_samples} · Features: {result.feature_count}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: "2rem", textAlign: "center" }}>
      <BarChart3 size={48} color="var(--accent-cyan)" />
      <h3>Compare Brood-Health Forecasting Models</h3>
      <p
        style={{
          color: "var(--text-secondary)",
          maxWidth: "720px",
          margin: "0 auto 1.5rem",
        }}
      >
        Compares Ridge Regression, XGBoost, Random Forest, Extra Trees and
        Histogram Gradient Boosting against a Dummy Median baseline using a
        chronological holdout.
      </p>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: "1rem",
          flexWrap: "wrap",
          marginBottom: "1.5rem",
        }}
      >
        <label>
          Forecast horizon
          <select
            value={horizonHours}
            onChange={(event) => setHorizonHours(Number(event.target.value))}
            style={{
              marginLeft: "0.5rem",
              background: "#1e293b",
              color: "inherit",
              padding: "0.4rem",
              borderRadius: "5px",
            }}
          >
            <option value={3}>3 hours</option>
            <option value={6}>6 hours</option>
            <option value={12}>12 hours</option>
            <option value={24}>24 hours</option>
          </select>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <input
            type="checkbox"
            checked={fastMode}
            onChange={(event) => setFastMode(event.target.checked)}
          />
          Fast development run
        </label>
      </div>

      <button
        type="button"
        onClick={startTraining}
        className="upload-btn"
        style={{
          background: "var(--accent-emerald)",
          padding: "0.75rem 1.75rem",
        }}
      >
        <Play size={18} /> Start Model Comparison
      </button>
    </div>
  );
}
