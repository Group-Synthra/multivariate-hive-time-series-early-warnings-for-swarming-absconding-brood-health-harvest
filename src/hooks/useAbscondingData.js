
import { useEffect, useState, useCallback } from 'react';

export function useAbscondingData() {
  const [abscondingData, setAbscondingData] = useState(null);
  const [abscondingLoading, setLoading] = useState(true);
  const [abscondingError, setError] = useState(null);

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

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { abscondingData, abscondingLoading, abscondingError, refetchAbsconding: fetchData };
}
