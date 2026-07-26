import { useEffect, useState, useCallback } from 'react';

export function useAbscondingData() {
  const [abscondingData, setAbscondingData] = useState(null);
  const [abscondingLoading, setLoading] = useState(true);
  const [abscondingError, setError] = useState(null);

  const [iotLiveData, setIotLiveData] = useState(null);
  const [iotLiveLoading, setIotLiveLoading] = useState(false);
  const [iotLiveError, setIotLiveError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/absconding/summary');
      if (!response.ok) {
        throw new Error('Absconding module data not generated. Run python backend/scripts/run_absconding.py');
      }
      const json = await response.json();
      setAbscondingData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchIotLive = useCallback(async () => {
    try {
      setIotLiveLoading(true);
      setIotLiveError(null);
      const response = await fetch('/api/absconding/iot/live');
      const json = await response.json();
      if (!response.ok) {
        throw new Error(json?.error || 'Live IoT prediction is not configured yet.');
      }
      setIotLiveData(json);
    } catch (err) {
      setIotLiveError(err.message);
    } finally {
      setIotLiveLoading(false);
    }
  }, []);

  const ingestTestIotReading = useCallback(async (reading) => {
    const response = await fetch('/api/absconding/iot/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reading),
    });
    const json = await response.json();
    if (!response.ok) {
      throw new Error(json?.error || 'Failed to save IoT reading.');
    }
    await fetchIotLive();
    return json;
  }, [fetchIotLive]);

  useEffect(() => {
    fetchData();
    fetchIotLive();
  }, [fetchData, fetchIotLive]);

  // IoT data is collected every 10 minutes. The frontend checks once per minute
  // so the dashboard updates shortly after a new database row arrives.
  useEffect(() => {
    const interval = setInterval(fetchIotLive, 60000);
    return () => clearInterval(interval);
  }, [fetchIotLive]);

  return {
    abscondingData,
    abscondingLoading,
    abscondingError,
    refetchAbsconding: fetchData,
    iotLiveData,
    iotLiveLoading,
    iotLiveError,
    refetchIotLive: fetchIotLive,
    ingestTestIotReading,
  };
}
