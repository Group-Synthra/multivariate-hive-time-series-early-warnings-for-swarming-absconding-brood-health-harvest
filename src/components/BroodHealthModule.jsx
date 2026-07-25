import React, { useState } from 'react';
import { BarChart3, Brain, Zap } from 'lucide-react';
import BroodHealthExploratory from './BroodHealthExploratory';
import BroodHealthPrediction from './BroodHealthPrediction';
import BroodHealthTraining from './BroodHealthTraining';

const TABS = [
  {
    id: 'exploratory',
    label: 'Exploratory Analysis',
    Icon: BarChart3,
    accent: 'var(--accent-emerald)',
  },
  {
    id: 'training',
    label: 'Model Training',
    Icon: Brain,
    accent: 'var(--accent-cyan)',
  },
  {
    id: 'prediction',
    label: 'Live Early Warning (IoT)',
    Icon: Zap,
    accent: 'var(--accent-gold)',
  },
];

export default function BroodHealthModule() {
  const [activeTab, setActiveTab] = useState('exploratory');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div
        className="card"
        role="tablist"
        aria-label="Brood health module sections"
        style={{
          padding: '0.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem',
          background: 'rgba(0,0,0,0.2)',
        }}
      >
        {TABS.map(({ id, label, Icon, accent }) => {
          const active = activeTab === id;
          return (
            <button
              type="button"
              role="tab"
              aria-selected={active}
              aria-controls={`brood-health-panel-${id}`}
              key={id}
              onClick={() => setActiveTab(id)}
              className={`tab-btn ${active ? 'active' : ''}`}
              style={{
                flex: '1 1 210px',
                padding: '0.75rem',
                background: active ? accent : 'transparent',
                color: active ? '#0f172a' : 'var(--text-secondary)',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                fontWeight: 600,
              }}
            >
              <Icon size={18} /> {label}
            </button>
          );
        })}
      </div>

      <section
        id={`brood-health-panel-${activeTab}`}
        role="tabpanel"
        aria-label={TABS.find((tab) => tab.id === activeTab)?.label}
      >
        {activeTab === 'exploratory' && <BroodHealthExploratory />}
        {activeTab === 'training' && <BroodHealthTraining />}
        {activeTab === 'prediction' && <BroodHealthPrediction />}
      </section>
    </div>
  );
}