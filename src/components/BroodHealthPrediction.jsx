import React from 'react';
import { Zap, WifiOff } from 'lucide-react';

export default function BroodHealthPrediction() {
  return (
    <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
      <Zap size={48} color="var(--accent-gold)" style={{ marginBottom: '1rem' }} />
      <h3>Live Prediction with IoT Data</h3>
      <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto' }}>
        This module will connect to real‑time Sri Lankan hive sensors (temperature, humidity, CO₂, weight)
        and use the trained machine learning model to predict the Brood Health Score on the fly.
      </p>
      <div style={{ marginTop: '2rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '1rem' }}>
        <WifiOff size={24} color="var(--text-muted)" />
        <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Waiting for IoT data stream integration...</p>
      </div>
    </div>
  );
}