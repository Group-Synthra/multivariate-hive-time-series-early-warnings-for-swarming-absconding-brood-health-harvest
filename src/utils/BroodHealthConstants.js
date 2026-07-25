export const HEALTH_COLORS = {
  Critical: "#ef4444",
  Poor: "#f97316",
  Good: "#34d399",
  Excellent: "#10b981",
};

export const HEALTH_LEVELS = [
  {
    level: "Critical",
    displayRange: "0-39",
    rule: "0 ≤ score < 40",
    minimum: 0,
    maximum: 40,
    description: "Critical conditions. Immediate inspection is required.",
  },
  {
    level: "Poor",
    displayRange: "40-59",
    rule: "40 ≤ score < 60",
    minimum: 40,
    maximum: 60,
    description: "Poor conditions. Hive intervention is recommended soon.",
  },
  {
    level: "Good",
    displayRange: "60-79",
    rule: "60 ≤ score < 80",
    minimum: 60,
    maximum: 80,
    description: "Generally favourable conditions with continued monitoring.",
  },
  {
    level: "Excellent",
    displayRange: "80-100",
    rule: "80 ≤ score ≤ 100",
    minimum: 80,
    maximum: 100,
    description: "Stable conditions favourable for brood development.",
  },
].map((item) => ({
  ...item,
  color: HEALTH_COLORS[item.level],
}));

export const STABILITY_COLORS = {
  High: "#10b981",
  Moderate: "#f59e0b",
  Low: "#ef4444",
};

export const TREND_COLORS = {
  "Rapid Improving": "#10b981",
  "Slow Improving": "#34d399",
  Stable: "#64748b",
  "Slow Declining": "#f97316",
  "Rapid Declining": "#ef4444",
};

/**
 * BHSI stability classifications.
 */
export const STABILITY_LEVELS = [
  {
    level: "High",
    displayRange: "70-100",
    minimum: 70,
    maximum: 100,
    description: "The internal brood environment is stable.",
  },
  {
    level: "Moderate",
    displayRange: "40-69",
    minimum: 40,
    maximum: 70,
    description: "Some instability exists and the hive should be monitored.",
  },
  {
    level: "Low",
    displayRange: "0-39",
    minimum: 0,
    maximum: 40,
    description:
      "The brood environment is unstable and may precede health deterioration.",
  },
].map((item) => ({
  ...item,
  color: STABILITY_COLORS[item.level],
}));

/**
 * RoD represents the change in brood-health score per hour.
 */
export const ROD_LEVELS = [
  {
    level: "Rapid Improving",
    minimum: 3,
    maximum: Number.POSITIVE_INFINITY,
    description: "The brood-health score is improving rapidly.",
  },
  {
    level: "Slow Improving",
    minimum: 0.5,
    maximum: 3,
    description: "The brood-health score is gradually improving.",
  },
  {
    level: "Stable",
    minimum: -0.5,
    maximum: 0.5,
    description: "No significant health-score change is currently detected.",
  },
  {
    level: "Slow Declining",
    minimum: -3,
    maximum: -0.5,
    description: "The brood-health score is gradually declining.",
  },
  {
    level: "Rapid Declining",
    minimum: Number.NEGATIVE_INFINITY,
    maximum: -3,
    description:
      "The brood-health score is declining rapidly and requires urgent attention.",
  },
].map((item) => ({
  ...item,
  color: TREND_COLORS[item.level],
}));

export function getHealthLevel(score) {
  const numericScore = Number(score);

  if (!Number.isFinite(numericScore)) {
    return null;
  }

  if (numericScore >= 80) {
    return "Excellent";
  }

  if (numericScore >= 60) {
    return "Good";
  }

  if (numericScore >= 40) {
    return "Poor";
  }

  return "Critical";
}

export function getRiskLevel(riskPercentage) {
  const risk = Number(riskPercentage);

  if (!Number.isFinite(risk)) {
    return null;
  }

  if (risk > 60) {
    return "Critical";
  }

  if (risk > 40) {
    return "High";
  }

  if (risk > 20) {
    return "Moderate";
  }

  return "Low";
}

export function getStabilityLevel(bhsi) {
  const value = Number(bhsi);

  if (!Number.isFinite(value)) {
    return null;
  }

  if (value >= 70) {
    return "High";
  }

  if (value >= 40) {
    return "Moderate";
  }

  return "Low";
}

export function getTrendLevel(rod) {
  const value = Number(rod);

  if (!Number.isFinite(value)) {
    return null;
  }

  if (value > 3) {
    return "Rapid Improving";
  }

  if (value > 0.5) {
    return "Slow Improving";
  }

  if (value >= -0.5) {
    return "Stable";
  }

  if (value >= -3) {
    return "Slow Declining";
  }

  return "Rapid Declining";
}

export function clampPercentage(value) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return 0;
  }

  return Math.min(100, Math.max(0, numericValue));
}
