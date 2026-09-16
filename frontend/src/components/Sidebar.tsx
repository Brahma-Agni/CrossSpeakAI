import React from 'react';
import { Settings, Key, RotateCcw, PlusCircle, Layers } from 'lucide-react';
import { ConfigResponse } from '../types';

interface SidebarProps {
  config: ConfigResponse | null;
  translationMode: string;
  setTranslationMode: (mode: string) => void;
  customApiKey: string;
  setCustomApiKey: (key: string) => void;
  historyCount: number;
  onClearLocalHistory: () => void;
  onNewConversation: () => void;
  isLoggedIn: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  config,
  translationMode,
  setTranslationMode,
  customApiKey,
  setCustomApiKey,
  historyCount,
  onClearLocalHistory,
  onNewConversation,
  isLoggedIn,
}) => {
  const modeOptions = config?.translation_modes || [
    { label: 'Auto-detect style', value: 'auto' },
    { label: 'Corporate to Gen Z', value: 'corporate_to_genz' },
    { label: 'Gen Z to Corporate', value: 'genz_to_corporate' },
  ];

  return (
    <aside
      className="glass-card"
      style={{
        width: '320px',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        height: 'fit-content',
        position: 'sticky',
        top: '1.5rem',
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <Settings size={18} color="var(--accent-primary)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Translation Settings
          </h2>
        </div>

        <label className="label">Translation Mode</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          {modeOptions.map((opt) => (
            <label
              key={opt.value}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                padding: '0.55rem 0.8rem',
                borderRadius: '0.6rem',
                background: translationMode === opt.value ? 'var(--accent-glow)' : 'transparent',
                border: `1px solid ${translationMode === opt.value ? 'var(--accent-primary)' : 'transparent'}`,
                cursor: 'pointer',
                fontSize: '0.88rem',
                fontWeight: translationMode === opt.value ? 700 : 500,
                color: translationMode === opt.value ? 'var(--accent-primary)' : 'var(--text-secondary)',
                transition: 'all 0.2s ease',
              }}
            >
              <input
                type="radio"
                name="translationMode"
                value={opt.value}
                checked={translationMode === opt.value}
                onChange={() => setTranslationMode(opt.value)}
                style={{ accentColor: 'var(--accent-primary)' }}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>

      <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)' }} />

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.8rem' }}>
          <Key size={18} color="var(--accent-primary)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            AI Service
          </h2>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.6rem' }}>
          {config?.gemini_api_keys_count ? (
            <span style={{ color: '#10b981', fontWeight: 600 }}>
              ✓ Connected with {config.gemini_api_keys_count} shared key(s)
            </span>
          ) : (
            <span>No shared key configured</span>
          )}
        </div>

        <label className="label">Personal Gemini API Key (Optional)</label>
        <input
          id="custom-api-key-input"
          type="password"
          className="input-field"
          placeholder="AIzaSy..."
          value={customApiKey}
          onChange={(e) => setCustomApiKey(e.target.value)}
        />
        <p style={{ fontSize: '0.73rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
          Your key remains local in your session browser.
        </p>
      </div>

      <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)' }} />

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.8rem' }}>
          <Layers size={18} color="var(--accent-primary)" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Current Session
          </h2>
        </div>

        <div style={{ background: 'var(--bg-input)', padding: '0.8rem 1rem', borderRadius: '0.75rem', border: '1px solid var(--border-color)', marginBottom: '0.8rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
            Translations Done
          </span>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            {historyCount}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            id="clear-history-btn"
            className="btn btn-secondary btn-sm"
            onClick={onClearLocalHistory}
            style={{ width: '100%' }}
          >
            <RotateCcw size={14} /> Clear Local History
          </button>

          {isLoggedIn && (
            <button
              id="new-conversation-btn"
              className="btn btn-primary btn-sm"
              onClick={onNewConversation}
              style={{ width: '100%' }}
            >
              <PlusCircle size={14} /> New Conversation
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};
