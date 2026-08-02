import { useCallback, useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Cloud,
  Database,
  Droplets,
  Gauge,
  HeartPulse,
  Info,
  Leaf,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Thermometer,
  TrendingDown,
  TrendingUp,
  Wifi,
  Wind,
  Zap,
} from "lucide-react";
import "./HarvestLiveDecisionDashboard.css";

const DEFAULT_HISTORY_HOURS = 168;
const DEMO_REFRESH_MS = 60_000;

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number(value) || 0));
}

function finiteNumber(value) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function formatNumber(value, digits = 1, suffix = "") {
  const numericValue = finiteNumber(value);
  return numericValue === null
    ? "Unavailable"
    : `${numericValue.toFixed(digits)}${suffix}`;
}

function formatSignedNumber(value, digits = 2, suffix = "") {
  const numericValue = finiteNumber(value);

  if (numericValue === null) {
    return "Unavailable";
  }

  const sign = numericValue > 0 ? "+" : "";
  return `${sign}${numericValue.toFixed(digits)}${suffix}`;
}

function formatDateTime(value) {
  if (!value) {
    return "Unavailable";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("en-LK", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Colombo",
  }).format(date);
}

function formatDateOnly(value) {
  if (!value) {
    return "Unavailable";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("en-LK", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Colombo",
  }).format(date);
}

function getReadinessClass(score, backendStatus) {
  const status = String(backendStatus || "").toLowerCase();

  if (status.includes("high-priority") || score >= 85) {
    return "High-Priority Harvest";
  }

  if (status === "ready" || score >= 70) {
    return "Ready";
  }

  if (
    status.includes("approaching") ||
    status.includes("developing") ||
    score >= 30
  ) {
    return "Approaching Harvest";
  }

  return "Not Ready";
}

function getStatusTone(status) {
  const normalized = String(status || "").toLowerCase();

  if (normalized.includes("high-priority")) {
    return "critical";
  }

  if (normalized === "ready") {
    return "ready";
  }

  if (normalized.includes("approaching")) {
    return "approaching";
  }

  return "not-ready";
}

function getHistoryReadinessValue(item) {
  const hui = finiteNumber(item?.hui);

  if (hui !== null) {
    return clamp(hui);
  }

  const probability = finiteNumber(item?.harvest_probability);

  if (probability !== null) {
    return clamp(probability * 100);
  }

  return null;
}

function calculatePredictionStability(predictionHistory) {
  const recentValues = predictionHistory
    .map(getHistoryReadinessValue)
    .filter((value) => value !== null)
    .slice(-24);

  if (recentValues.length < 3) {
    return {
      score: null,
      className: "Insufficient History",
      standardDeviation: null,
      meanAbsoluteChange: null,
      explanation:
        "At least three stored live predictions are needed to calculate HRSI.",
    };
  }

  const mean =
    recentValues.reduce((total, value) => total + value, 0) /
    recentValues.length;

  const variance =
    recentValues.reduce(
      (total, value) => total + (value - mean) ** 2,
      0
    ) / recentValues.length;

  const standardDeviation = Math.sqrt(variance);

  const changes = recentValues
    .slice(1)
    .map((value, index) => Math.abs(value - recentValues[index]));

  const meanAbsoluteChange =
    changes.reduce((total, value) => total + value, 0) /
    Math.max(changes.length, 1);

  /*
    HRSI is a presentation-layer stability indicator:
    100 means recent predictions are highly stable.
    It combines dispersion and consecutive prediction changes.
  */
  const instabilityPenalty =
    standardDeviation * 4 + meanAbsoluteChange * 3;

  const score = clamp(100 - instabilityPenalty);

  let className = "Fluctuating";

  if (score >= 75) {
    className = "Stable";
  } else if (score >= 50) {
    className = "Moderately Stable";
  }

  return {
    score,
    className,
    standardDeviation,
    meanAbsoluteChange,
    explanation:
      "Calculated from the dispersion and consecutive changes of recent stored readiness predictions.",
  };
}

function calculateReadinessRate(predictionHistory) {
  const points = predictionHistory
    .map((item) => ({
      timestamp: new Date(item?.prediction_timestamp).getTime(),
      value: getHistoryReadinessValue(item),
    }))
    .filter(
      (item) =>
        Number.isFinite(item.timestamp) &&
        item.value !== null
    )
    .slice(-24);

  if (points.length < 2) {
    return {
      pointsPerHour: null,
      direction: "Insufficient History",
      icon: "stable",
      explanation:
        "At least two stored predictions are required to calculate the rate of change.",
    };
  }

  const origin = points[0].timestamp;
  const xValues = points.map(
    (item) => (item.timestamp - origin) / 3_600_000
  );
  const yValues = points.map((item) => item.value);

  const meanX =
    xValues.reduce((total, value) => total + value, 0) /
    xValues.length;
  const meanY =
    yValues.reduce((total, value) => total + value, 0) /
    yValues.length;

  const numerator = xValues.reduce(
    (total, value, index) =>
      total + (value - meanX) * (yValues[index] - meanY),
    0
  );
  const denominator = xValues.reduce(
    (total, value) => total + (value - meanX) ** 2,
    0
  );

  const pointsPerHour =
    denominator === 0 ? 0 : numerator / denominator;

  if (pointsPerHour > 0.15) {
    return {
      pointsPerHour,
      direction: "Increasing",
      icon: "up",
      explanation:
        "Recent stored readiness predictions show an upward trend.",
    };
  }

  if (pointsPerHour < -0.15) {
    return {
      pointsPerHour,
      direction: "Decreasing",
      icon: "down",
      explanation:
        "Recent stored readiness predictions show a downward trend.",
    };
  }

  return {
    pointsPerHour,
    direction: "Stable",
    icon: "stable",
    explanation:
      "Recent stored readiness predictions show no material directional change.",
  };
}

