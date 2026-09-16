import React, { useEffect, useState } from 'react';
import { Clock, MessageSquare, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import { HistoryItem, TranslationResult } from '../types';
import { fetchHistory } from '../services/api';

interface HistoryTabProps {
  token?: string;
  localHistory: TranslationResult[];
}

export const HistoryTab: React.FC<HistoryTabProps> = ({ token, localHistory }) => {
  const [remoteHistory, setRemoteHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

  useEffect(() => {
    if (token) {
      setLoading(true);
      setError(null);
      fetchHistory(token)
        .then((data) => setRemoteHistory(data))
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [token]);

  const toggleExpand = (idx: number) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div className="glass-card" style={{ padding: '1.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.5rem' }}>
        <Clock size={20} color="var(--accent-primary)" />
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            Translation History
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {token ? 'Saved account history across sessions.' : 'Translations performed in this browser session.'}
          </p>
        </div>
      </div>

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div className="skeleton" style={{ height: '60px' }} />
          <div className="skeleton" style={{ height: '60px' }} />
        </div>
      )}

      {error && (
        <div
          style={{
            padding: '0.8rem 1rem',
            borderRadius: '0.6rem',
            backgroundColor: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            color: '#fbbf24',
            fontSize: '0.85rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <AlertCircle size={16} /> Saved remote history unavailable; showing session history instead. ({error})
        </div>
      )}

      {token && !loading && remoteHistory.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          {remoteHistory.map((item, idx) => (
            <div
              key={item.id || idx}
              style={{
                borderRadius: '0.75rem',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-input)',
                overflow: 'hidden',
              }}
            >
              <button
                onClick={() => toggleExpand(idx)}
                style={{
                  width: '100%',
                  padding: '1rem 1.25rem',
                  background: 'none',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  color: 'var(--text-primary)',
                  textAlign: 'left',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span className="badge badge-accent">#{remoteHistory.length - idx}</span>
                  <span className="badge badge-corp">{item.translation_direction}</span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {item.created_at ? new Date(item.created_at).toLocaleString() : ''}
                  </span>
                </div>
                {expandedIndex === idx ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>

              {expandedIndex === idx && (
                <div style={{ padding: '0 1.25rem 1.25rem 1.25rem', borderTop: '1px solid var(--border-color)' }}>
                  <div style={{ marginTop: '0.8rem', fontSize: '0.9rem' }}>
                    <div style={{ fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Input:</div>
                    <div style={{ color: 'var(--text-primary)', background: 'var(--bg-card)', padding: '0.6rem 0.8rem', borderRadius: '0.5rem', marginBottom: '0.8rem' }}>
                      {item.input_text}
                    </div>
                    <div style={{ fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.2rem' }}>Result:</div>
                    <div style={{ color: 'var(--text-primary)', background: 'var(--bg-card)', padding: '0.6rem 0.8rem', borderRadius: '0.5rem', fontWeight: 600 }}>
                      {item.output_text}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {(!token || remoteHistory.length === 0) && !loading && (
        <div>
          {localHistory.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <MessageSquare size={36} style={{ opacity: 0.5, marginBottom: '0.5rem' }} />
              <p>No translations recorded in this session yet.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              {localHistory.slice().reverse().map((res, idx) => (
                <div
                  key={idx}
                  style={{
                    borderRadius: '0.75rem',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-input)',
                    padding: '1.25rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.75rem' }}>
                    <span className="badge badge-accent">Session Item #{localHistory.length - idx}</span>
                    <span className="badge badge-corp">{res.translation_direction}</span>
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {res.translation}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
