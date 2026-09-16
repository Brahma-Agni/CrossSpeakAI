import React, { useEffect, useState } from 'react';
import { Send, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { SlangSuggestion } from '../types';
import { submitSlangSuggestion, fetchUserSuggestions } from '../services/api';

interface SuggestSlangTabProps {
  token?: string;
  onOpenAuth: () => void;
}

export const SuggestSlangTab: React.FC<SuggestSlangTabProps> = ({ token, onOpenAuth }) => {
  const [term, setTerm] = useState('');
  const [category, setCategory] = useState('Gen Z');
  const [meaning, setMeaning] = useState('');
  const [translation, setTranslation] = useState('');
  const [example, setExample] = useState('');
  const [context, setContext] = useState('');

  const [submissions, setSubmissions] = useState<SlangSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadSubmissions = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await fetchUserSuggestions(token);
      setSubmissions(data);
    } catch (err: any) {
      console.warn('Failed to load user submissions', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSubmissions();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      onOpenAuth();
      return;
    }
    setError(null);
    setSuccess(null);

    if (!term.trim() || !meaning.trim() || !translation.trim()) {
      setError('Term, meaning, and translation are required.');
      return;
    }

    setSubmitting(true);
    try {
      await submitSlangSuggestion(
        {
          term: term.trim(),
          category,
          meaning: meaning.trim(),
          translation: translation.trim(),
          example: example.trim(),
          context: context.trim(),
        },
        token
      );
      setSuccess('Suggestion submitted successfully for admin review!');
      setTerm('');
      setMeaning('');
      setTranslation('');
      setExample('');
      setContext('');
      loadSubmissions();
    } catch (err: any) {
      setError(err.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <div className="glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
          Recommend New Slang or Terminology
        </h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', maxWidth: '500px', margin: '0 auto 1.5rem' }}>
          Sign in to submit new corporate jargon or Gen Z slang phrases to be reviewed by admins and added to the RAG vector index.
        </p>
        <button className="btn btn-primary" onClick={onOpenAuth}>
          Sign In to Submit Slang
        </button>
      </div>
    );
  }

  return (
    <div className="grid-2">
      {/* Submission Form */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
          Recommend New Slang
        </h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          Submit terms to expand Cross Speak AI's RAG knowledge base.
        </p>

        {error && (
          <div style={{ padding: '0.75rem', borderRadius: '0.6rem', backgroundColor: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', fontSize: '0.85rem', marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        {success && (
          <div style={{ padding: '0.75rem', borderRadius: '0.6rem', backgroundColor: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)', color: '#34d399', fontSize: '0.85rem', marginBottom: '1rem' }}>
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.75rem' }}>
            <div>
              <label className="label">Term / Phrase *</label>
              <input
                id="slang-term-input"
                type="text"
                className="input-field"
                placeholder="e.g. Touch base"
                value={term}
                onChange={(e) => setTerm(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label">Category *</label>
              <select
                id="slang-category-select"
                className="select-field"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="Gen Z">Gen Z</option>
                <option value="Corporate">Corporate</option>
              </select>
            </div>
          </div>

          <div>
            <label className="label">Meaning *</label>
            <textarea
              id="slang-meaning-textarea"
              className="textarea-field"
              style={{ height: '70px' }}
              placeholder="What does this phrase mean?"
              value={meaning}
              onChange={(e) => setMeaning(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="label">Opposite-Style Translation *</label>
            <textarea
              id="slang-translation-textarea"
              className="textarea-field"
              style={{ height: '70px' }}
              placeholder="How would the other dialect say this?"
              value={translation}
              onChange={(e) => setTranslation(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="label">Example Usage (Optional)</label>
            <input
              id="slang-example-input"
              type="text"
              className="input-field"
              placeholder="Example sentence using the term"
              value={example}
              onChange={(e) => setExample(e.target.value)}
            />
          </div>

          <div>
            <label className="label">Context / Tone Notes (Optional)</label>
            <input
              id="slang-context-input"
              type="text"
              className="input-field"
              placeholder="e.g. Sarcastic, formal email context"
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
          </div>

          <button
            id="slang-submit-btn"
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
            style={{ width: '100%', marginTop: '0.5rem' }}
          >
            <Send size={16} /> Submit for Review
          </button>
        </form>
      </div>

      {/* User Submission Tracker */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
          Your Submissions
        </h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>
          Track the approval status of your recommended terms.
        </p>

        {loading ? (
          <div className="skeleton" style={{ height: '120px' }} />
        ) : submissions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            You haven't submitted any terms yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {submissions.map((item) => (
              <div
                key={item.id}
                style={{
                  padding: '1rem',
                  borderRadius: '0.75rem',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                    {item.term}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                    {item.meaning}
                  </div>
                </div>
                <div>
                  {item.status === 'approved' ? (
                    <span className="badge" style={{ backgroundColor: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' }}>
                      <CheckCircle2 size={12} style={{ marginRight: '3px' }} /> Approved
                    </span>
                  ) : item.status === 'rejected' ? (
                    <span className="badge" style={{ backgroundColor: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}>
                      <AlertCircle size={12} style={{ marginRight: '3px' }} /> Rejected
                    </span>
                  ) : (
                    <span className="badge" style={{ backgroundColor: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' }}>
                      <Clock size={12} style={{ marginRight: '3px' }} /> Pending Review
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
