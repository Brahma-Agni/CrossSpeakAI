import React from 'react';
import { CheckCircle2, Key, Layers, PlusCircle, RotateCcw } from 'lucide-react';
import { ConfigResponse } from '../types';

interface SidebarProps {
  config: ConfigResponse | null;
  customApiKey: string;
  setCustomApiKey: (key: string) => void;
  historyCount: number;
  onClearLocalHistory: () => void;
  onNewConversation: () => void;
  plan: 'free' | 'paid';
  usageCount: number;
  usageLimit: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  config,
  customApiKey,
  setCustomApiKey,
  historyCount,
  onClearLocalHistory,
  onNewConversation,
  plan,
  usageCount,
  usageLimit,
}) => {
  const connected = Boolean(config?.gemini_api_keys_count || customApiKey);

  return (
    <aside className="workspace-sidebar" aria-label="Workspace utilities">
      <section className="glass-card sidebar-card">
        <div className="sidebar-card-heading">
          <Key size={18} />
          <div>
            <h2>AI Service</h2>
            <p>Translation engine status</p>
          </div>
        </div>

        <div className={`service-status ${connected ? 'connected' : ''}`}>
          <CheckCircle2 size={17} />
          <div>
            <strong>{connected ? 'Gemini connected' : 'Shared service unavailable'}</strong>
            <span>
              {customApiKey
                ? 'Using your personal key'
                : config?.gemini_api_keys_count
                  ? `${config.gemini_api_keys_count} shared keys available`
                  : 'Add a personal key to continue'}
            </span>
          </div>
        </div>

        <details className="service-key-details">
          <summary>Use a personal API key</summary>
          <label className="label" htmlFor="custom-api-key-input">Gemini API Key</label>
          <input
            id="custom-api-key-input"
            type="password"
            className="input-field"
            placeholder="AIzaSy..."
            value={customApiKey}
            onChange={(event) => setCustomApiKey(event.target.value)}
          />
          <p>Your key stays in this browser session.</p>
        </details>
      </section>

      <section className="glass-card sidebar-card">
        <div className="sidebar-card-heading">
          <Layers size={18} />
          <div>
            <h2>Current Session</h2>
            <p>Your workspace at a glance</p>
          </div>
        </div>

        <div className="session-stats">
          <div>
            <strong>{historyCount}</strong>
            <span>Session translations</span>
          </div>
          <div>
            <strong>{plan === 'paid' ? '∞' : `${usageCount}/${usageLimit}`}</strong>
            <span>{plan === 'paid' ? 'Paid access' : 'Free usage'}</span>
          </div>
        </div>

        <div className="sidebar-actions">
          <button id="new-conversation-btn" className="btn btn-primary btn-sm" onClick={onNewConversation}>
            <PlusCircle size={15} /> New conversation
          </button>
          <button id="clear-history-btn" className="btn btn-secondary btn-sm" onClick={onClearLocalHistory} disabled={!historyCount}>
            <RotateCcw size={14} /> Clear session
          </button>
        </div>
      </section>
    </aside>
  );
};
