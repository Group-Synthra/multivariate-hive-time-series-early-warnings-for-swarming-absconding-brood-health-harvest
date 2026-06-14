import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

export function useBroodHealthData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [metricsRes, summaryRes] = await Promise.all([
        axios.get(`${API_BASE}/brood_health`),
        axios.get(`${API_BASE}/brood_health/summary`)
      ]);
      setData({
        metrics: metricsRes.data,
        summary: summaryRes.data
      });
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return { data, loading, error, refetch: fetchData };
}