function median(values) {
  if (!values.length) {
    return null;
  }

  const sortedValues = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sortedValues.length / 2);

  return sortedValues.length % 2 === 0
    ? (sortedValues[middle - 1] + sortedValues[middle]) / 2
    : sortedValues[middle];
}

function calculateNextExpectedReading(history) {
  const timestamps = history
    .map((item) => new Date(item?.timestamp).getTime())
    .filter(Number.isFinite)
    .sort((a, b) => a - b);

  if (!timestamps.length) {
    return null;
  }

  const intervals = timestamps
    .slice(1)
    .map((timestamp, index) => timestamp - timestamps[index])
    .filter(
      (interval) =>
        interval > 0 && interval <= 24 * 60 * 60 * 1000
    );

  const interval =
    median(intervals.slice(-30)) || 10 * 60 * 1000;

  return new Date(timestamps[timestamps.length - 1] + interval);
}

function calculateFreshness(readingTimestamp, staleFlag) {
  if (!readingTimestamp) {
    return {
      label: "Unavailable",
      tone: "stale",
      ageMinutes: null,
    };
  }

  const timestamp = new Date(readingTimestamp).getTime();

  if (!Number.isFinite(timestamp)) {
    return {
      label: "Unavailable",
      tone: "stale",
      ageMinutes: null,
    };
  }

  const ageMinutes = Math.max(
    0,
    (Date.now() - timestamp) / 60_000
  );

  if (staleFlag || ageMinutes > 120) {
    return {
      label: "Stale",
      tone: "stale",
      ageMinutes,
    };
  }

  if (ageMinutes > 30) {
    return {
      label: "Delayed",
      tone: "delayed",
      ageMinutes,
    };
  }

  return {
    label: "Live",
    tone: "live",
    ageMinutes,
  };
}

function calculateSensorStatus(
  history,
  key,
  currentValue,
  stableDifference,
  highThreshold = null
) {
  const current = finiteNumber(currentValue);

  if (current === null) {
    return {
      label: "Unavailable",
      tone: "neutral",
    };
  }

  if (highThreshold !== null && current >= highThreshold) {
    return {
      label: "High",
      tone: "warning",
    };
  }

  const recentValues = history
    .slice(-6)
    .map((item) => finiteNumber(item?.[key]))
    .filter((value) => value !== null);

  if (recentValues.length < 2) {
    return {
      label: "Current",
      tone: "neutral",
    };
  }

  const range =
    Math.max(...recentValues) - Math.min(...recentValues);

  if (range <= stableDifference) {
    return {
      label: "Stable",
      tone: "good",
    };
  }

  return {
    label: "Changing",
    tone: "warning",
  };
}

function calculateCo2Status(value) {
  const numericValue = finiteNumber(value);

  if (numericValue === null) {
    return {
      label: "Unavailable",
      tone: "neutral",
    };
  }

  if (numericValue >= 1800) {
    return {
      label: "High",
      tone: "danger",
    };
  }

  if (numericValue >= 1200) {
    return {
      label: "Elevated",
      tone: "warning",
    };
  }

  return {
    label: "Normal",
    tone: "good",
  };
}

function normalizeSafetyItem(value, defaultLabel = "Unavailable") {
  if (value === null || value === undefined) {
    return {
      value: defaultLabel,
      score: null,
      className: defaultLabel,
    };
  }

  if (typeof value === "object") {
    const score =
      finiteNumber(value.score) ??
      finiteNumber(value.probability) ??
      finiteNumber(value.risk_probability);

    const className =
      value.class ||
      value.status ||
      value.label ||
      value.risk_class ||
      defaultLabel;

    return {
      value:
        score === null
          ? String(className)
          : `${(score <= 1 ? score * 100 : score).toFixed(
              1
            )}% · ${className}`,
      score,
      className: String(className),
    };
  }

  return {
    value: String(value),
    score: null,
    className: String(value),
  };
}

function isUnsafeSafetyClass(value) {
  const normalized = String(value || "").toLowerCase();

  return [
    "high",
    "critical",
    "poor",
    "severe",
    "urgent",
    "danger",
  ].some((keyword) => normalized.includes(keyword));
}

function calculateEarlyWarning({
  score,
  threshold,
  readinessClass,
  rate,
  confidence,
}) {
  const confidenceLevel = String(confidence || "").toLowerCase();

  if (
    score >= 85 ||
    readinessClass === "High-Priority Harvest"
  ) {
    return {
      level: "High",
      tone: "high",
      message:
        "Inspect the hive and confirm harvesting conditions as soon as practical.",
    };
  }

  if (
    score >= threshold ||
    readinessClass === "Ready" ||
    (readinessClass === "Approaching Harvest" &&
      rate.pointsPerHour !== null &&
      rate.pointsPerHour > 0.15)
  ) {
    return {
      level: "Moderate",
      tone: "moderate",
      message:
        confidenceLevel === "low"
          ? "Readiness is elevated, but inspect the hive before acting because confidence is low."
          : "Plan a field inspection and prepare for harvesting within the recommended period.",
    };
  }

  return {
    level: "Low",
    tone: "low",
    message:
      "No immediate harvest alert is active. Continue routine monitoring.",
  };
}

