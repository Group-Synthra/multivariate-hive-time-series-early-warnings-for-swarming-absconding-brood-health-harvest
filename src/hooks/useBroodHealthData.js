import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";

export const BROOD_HEALTH_API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

export const LIVE_REFRESH_MS = 10 * 60 * 1000;

function normaliseArray(value) {
  return Array.isArray(value) ? value : [];
}

function getApiError(error) {
  if (axios.isCancel(error) || error?.code === "ERR_CANCELED") {
    return null;
  }

  return (
    error?.response?.data?.error ||
    error?.response?.data?.message ||
    error?.message ||
    "Unable to load brood-health data."
  );
}

/**
 * Historical CSV hook used by the EDA page only.
 *
 * Data source:
 * backend/data/hive_data_with_features.csv
 */
export function useBroodHealthData({ hive = null, limit = 2000 } = {}) {
  const [summary, setSummary] = useState([]);
  const [healthLevels, setHealthLevels] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [loadedHive, setLoadedHive] = useState(null);

  const [summaryLoading, setSummaryLoading] = useState(true);

  const [metricsLoading, setMetricsLoading] = useState(false);

  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const defaultHive = summary[0]?.hive || null;
  const effectiveHive = hive || defaultHive;

  const refetch = useCallback(() => {
    setRefreshKey((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadSummaryAndLevels() {
      setSummaryLoading(true);
      setError(null);

      try {
        const [summaryResponse, levelsResponse] = await Promise.all([
          axios.get(`${BROOD_HEALTH_API_BASE}/brood_health/summary`, {
            signal: controller.signal,
          }),
          axios.get(`${BROOD_HEALTH_API_BASE}/brood_health/health-levels`, {
            signal: controller.signal,
          }),
        ]);

        const orderedSummary = normaliseArray(summaryResponse.data)
          .slice()
          .sort((first, second) =>
            String(first.hive).localeCompare(String(second.hive)),
          );

        setSummary(orderedSummary);
        setHealthLevels(normaliseArray(levelsResponse.data));
      } catch (requestError) {
        const message = getApiError(requestError);

        if (message) {
          setError(message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setSummaryLoading(false);
        }
      }
    }

    loadSummaryAndLevels();

    return () => {
      controller.abort();
    };
  }, [refreshKey]);

  useEffect(() => {
    if (!effectiveHive) {
      setMetrics([]);
      setLoadedHive(null);
      return undefined;
    }

    const controller = new AbortController();

    async function loadSelectedHiveMetrics() {
      setMetricsLoading(true);
      setError(null);

      try {
        const response = await axios.get(
          `${BROOD_HEALTH_API_BASE}/brood_health`,
          {
            params: {
              hive: effectiveHive,
              limit: Math.max(1, Number(limit) || 2000),
            },
            signal: controller.signal,
          },
        );

        const orderedMetrics = normaliseArray(response.data)
          .slice()
          .sort(
            (first, second) =>
              new Date(first.timestamp) - new Date(second.timestamp),
          );

        setMetrics(orderedMetrics);
        setLoadedHive(effectiveHive);
      } catch (requestError) {
        const message = getApiError(requestError);

        if (message) {
          setError(message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setMetricsLoading(false);
        }
      }
    }

    loadSelectedHiveMetrics();

    return () => {
      controller.abort();
    };
  }, [effectiveHive, limit, refreshKey]);

  const selectedSummary = useMemo(() => {
    return (
      summary.find((record) => String(record.hive) === String(effectiveHive)) ||
      null
    );
  }, [summary, effectiveHive]);

  const waitingForSelectedHive = Boolean(
    effectiveHive && String(loadedHive) !== String(effectiveHive),
  );

  return {
    data: {
      metrics,
      summary,
      healthLevels,
      defaultHive,
      effectiveHive,
      selectedSummary,
      dataSource: "historical_csv",
    },

    loading: summaryLoading || metricsLoading || waitingForSelectedHive,

    summaryLoading,
    metricsLoading,
    error,
    refetch,
  };
}

/**
 * Live PostgreSQL hook used by the IoT early-warning page.
 *
 * Every refresh requests one complete dashboard payload from Flask.
 * The Flask backend reads public.beehive_readings, calculates the
 * current health score, BHSI and RoD, and predicts future brood risk
 * with the selected model trained using the historical CSV dataset.
 */
export function useBroodHealthIoTData({
  hive = null,
  historyHours = 168,
  timelinePoints = 144,
  pollIntervalMs = LIVE_REFRESH_MS,
} = {}) {
  const [hives, setHives] = useState([]);
  const [databaseStatus, setDatabaseStatus] = useState(null);

  const [dashboard, setDashboard] = useState(null);

  const [loadingHives, setLoadingHives] = useState(true);

  const [loadingDashboard, setLoadingDashboard] = useState(false);

  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const [lastSuccessfulRefresh, setLastSuccessfulRefresh] = useState(null);

  const requestSequence = useRef(0);

  const defaultHive = hives[0]?.hive || null;
  const effectiveHive = hive || defaultHive;

  const refetch = useCallback(() => {
    setRefreshKey((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadConnectionAndHives() {
      setLoadingHives(true);
      setError(null);

      try {
        const [statusResponse, hivesResponse] = await Promise.all([
          axios.get(`${BROOD_HEALTH_API_BASE}/brood_health/iot/status`, {
            signal: controller.signal,
          }),
          axios.get(`${BROOD_HEALTH_API_BASE}/brood_health/iot/hives`, {
            signal: controller.signal,
          }),
        ]);

        setDatabaseStatus(statusResponse.data);

        const orderedHives = normaliseArray(hivesResponse.data)
          .slice()
          .sort((first, second) =>
            String(first.hive).localeCompare(String(second.hive)),
          );

        setHives(orderedHives);
      } catch (requestError) {
        const message = getApiError(requestError);

        if (message) {
          setError(message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingHives(false);
        }
      }
    }

    loadConnectionAndHives();

    return () => {
      controller.abort();
    };
  }, [refreshKey]);

  const loadDashboard = useCallback(
    async ({ signal } = {}) => {
      if (!effectiveHive) {
        return null;
      }

      const sequence = requestSequence.current + 1;

      requestSequence.current = sequence;

      setLoadingDashboard(true);
      setError(null);

      try {
        const response = await axios.get(
          `${BROOD_HEALTH_API_BASE}/brood_health/iot/dashboard`,
          {
            params: {
              hive: effectiveHive,

              hours: Math.max(25, Number(historyHours) || 168),

              timeline_points: Math.max(24, Number(timelinePoints) || 144),
            },
            signal,
          },
        );

        if (sequence === requestSequence.current) {
          setDashboard(response.data);
          setLastSuccessfulRefresh(new Date());
        }

        return response.data;
      } catch (requestError) {
        const message = getApiError(requestError);

        if (message && sequence === requestSequence.current) {
          setError(message);
        }

        return null;
      } finally {
        if (sequence === requestSequence.current) {
          setLoadingDashboard(false);
        }
      }
    },
    [effectiveHive, historyHours, timelinePoints],
  );

  useEffect(() => {
    if (!effectiveHive) {
      setDashboard(null);
      return undefined;
    }

    const controller = new AbortController();

    setDashboard(null);

    loadDashboard({
      signal: controller.signal,
    });

    return () => {
      controller.abort();
    };
  }, [effectiveHive, refreshKey, loadDashboard]);

  useEffect(() => {
    if (!pollIntervalMs || pollIntervalMs < 60_000) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      loadDashboard();
    }, pollIntervalMs);

    return () => {
      window.clearInterval(interval);
    };
  }, [pollIntervalMs, loadDashboard]);

  const selectedHiveInfo = useMemo(() => {
    return (
      hives.find((record) => String(record.hive) === String(effectiveHive)) ||
      null
    );
  }, [hives, effectiveHive]);

  return {
    data: {
      hives,
      databaseStatus,
      dashboard,
      defaultHive,
      effectiveHive,
      selectedHiveInfo,
      lastSuccessfulRefresh,
      dataSource: "postgresql_iot",
    },

    loading: loadingHives || loadingDashboard,

    loadingHives,
    loadingDashboard,
    error,
    refetch,

    refreshDashboard: loadDashboard,
  };
}
