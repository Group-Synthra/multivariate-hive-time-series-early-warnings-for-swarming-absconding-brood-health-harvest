import { useState, useEffect } from 'react';

/**
 * useEDAData — fetches real EDA data from the Flask backend.
 * Returns { edaData, loading, error, refetch }
 */
export function useEDAData() {
  const [edaData, setEdaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/eda');
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}: ${res.statusText}`);
      }
      const data = await res.json();
      setEdaData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return { edaData, loading, error, refetch: fetchData };
}