function buildProvisionalHarvestWindow(
  backendWindow,
  readinessClass,
  predictionTimestamp
) {
  if (backendWindow?.available) {
    return {
      available: true,
      start: backendWindow.start,
      end: backendWindow.end,
      source: "Validated sustained-prediction rule",
      provisional: false,
      note: backendWindow.basis || "",
    };
  }

  if (
    readinessClass === "Not Ready" ||
    !predictionTimestamp
  ) {
    return {
      available: false,
      start: null,
      end: null,
      source: "Unavailable",
      provisional: false,
      note:
        backendWindow?.reason ||
        "The current readiness level does not support a harvest-window estimate.",
    };
  }

  const baseDate = new Date(predictionTimestamp);

  if (Number.isNaN(baseDate.getTime())) {
    return {
      available: false,
      start: null,
      end: null,
      source: "Unavailable",
      provisional: false,
      note: backendWindow?.reason || "Prediction time is unavailable.",
    };
  }

  let startOffsetDays = 2;
  let endOffsetDays = 7;

  if (readinessClass === "Ready") {
    startOffsetDays = 1;
    endOffsetDays = 4;
  }

  if (readinessClass === "High-Priority Harvest") {
    startOffsetDays = 0;
    endOffsetDays = 2;
  }

  const start = new Date(baseDate);
  start.setDate(start.getDate() + startOffsetDays);

  const end = new Date(baseDate);
  end.setDate(end.getDate() + endOffsetDays);

  return {
    available: true,
    start: start.toISOString(),
    end: end.toISOString(),
    source: "Provisional readiness-class rule",
    provisional: true,
    note:
      "This provisional window is generated for decision-support display because the current historical target covers seven days. Confirm it through hive inspection.",
  };
}

function buildFinalRecommendation({
  backendRecommendation,
  readinessClass,
  safety,
  environmentalStatus,
  confidenceLevel,
}) {
  if (isUnsafeSafetyClass(safety.absconding.className)) {
    return "Urgent colony inspection is required. Address the absconding risk before harvesting.";
  }

  if (isUnsafeSafetyClass(safety.swarming.className)) {
    return "Manage the swarming risk before harvesting and reassess readiness after inspection.";
  }

  if (isUnsafeSafetyClass(safety.brood.className)) {
    return "Inspect brood health before harvesting.";
  }

  if (
    String(environmentalStatus || "")
      .toLowerCase()
      .includes("unsuitable")
  ) {
    return "Harvest readiness is elevated, but environmental conditions are unsuitable. Delay field action and continue monitoring.";
  }

  if (confidenceLevel === "Low") {
    return `${backendRecommendation || "Continue monitoring."} Confirm the decision through a manual hive inspection because prediction confidence is low.`;
  }

  if (backendRecommendation) {
    return backendRecommendation;
  }

  if (readinessClass === "High-Priority Harvest") {
    return "Inspect and harvest as soon as practical.";
  }

  if (readinessClass === "Ready") {
    return "Plan harvesting within the recommended window.";
  }

  if (readinessClass === "Approaching Harvest") {
    return "Inspect the hive within the next two days.";
  }

  return "Continue monitoring.";
}

function buildExplanation({
  backendReasons,
  rate,
  stability,
  derivedValues,
  environmentalStatus,
}) {
  const reasons = [...(backendReasons || [])];

  const weightGain = finiteNumber(
    derivedValues?.weight_change_72h_kg
  );

  const distanceFromMaximum = finiteNumber(
    derivedValues?.distance_from_7day_max_kg
  );

  if (weightGain !== null && weightGain > 0.5) {
    reasons.push(
      `Strong recent weight gain: ${weightGain.toFixed(
        2
      )} kg over the previous 72 hours.`
    );
  }

  if (
    distanceFromMaximum !== null &&
    distanceFromMaximum <= 2
  ) {
    reasons.push(
      `Hive weight remains close to its recent maximum (${distanceFromMaximum.toFixed(
        2
      )} kg below the seven-day maximum).`
    );
  }

  if (stability.score !== null && stability.score >= 75) {
    reasons.push(
      `Recent harvest-readiness predictions are stable (HRSI ${stability.score.toFixed(
        0
      )}/100).`
    );
  }

  if (
    rate.pointsPerHour !== null &&
    rate.pointsPerHour > 0.15
  ) {
    reasons.push(
      `Harvest readiness is increasing by ${rate.pointsPerHour.toFixed(
        2
      )} HUI points per hour.`
    );
  }

  if (
    String(environmentalStatus || "")
      .toLowerCase()
      .includes("suitable")
  ) {
    reasons.push(
      "Current environmental conditions are similar to historical pre-harvest conditions."
    );
  }

  return [...new Set(reasons)].slice(0, 6);
}

