import React, { useEffect, useState } from 'react';
import { ShieldCheck, Check, X, AlertTriangle } from 'lucide-react';
import { SlangSuggestion } from '../types';
import { fetchAdminPendingSuggestions, approveSuggestion, rejectSuggestion } from '../services/api';

interface AdminReviewTabProps {
  token?: string;
  role: 'user' | 'admin';
}

export const AdminReviewTab: React.FC<AdminReviewTabProps> = ({ token, role }) => {
  const [suggestions, setSuggestions] = useState<SlangSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  // Form states for inline editing
  const [editForms, setEditForms] = useState<Record<string, SlangSuggestion>>({});
  const [rejectionReasons, setRejectionReasons] = useState<Record<string, string>>({});

  const loadPending = async () => {
    if (!token || role !== 'admin') return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAdminPendingSuggestions(token);
      setSuggestions(data);
      const initialForms: Record<string, SlangSuggestion> = {};
      data.forEach((item) => {
        initialForms[item.id] = { ...item };
      });
      setEditForms(initialForms);
    } catch (err: any) {
      setError(err.message || 'Failed to load pending admin review items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPending();
  }, [token, role]);

  const handleInputChange = (id: string, field: string, value: string) => {
    setEditForms((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: value },
    }));
  };

  const handleApprove = async (id: string) => {
    if (!token) return;
    const form = editForms[id];
    if (!form.term.trim() || !form.meaning.trim() || !form.translation.trim()) {
      alert('Term, meaning, and translation are required.');
      return;
    }

    setProcessingId(id);
    try {
      await approveSuggestion(id, form, token);
      await loadPending();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: string) => {
    if (!token) return;
    const reason = rejectionReasons[id] || '';

    setProcessingId(id);
    try {
      await rejectSuggestion(id, reason, token);
      await loadPending();
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  if (role !== 'admin') {
    return (
      <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', color: '#f87171' }}>
        <AlertTriangle size={36} style={{ marginBottom: '0.5rem' }} />
        <h2 style={{ fontSize: '1.2rem', fontWeight: 800 }}>Admin Access Required</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          You must be signed in with an administrator role to access the slang approval queue.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ padding: '1.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.5rem' }}>
        <ShieldCheck size={22} color="var(--accent-primary)" />
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            Admin Review Queue
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Review, edit, and index new user slang submissions directly into the RAG vector search engine.
          </p>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.8rem', borderRadius: '0.6rem', backgroundColor: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', fontSize: '0.85rem', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="skeleton" style={{ height: '160px' }} />
      ) : suggestions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          No pending slang submissions awaiting review.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {suggestions.map((item) => {
            const form = editForms[item.id] || item;
            return (
              <div
                key={item.id}
                style={{
                  padding: '1.5rem',
                  borderRadius: '0.85rem',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
                  <div>
                    <label className="label">Term</label>
                    <input
                      type="text"
                      className="input-field"
                      value={form.term}
                      onChange={(e) => handleInputChange(item.id, 'term', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label">Category</label>
                    <select
                      className="select-field"
                      value={form.category}
                      onChange={(e) => handleInputChange(item.id, 'category', e.target.value)}
                    >
                      <option value="Gen Z">Gen Z</option>
                      <option value="Corporate">Corporate</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label className="label">Meaning</label>
                    <textarea
                      className="textarea-field"
                      style={{ height: '65px' }}
                      value={form.meaning}
                      onChange={(e) => handleInputChange(item.id, 'meaning', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label">Opposite Translation</label>
                    <textarea
                      className="textarea-field"
                      style={{ height: '65px' }}
                      value={form.translation}
                      onChange={(e) => handleInputChange(item.id, 'translation', e.target.value)}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label className="label">Example</label>
                    <input
                      type="text"
                      className="input-field"
                      value={form.example || ''}
                      onChange={(e) => handleInputChange(item.id, 'example', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label">Rejection Reason (If rejecting)</label>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="Reason for rejecting..."
                      value={rejectionReasons[item.id] || ''}
                      onChange={(e) =>
                        setRejectionReasons({ ...rejectionReasons, [item.id]: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    style={{ borderColor: 'rgba(239,68,68,0.4)', color: '#f87171' }}
                    onClick={() => handleReject(item.id)}
                    disabled={processingId === item.id}
                  >
                    <X size={14} /> Reject
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleApprove(item.id)}
                    disabled={processingId === item.id}
                  >
                    <Check size={14} /> Approve & Index RAG
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
