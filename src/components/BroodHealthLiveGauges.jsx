import React from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  HEALTH_COLORS,
  STABILITY_COLORS,
  TREND_COLORS,
} from "../utils/broodHealthConstants";

function clamp(value, minimum, maximum) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return minimum;
  return Math.min(maximum, Math.max(minimum, numeric));
}

function polarPoint(cx, cy, radius, degrees) {
  const radians = (degrees * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy - radius * Math.sin(radians),
  };
}

function arcPath(cx, cy, radius, startRisk, endRisk) {
  const startAngle = 180 - startRisk * 1.8;
  const endAngle = 180 - endRisk * 1.8;
  const start = polarPoint(cx, cy, radius, startAngle);
  const end = polarPoint(cx, cy, radius, endAngle);
  const largeArc = Math.abs(endAngle - startAngle) > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

export function BroodHealthGauge({
  score = 0,
  healthLevel = "Critical",
  forecastHorizonHours = 6,
}) {
  const healthScore = clamp(score, 0, 100);

  const needleRotation = healthScore * 1.8;

  const color = HEALTH_COLORS[healthLevel] || "#64748b";

  const segments = [
    {
      start: 0,
      end: 40,
      color: HEALTH_COLORS.Critical,
    },
    {
      start: 40,
      end: 60,
      color: HEALTH_COLORS.Poor,
    },
    {
      start: 60,
      end: 80,
      color: HEALTH_COLORS.Good,
    },
    {
      start: 80,
      end: 100,
      color: HEALTH_COLORS.Excellent,
    },
  ];

  return (
    <div
      className="card"
      style={{
        textAlign: "center",
        minHeight: 330,
      }}
    >
      <div className="stat-header">
        <span>Predicted Brood Health Status</span>
        <Gauge size={18} />
      </div>

      <svg
        viewBox="0 0 300 185"
        width="100%"
        role="img"
        aria-label={
          `Predicted brood health score ` + `${healthScore.toFixed(1)}`
        }
      >
        {segments.map((segment) => (
          <path
            key={`${segment.start}-${segment.end}`}
            d={arcPath(150, 140, 102, segment.start, segment.end)}
            fill="none"
            stroke={segment.color}
            strokeWidth="22"
            strokeLinecap="butt"
            opacity="0.9"
          />
        ))}

        <line
          x1="150"
          y1="140"
          x2="58"
          y2="140"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          style={{
            transformOrigin: "150px 140px",
            transform: `rotate(${needleRotation}deg)`,
            transition: "transform 900ms " + "cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        />

        <circle cx="150" cy="140" r="12" fill={color} />

        <circle cx="150" cy="140" r="5" fill="#0f172a" />

        <text x="47" y="169" fill="#94a3b8" fontSize="11">
          0
        </text>

        <text x="241" y="169" fill="#94a3b8" fontSize="11">
          100
        </text>

        <text
          x="150"
          y="103"
          textAnchor="middle"
          fill={color}
          fontSize="26"
          fontWeight="700"
        >
          {healthScore.toFixed(1)}
        </text>

        <text x="150" y="124" textAnchor="middle" fill="#cbd5e1" fontSize="12">
          {healthLevel}
        </text>
      </svg>

      <div
        style={{
          color,
          fontSize: "1.15rem",
          fontWeight: 700,
        }}
      >
        {healthLevel}
      </div>

      <div
        style={{
          color: "var(--text-secondary)",
          fontSize: "0.82rem",
          marginTop: 5,
        }}
      >
        Predicted brood condition in {forecastHorizonHours} hours
      </div>
    </div>
  );
}

export function BHSIVisual({ value = 0, stabilityLevel = "Low" }) {
  const score = clamp(value, 0, 100);
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const color = STABILITY_COLORS[stabilityLevel] || "#64748b";

  return (
    <div className="card" style={{ textAlign: "center", minHeight: 330 }}>
      <div className="stat-header">
        <span>Brood Health Stability Index</span>
        <Activity size={18} />
      </div>

      <svg
        viewBox="0 0 200 200"
        width="210"
        height="210"
        role="img"
        aria-label={`BHSI ${score.toFixed(1)}`}
      >
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke="rgba(148,163,184,0.18)"
          strokeWidth="18"
        />
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="18"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 100 100)"
          style={{ transition: "stroke-dashoffset 900ms ease" }}
        />
        <text
          x="100"
          y="94"
          textAnchor="middle"
          fill={color}
          fontSize="30"
          fontWeight="700"
        >
          {score.toFixed(1)}
        </text>
        <text x="100" y="118" textAnchor="middle" fill="#cbd5e1" fontSize="13">
          {stabilityLevel} stability
        </text>
      </svg>

      <div style={{ color, fontWeight: 700 }}>{stabilityLevel} Stability</div>
      <div
        style={{
          color: "var(--text-secondary)",
          fontSize: "0.82rem",
          marginTop: 5,
        }}
      >
        Internal temperature, humidity and CO₂ consistency over the last 6 hours
      </div>
    </div>
  );
}

export function RoDVisual({ value = 0, trendLabel = "Stable" }) {
  const rod = Number.isFinite(Number(value)) ? Number(value) : 0;
  const displayRod = clamp(rod, -6, 6);
  const position = ((displayRod + 6) / 12) * 100;
  const color = TREND_COLORS[trendLabel] || "#64748b";
  const TrendIcon =
    rod < -0.5 ? TrendingDown : rod > 0.5 ? TrendingUp : Activity;

  return (
    <div className="card" style={{ minHeight: 330 }}>
      <div className="stat-header">
        <span>Rate of Deterioration</span>
        <TrendIcon size={18} color={color} />
      </div>

      <div style={{ textAlign: "center", margin: "2.3rem 0 2rem" }}>
        <div style={{ color, fontSize: "2.4rem", fontWeight: 700 }}>
          {rod.toFixed(2)}
          <span style={{ fontSize: "0.85rem", marginLeft: 5 }}>pts/hr</span>
        </div>
        <div style={{ color, fontWeight: 700 }}>{trendLabel}</div>
      </div>

      <div style={{ position: "relative", padding: "1.2rem 0 2rem" }}>
        <div
          style={{
            height: 18,
            borderRadius: 999,
            background:
              "linear-gradient(90deg, #ef4444 0%, #f97316 25%, #64748b 50%, #34d399 75%, #10b981 100%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: `${position}%`,
            top: 4,
            width: 4,
            height: 42,
            borderRadius: 4,
            background: "#f8fafc",
            boxShadow: "0 0 0 4px rgba(248,250,252,0.18)",
            transform: "translateX(-50%)",
            transition: "left 900ms cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 12,
            color: "#94a3b8",
            fontSize: 11,
          }}
        >
          <span>Rapid decline</span>
          <span>Stable</span>
          <span>Improving</span>
        </div>
      </div>

      <div
        style={{
          color: "var(--text-secondary)",
          fontSize: "0.82rem",
          textAlign: "center",
        }}
      >
        Negative values indicate decline. Below −3 pts/hr is treated as rapid
        deterioration.
      </div>
    </div>
  );
}

export function EarlyWarningPanel({ warning }) {
  if (!warning) return null;
  const critical = warning.level === "Critical";
  const alerting = warning.is_alert;
  const color = HEALTH_COLORS[warning.level] || "#64748b";
  const Icon = critical || alerting ? AlertTriangle : CheckCircle2;

  return (
    <div
      className="card"
      style={{
        borderLeft: `5px solid ${color}`,
        background: `${color}12`,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "0.9rem" }}>
        <Icon size={28} color={color} style={{ flexShrink: 0, marginTop: 2 }} />
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, color }}>
            {warning.level} Brood Health Early-Warning Status:
          </h3>
          <p style={{ margin: "0.45rem 0", fontWeight: 600 }}>
            {warning.recommended_action}
          </p>
          <ul
            style={{
              margin: "0.4rem 0 0",
              paddingLeft: "1.2rem",
              color: "var(--text-secondary)",
            }}
          >
            {(warning.reasons || []).map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