function GaugeCard({
  score,
  modelName,
  probability,
}) {
  const normalizedScore = clamp(score);

  return (
    <article className="hd-output-card hd-gauge-card">
      <div className="hd-card-title-row">
        <h3>Harvest Urgency Index</h3>
        <Info size={16} />
      </div>

      <div className="hd-semi-gauge">
        <svg viewBox="0 0 220 130" aria-label={`HUI ${normalizedScore}`}>
          <path
            d="M 20 110 A 90 90 0 0 1 200 110"
            pathLength="100"
            className="hd-gauge-track"
          />
          <path
            d="M 20 110 A 90 90 0 0 1 200 110"
            pathLength="100"
            className="hd-gauge-progress"
            strokeDasharray={`${normalizedScore} ${100 - normalizedScore}`}
          />
        </svg>

        <div className="hd-gauge-value">
          <strong>{normalizedScore.toFixed(0)}</strong>
          <span>{normalizedScore.toFixed(1)}% urgency</span>
        </div>
      </div>

      <div className="hd-model-chip">
        Model: <strong>{modelName || "Unavailable"}</strong>
      </div>

      <p className="hd-card-footnote">
        Upcoming harvest score: {formatNumber(probability, 1, "%")}
      </p>
    </article>
  );
}

function StatusScale({ score, readinessClass }) {
  const markerPosition = clamp(score);

  return (
    <article className="hd-output-card hd-status-card">
      <div className="hd-card-title-row">
        <h3>Harvest Status</h3>
        <Info size={16} />
      </div>

      <strong
        className={`hd-status-title hd-status-title--${getStatusTone(
          readinessClass
        )}`}
      >
        {readinessClass}
      </strong>

      <div className="hd-status-scale">
        <div className="hd-status-segment hd-status-segment--not-ready" />
        <div className="hd-status-segment hd-status-segment--approaching" />
        <div className="hd-status-segment hd-status-segment--ready" />
        <div className="hd-status-segment hd-status-segment--priority" />

        <span
          className="hd-status-marker"
          style={{ left: `${markerPosition}%` }}
        />
      </div>

      <div className="hd-status-labels">
        <span>Not Ready</span>
        <span>Approaching</span>
        <span>Ready</span>
        <span>High Priority</span>
      </div>

      <div className="hd-status-message">
        Hive is currently classified as{" "}
        <strong>{readinessClass}</strong>.
      </div>
    </article>
  );
}

function TrendBehaviorCard({ rate, stability }) {
  const DirectionIcon =
    rate.icon === "up"
      ? TrendingUp
      : rate.icon === "down"
        ? TrendingDown
        : Activity;

  return (
    <article className="hd-output-card hd-behavior-card">
      <div className="hd-card-title-row">
        <h3>Readiness Behaviour</h3>
        <Info size={16} />
      </div>

      <DirectionIcon
        size={56}
        className={`hd-direction-icon hd-direction-icon--${rate.icon}`}
      />

      <strong className="hd-behavior-title">
        {rate.direction}
      </strong>

      <p>
        {rate.pointsPerHour === null
          ? rate.explanation
          : `${formatSignedNumber(
              rate.pointsPerHour,
              2
            )} HUI points per hour`}
      </p>

      <div className="hd-stability-chip">
        HRSI:{" "}
        <strong>
          {stability.score === null
            ? "Unavailable"
            : `${stability.score.toFixed(0)}/100`}
        </strong>{" "}
        · {stability.className}
      </div>
    </article>
  );
}

function EarlyWarningCard({ warning }) {
  return (
    <article
      className={`hd-output-card hd-warning-output hd-warning-output--${warning.tone}`}
    >
      <div className="hd-card-title-row">
        <h3>Early Warning Alert</h3>
        <Info size={16} />
      </div>

      <AlertTriangle size={68} />

      <strong>{warning.level}</strong>
      <p>{warning.message}</p>
    </article>
  );
}

function InsightCard({ explanations }) {
  return (
    <article className="hd-output-card hd-insight-card">
      <div className="hd-card-title-row">
        <h3>Explainable Harvest Insights</h3>
        <Info size={16} />
      </div>

      {explanations.length ? (
        <ul>
          {explanations.slice(0, 4).map((reason, index) => (
            <li key={`${reason}-${index}`}>{reason}</li>
          ))}
        </ul>
      ) : (
        <p>
          Prediction explanations will appear when the model
          returns contributing factors.
        </p>
      )}
    </article>
  );
}

function SensorReadingRow({
  icon,
  label,
  value,
  status,
}) {
  return (
    <div className="hd-sensor-row">
      <span className="hd-sensor-icon">{icon}</span>
      <span className="hd-sensor-label">{label}</span>
      <strong>{value}</strong>
      <span
        className={`hd-sensor-status hd-sensor-status--${status.tone}`}
      >
        {status.label}
      </span>
    </div>
  );
}

function SafetyStatus({
  icon,
  label,
  item,
}) {
  const unsafe = isUnsafeSafetyClass(item.className);

  return (
    <div className="hd-safety-item">
      <span>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{item.value}</strong>
      </div>
      <span
        className={
          unsafe
            ? "hd-safety-dot hd-safety-dot--danger"
            : item.className === "Unavailable"
              ? "hd-safety-dot"
              : "hd-safety-dot hd-safety-dot--good"
        }
      />
    </div>
  );
}

