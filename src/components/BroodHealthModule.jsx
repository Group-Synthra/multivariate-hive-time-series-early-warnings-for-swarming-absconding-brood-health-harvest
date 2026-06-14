import React, { useState } from 'react';
import { Heart, BarChart3, Brain, Zap } from 'lucide-react';
import BroodHealthExploratory from './BroodHealthExploratory'; 
import BroodHealthTraining from './BroodHealthTraining';
import BroodHealthPrediction from './BroodHealthPrediction';  

export default function BroodHealthModule() {
  const [activeTab, setActiveTab] = useState('exploratory');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Tabs Navigation */}
      <div className="card" style={{ padding: '0.5rem', display: 'flex', gap: '0.5rem', background: 'rgba(0,0,0,0.2)' }}>
        <button
          onClick={() => setActiveTab('exploratory')}
          className={`tab-btn ${activeTab === 'exploratory' ? 'active' : ''}`}
          style={{ flex: 1, padding: '0.75rem', background: activeTab === 'exploratory' ? 'var(--accent-emerald)' : 'transparent', color: activeTab === 'exploratory' ? '#0f172a' : 'var(--text-secondary)', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
        >
          <BarChart3 size={18} /> Exploratory Analysis
        </button>
        <button
          onClick={() => setActiveTab('training')}
          className={`tab-btn ${activeTab === 'training' ? 'active' : ''}`}
          style={{ flex: 1, padding: '0.75rem', background: activeTab === 'training' ? 'var(--accent-cyan)' : 'transparent', color: activeTab === 'training' ? '#0f172a' : 'var(--text-secondary)', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
        >
          <Brain size={18} /> Model Training
        </button>
        <button
          onClick={() => setActiveTab('prediction')}
          className={`tab-btn ${activeTab === 'prediction' ? 'active' : ''}`}
          style={{ flex: 1, padding: '0.75rem', background: activeTab === 'prediction' ? 'var(--accent-gold)' : 'transparent', color: activeTab === 'prediction' ? '#0f172a' : 'var(--text-secondary)', border: 'none', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
        >
          <Zap size={18} /> Live Prediction (IoT)
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'exploratory' && <BroodHealthExploratory />}
      {activeTab === 'training' && <BroodHealthTraining />}
      {activeTab === 'prediction' && <BroodHealthPrediction />}
    </div>
  );
}