export default function HarvestLiveDecisionDashboard({
  apiBaseUrl,
  edaData,
  onBack,
}) {
  const [health, setHealth] = useState(null);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [selectedRange, setSelectedRange] = useState("7D");

  const fetchJson = useCallback(
    async (path, allowUnprocessable = false) => {
      const response = await fetch(`${apiBaseUrl}${path}`);
      const payload = await response.json();

      if (
        !response.ok &&
        !(allowUnprocessable && response.status === 422)
      ) {
        throw new Error(
          payload.details ||
            payload.error ||
            payload.reason ||
            `Request failed with status ${response.status}`
        );
      }

      return payload;
    },
    [apiBaseUrl]
  );

  const loadDeviceData = useCallback(
    async (deviceId, background = false) => {
      if (!deviceId) {
        return;
      }

      if (background) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      try {
        const [predictionPayload, historyPayload] =
          await Promise.all([
            fetchJson(
              `/api/harvest/live/predict/${encodeURIComponent(
                deviceId
              )}?hours=${DEFAULT_HISTORY_HOURS}`,
              true
            ),
            fetchJson(
              `/api/harvest/live/history/${encodeURIComponent(
                deviceId
              )}?hours=${DEFAULT_HISTORY_HOURS}`
            ),
          ]);

        setPrediction(predictionPayload);
        setHistory(historyPayload.readings || []);
      } catch (requestError) {
        setError(
          requestError.message ||
            "Unable to load the live harvest output."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [fetchJson]
  );

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      setLoading(true);
      setError("");

      try {
        const [healthPayload, devicesPayload] =
          await Promise.all([
            fetchJson("/api/harvest/live/health"),
            fetchJson("/api/harvest/live/devices"),
          ]);

        if (cancelled) {
          return;
        }

        const availableDevices = devicesPayload.devices || [];

        setHealth(healthPayload);
        setDevices(availableDevices);

        const firstDevice = availableDevices[0] || "";
        setSelectedDevice(firstDevice);

        if (firstDevice) {
          await loadDeviceData(firstDevice);
        } else {
          setLoading(false);
          setError(
            "No ongoing IoT hive was returned by PostgreSQL."
          );
        }
      } catch (requestError) {
        if (!cancelled) {
          setLoading(false);
          setError(
            requestError.message ||
              "Unable to initialize the live dashboard."
          );
        }
      }
    }

    initialize();

    return () => {
      cancelled = true;
    };
  }, [fetchJson, loadDeviceData]);

  useEffect(() => {
    if (!selectedDevice) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      loadDeviceData(selectedDevice, true);
    }, DEMO_REFRESH_MS);

    return () => window.clearInterval(timer);
  }, [loadDeviceData, selectedDevice]);

  const predictionHistory =
    prediction?.trend?.previous_7_day_predictions || [];

  const probabilityPercent = clamp(
    finiteNumber(prediction?.harvest_probability) !== null
      ? Number(prediction.harvest_probability) * 100
      : prediction?.harvest_readiness_percent ??
          prediction?.hui ??
          0
  );

  const hui = clamp(
    prediction?.hui ??
      prediction?.harvest_readiness_percent ??
      probabilityPercent
  );

  const readinessClass = getReadinessClass(
    hui,
    prediction?.status
  );

  const operationalThreshold = clamp(
    prediction?.operational_decision?.validated_threshold ??
      47.78
  );

  const stability = useMemo(
    () => calculatePredictionStability(predictionHistory),
    [predictionHistory]
  );

  const rate = useMemo(
    () => calculateReadinessRate(predictionHistory),
    [predictionHistory]
  );

  const nextExpectedReading = useMemo(
    () => calculateNextExpectedReading(history),
    [history]
  );

  const dataQuality = prediction?.data_quality || {};
  const currentSensors =
    prediction?.current_sensor_values || {};
  const derivedValues = prediction?.derived_values || {};
  const confidence = prediction?.confidence || {};
  const environment =
    prediction?.environmental_suitability || {};
  const backendSafety = prediction?.colony_risks || {};

  const freshness = calculateFreshness(
    prediction?.reading_timestamp,
    dataQuality.reading_stale
  );

  const safety = {
    brood: normalizeSafetyItem(
      backendSafety.brood_health ??
        edaData?.live_brood_health
    ),
    swarming: normalizeSafetyItem(
      backendSafety.swarming_risk ??
        edaData?.live_swarming_risk
    ),
    absconding: normalizeSafetyItem(
      backendSafety.absconding_risk ??
        edaData?.live_absconding_risk
    ),
  };

  const earlyWarning = calculateEarlyWarning({
    score: hui,
    threshold: operationalThreshold,
    readinessClass,
    rate,
    confidence: confidence.level,
  });

  const harvestWindow = buildProvisionalHarvestWindow(
    prediction?.recommended_harvest_window,
    readinessClass,
    prediction?.prediction_timestamp
  );

  const explanations = buildExplanation({
    backendReasons: prediction?.main_reasons || [],
    rate,
    stability,
    derivedValues,
    environmentalStatus: environment.status,
  });

  const finalRecommendation = buildFinalRecommendation({
    backendRecommendation: prediction?.recommendation,
    readinessClass,
    safety,
    environmentalStatus: environment.status,
    confidenceLevel: confidence.level,
  });

  const temperatureStatus = calculateSensorStatus(
    history,
    "internal_temperature_c",
    currentSensors.internal_temperature_c,
    1.5
  );

  const humidityStatus = calculateSensorStatus(
    history,
    "internal_humidity_pct",
    currentSensors.internal_humidity_pct,
    5,
    80
  );

  const weightStatus = calculateSensorStatus(
    history,
    "hive_weight_kg",
    currentSensors.hive_weight_kg,
    0.75
  );

  const co2Status = calculateCo2Status(
    currentSensors.co2_ppm
  );

  const rangeHours = {
    "1H": 1,
    "6H": 6,
    "12H": 12,
    "24H": 24,
    "7D": 168,
  }[selectedRange];

  const cutoffTimestamp =
    Date.now() - rangeHours * 60 * 60 * 1000;

  const sensorChartData = history
    .filter(
      (item) =>
        new Date(item.timestamp).getTime() >= cutoffTimestamp
    )
    .map((item) => ({
      timestamp: item.timestamp,
      displayTime: new Intl.DateTimeFormat("en-LK", {
        hour: "2-digit",
        minute: "2-digit",
        month: rangeHours > 24 ? "short" : undefined,
        day: rangeHours > 24 ? "numeric" : undefined,
        timeZone: "Asia/Colombo",
      }).format(new Date(item.timestamp)),
      temperature: finiteNumber(
        item.internal_temperature_c
      ),
      humidity: finiteNumber(
        item.internal_humidity_pct
      ),
      co2: finiteNumber(item.co2_ppm),
      weight: finiteNumber(item.hive_weight_kg),
    }));

  const readinessChartData = predictionHistory
    .filter(
      (item) =>
        new Date(item.prediction_timestamp).getTime() >=
        cutoffTimestamp
    )
    .map((item) => ({
      timestamp: item.prediction_timestamp,
      displayTime: new Intl.DateTimeFormat("en-LK", {
        hour: "2-digit",
        minute: "2-digit",
        month: rangeHours > 24 ? "short" : undefined,
        day: rangeHours > 24 ? "numeric" : undefined,
        timeZone: "Asia/Colombo",
      }).format(new Date(item.prediction_timestamp)),
      hui: getHistoryReadinessValue(item),
    }));

  if (loading && !prediction) {
    return (
      <section className="content-section">
        <div className="message-card">
          Loading the ongoing hive and harvest prediction…
        </div>
      </section>
    );
  }

  return (
    <section className="content-section hd-dashboard">
      <div className="section-heading hd-section-heading">
        <div>
          <p className="section-kicker">Step 3</p>
          <h2>Harvest Urgency Live Prediction</h2>
          <p>
            Monitor real-time IoT sensor readings and generate
            the complete hive-level harvest decision-support
            output package.
          </p>
        </div>

        <div className="hd-live-controls">
          <label>
            <span>Ongoing Hive</span>
            <select
              value={selectedDevice}
              onChange={(event) => {
                const deviceId = event.target.value;
                setSelectedDevice(deviceId);
                loadDeviceData(deviceId);
              }}
              disabled={refreshing}
            >
              {devices.map((deviceId) => (
                <option key={deviceId} value={deviceId}>
                  {String(deviceId).toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            className="primary-button hd-refresh-button"
            onClick={() =>
              loadDeviceData(selectedDevice, true)
            }
            disabled={refreshing || !selectedDevice}
          >
            <RefreshCw
              size={16}
              className={refreshing ? "hd-spin" : ""}
            />
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="error-card">
          <strong>Error:</strong> {error}
        </div>
      ) : null}

      {prediction?.prediction_available === false ? (
        <div className="hd-unavailable">
          <AlertTriangle size={25} />
          <div>
            <h3>Live prediction is not available yet</h3>
            <p>{prediction.reason}</p>
            <small>
              Available history:{" "}
              {formatNumber(
                prediction.available_history_hours,
                1,
                " hours"
              )}
            </small>
          </div>
        </div>
      ) : null}

      {prediction?.prediction_available ? (
        <>
          <div className="hd-identity-grid">
            <div className="hd-identity-card">
              <span className="hd-identity-icon">
                <Database size={20} />
              </span>
              <div>
                <small>Hive ID</small>
                <strong>
                  {String(selectedDevice).toUpperCase()}
                </strong>
              </div>
            </div>

            <div className="hd-identity-card">
              <span className="hd-identity-icon">
                <Clock3 size={20} />
              </span>
              <div>
                <small>Last Updated</small>
                <strong>
                  {formatDateTime(
                    prediction.reading_timestamp
                  )}
                </strong>
              </div>
            </div>

            <div className="hd-identity-card">
              <span className="hd-identity-icon">
                <CalendarDays size={20} />
              </span>
              <div>
                <small>Next Expected Reading</small>
                <strong>
                  {nextExpectedReading
                    ? formatDateTime(
                        nextExpectedReading.toISOString()
                      )
                    : "Unavailable"}
                </strong>
              </div>
            </div>

            <div className="hd-identity-card">
              <span
                className={`hd-identity-icon hd-freshness-icon hd-freshness-icon--${freshness.tone}`}
              >
                {freshness.tone === "live" ? (
                  <CheckCircle2 size={20} />
                ) : (
                  <AlertTriangle size={20} />
                )}
              </span>
              <div>
                <small>Data Freshness</small>
                <strong
                  className={`hd-freshness-text hd-freshness-text--${freshness.tone}`}
                >
                  {freshness.label}
                </strong>
                <span>
                  {freshness.ageMinutes === null
                    ? ""
                    : `${freshness.ageMinutes.toFixed(
                        0
                      )} minutes old`}
                </span>
              </div>
            </div>
          </div>

          <div className="hd-output-grid">
            <GaugeCard
              score={hui}
              probability={probabilityPercent}
              modelName={prediction?.model?.name}
            />

            <StatusScale
              score={hui}
              readinessClass={readinessClass}
            />

            <TrendBehaviorCard
              rate={rate}
              stability={stability}
            />

            <EarlyWarningCard warning={earlyWarning} />

            <InsightCard explanations={explanations} />
          </div>

          <div className="hd-main-grid">
            <article className="hd-chart-panel">
              <div className="hd-panel-heading">
                <div>
                  <h3>Harvest Urgency Timeline</h3>
                  <p>
                    Stored HUI predictions and operational
                    readiness thresholds.
                  </p>
                </div>
                <Info size={16} />
              </div>

              {readinessChartData.length > 1 ? (
                <ResponsiveContainer width="100%" height={330}>
                  <LineChart
                    data={readinessChartData}
                    margin={{
                      top: 20,
                      right: 22,
                      left: 0,
                      bottom: 8,
                    }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="displayTime"
                      minTickGap={50}
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip />
                    <Legend />
                    <ReferenceLine
                      y={operationalThreshold}
                      stroke="#1f9d55"
                      strokeDasharray="5 4"
                      label="Operational threshold"
                    />
                    <ReferenceLine
                      y={85}
                      stroke="#dc3545"
                      strokeDasharray="5 4"
                      label="High priority"
                    />
                    <Line
                      type="monotone"
                      dataKey="hui"
                      name="HUI"
                      stroke="#f2a900"
                      strokeWidth={2.5}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="hd-chart-empty">
                  Multiple stored predictions are required
                  before the HUI timeline can be displayed.
                </div>
              )}

              <div className="hd-range-buttons">
                {["1H", "6H", "12H", "24H", "7D"].map(
                  (range) => (
                    <button
                      type="button"
                      key={range}
                      className={
                        selectedRange === range
                          ? "hd-range-button active"
                          : "hd-range-button"
                      }
                      onClick={() => setSelectedRange(range)}
                    >
                      {range}
                    </button>
                  )
                )}
              </div>
            </article>

            <article className="hd-chart-panel">
              <div className="hd-panel-heading">
                <div>
                  <h3>Sensor Trend (Live)</h3>
                  <p>
                    Temperature, humidity, CO₂ and weight from
                    the ongoing hive.
                  </p>
                </div>
                <Info size={16} />
              </div>

              {sensorChartData.length > 1 ? (
                <ResponsiveContainer width="100%" height={330}>
                  <LineChart
                    data={sensorChartData}
                    margin={{
                      top: 20,
                      right: 26,
                      left: 0,
                      bottom: 8,
                    }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="displayTime"
                      minTickGap={50}
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis
                      yAxisId="environment"
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis
                      yAxisId="co2"
                      orientation="right"
                      tick={{ fontSize: 10 }}
                    />
                    <Tooltip />
                    <Legend />
                    <Line
                      yAxisId="environment"
                      type="monotone"
                      dataKey="temperature"
                      name="Temperature (°C)"
                      stroke="#e63946"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Line
                      yAxisId="environment"
                      type="monotone"
                      dataKey="humidity"
                      name="Humidity (%)"
                      stroke="#1d8cf8"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Line
                      yAxisId="co2"
                      type="monotone"
                      dataKey="co2"
                      name="CO₂ (ppm)"
                      stroke="#1f9d55"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Line
                      yAxisId="environment"
                      type="monotone"
                      dataKey="weight"
                      name="Weight (kg)"
                      stroke="#f2a900"
                      dot={false}
                      strokeWidth={2.3}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="hd-chart-empty">
                  Recent live sensor history is unavailable.
                </div>
              )}

              <div className="hd-range-buttons">
                {["1H", "6H", "12H", "24H", "7D"].map(
                  (range) => (
                    <button
                      type="button"
                      key={range}
                      className={
                        selectedRange === range
                          ? "hd-range-button active"
                          : "hd-range-button"
                      }
                      onClick={() => setSelectedRange(range)}
                    >
                      {range}
                    </button>
                  )
                )}
              </div>
            </article>

            <aside className="hd-side-panel">
              <article className="hd-latest-readings">
                <div className="hd-panel-heading">
                  <div>
                    <h3>Latest IoT Readings</h3>
                    <p>Current ongoing-hive sensor values.</p>
                  </div>
                  <Info size={16} />
                </div>

                <SensorReadingRow
                  icon={<Thermometer size={19} />}
                  label="Temperature"
                  value={formatNumber(
                    currentSensors.internal_temperature_c,
                    1,
                    " °C"
                  )}
                  status={temperatureStatus}
                />

                <SensorReadingRow
                  icon={<Droplets size={19} />}
                  label="Humidity"
                  value={formatNumber(
                    currentSensors.internal_humidity_pct,
                    1,
                    "%"
                  )}
                  status={humidityStatus}
                />

                <SensorReadingRow
                  icon={<Cloud size={19} />}
                  label="CO₂ Level"
                  value={formatNumber(
                    currentSensors.co2_ppm,
                    0,
                    " ppm"
                  )}
                  status={co2Status}
                />

                <SensorReadingRow
                  icon={<Scale size={19} />}
                  label="Weight"
                  value={formatNumber(
                    currentSensors.hive_weight_kg,
                    2,
                    " kg"
                  )}
                  status={weightStatus}
                />
              </article>

              <article className="hd-window-card">
                <CalendarDays size={24} />
                <div>
                  <small>
                    {harvestWindow.provisional
                      ? "Provisional Harvest Window"
                      : "Recommended Harvest Window"}
                  </small>
                  <strong>
                    {harvestWindow.available
                      ? `${formatDateOnly(
                          harvestWindow.start
                        )} – ${formatDateOnly(
                          harvestWindow.end
                        )}`
                      : "Unavailable"}
                  </strong>
                  <span>{harvestWindow.source}</span>
                </div>

                <div className="hd-confidence-block">
                  <small>Confidence</small>
                  <strong>
                    {confidence.level || "Unavailable"}
                  </strong>
                </div>
              </article>

              {harvestWindow.note ? (
                <p className="hd-window-note">
                  {harvestWindow.note}
                </p>
              ) : null}

              <article className="hd-safety-card">
                <div className="hd-panel-heading">
                  <div>
                    <h3>Colony-Safety Status</h3>
                    <p>
                      Other module outputs remain separate from HUI.
                    </p>
                  </div>
                  <ShieldCheck size={20} />
                </div>

                <SafetyStatus
                  icon={<HeartPulse size={18} />}
                  label="Brood Health"
                  item={safety.brood}
                />

                <SafetyStatus
                  icon={<Zap size={18} />}
                  label="Swarming Risk"
                  item={safety.swarming}
                />

                <SafetyStatus
                  icon={<Wind size={18} />}
                  label="Absconding Risk"
                  item={safety.absconding}
                />

                <SafetyStatus
                  icon={<Leaf size={18} />}
                  label="Environmental Suitability"
                  item={normalizeSafetyItem(
                    environment.status
                  )}
                />
              </article>

              <article className="hd-final-recommendation">
                <ShieldCheck size={24} />
                <div>
                  <small>Final Recommendation</small>
                  <strong>{finalRecommendation}</strong>
                </div>
              </article>
            </aside>
          </div>

          <div className="hd-output-package">
            <div className="hd-panel-heading">
              <div>
                <h3>Complete Decision-Support Output Package</h3>
                <p>
                  All outputs specified under Section 4.2.3.
                </p>
              </div>
              <BrainCircuit size={21} />
            </div>

            <div className="hd-output-list">
              <div>
                <span>4.2.3.1 Upcoming Harvest Probability</span>
                <strong>
                  {probabilityPercent.toFixed(1)}% within{" "}
                  {prediction.prediction_horizon ||
                    "the selected horizon"}
                </strong>
              </div>

              <div>
                <span>4.2.3.2 Harvest Urgency Index</span>
                <strong>{hui.toFixed(1)}/100</strong>
              </div>

              <div>
                <span>4.2.3.3 Harvest-Readiness Class</span>
                <strong>{readinessClass}</strong>
              </div>

              <div>
                <span>
                  4.2.3.4 Harvest Readiness Stability Index
                </span>
                <strong>
                  {stability.score === null
                    ? "Unavailable"
                    : `${stability.score.toFixed(
                        1
                      )}/100 — ${stability.className}`}
                </strong>
              </div>

              <div>
                <span>
                  4.2.3.5 Harvest Readiness Rate of Change
                </span>
                <strong>
                  {rate.pointsPerHour === null
                    ? "Unavailable"
                    : `${rate.direction} at ${formatSignedNumber(
                        rate.pointsPerHour,
                        2
                      )} HUI points/hour`}
                </strong>
              </div>

              <div>
                <span>
                  4.2.3.6 Recommended Harvest Window
                </span>
                <strong>
                  {harvestWindow.available
                    ? `${formatDateOnly(
                        harvestWindow.start
                      )} – ${formatDateOnly(
                        harvestWindow.end
                      )}`
                    : "Unavailable"}
                </strong>
              </div>

              <div>
                <span>4.2.3.7 Prediction Confidence</span>
                <strong>
                  {confidence.level || "Unavailable"}
                </strong>
              </div>

              <div>
                <span>4.2.3.8 Colony-Safety Status</span>
                <strong>
                  Brood: {safety.brood.className} · Swarming:{" "}
                  {safety.swarming.className} · Absconding:{" "}
                  {safety.absconding.className} · Environment:{" "}
                  {environment.status || "Unavailable"}
                </strong>
              </div>

              <div>
                <span>4.2.3.9 Final Recommendation</span>
                <strong>{finalRecommendation}</strong>
              </div>

              <div>
                <span>4.2.3.10 Prediction Explanation</span>
                <strong>
                  {explanations.length
                    ? explanations.join(" ")
                    : "Unavailable"}
                </strong>
              </div>
            </div>
          </div>

          {prediction?.warnings?.length ? (
            <div className="hd-model-warnings">
              <ShieldAlert size={22} />
              <div>
                <h3>Model and Data-Quality Warnings</h3>
                <ul>
                  {prediction.warnings.map((warning, index) => (
                    <li key={`${warning}-${index}`}>
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}

          <div className="hd-model-note">
            <strong>
              Model: {prediction?.model?.name || "Unavailable"}
            </strong>
            <span>
              {prediction?.model?.local_validation_status ||
                "Local Sri Lankan harvest-event validation is pending."}
            </span>
            <span>
              Data completeness:{" "}
              {formatNumber(
                finiteNumber(dataQuality.data_completeness) *
                  100,
                1,
                "%"
              )}
            </span>
          </div>
        </>
      ) : null}

      <div className="section-actions">
        <button
          className="secondary-button"
          type="button"
          onClick={onBack}
        >
          Back to Model Comparison
        </button>
      </div>
    </section>
  );
}
