import React, { useState } from 'react';
import { ArrowRight, Copy, Check, Sparkles, BookOpen, Layers, Briefcase, Zap, ShieldCheck } from 'lucide-react';
import { TranslationResult } from '../types';
import { requestTranslation } from '../services/api';

interface TranslateTabProps {
  translationMode: string;
  customApiKey: string;
  token?: string;
  conversationId?: string;
  userMode: 'corporate' | 'genz';
  onTranslationComplete: (result: TranslationResult) => void;
  lastResult: TranslationResult | null;
}

export const TranslateTab: React.FC<TranslateTabProps> = ({
  translationMode,
  customApiKey,
  token,
  conversationId,
  userMode,
  onTranslationComplete,
  lastResult,
}) => {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const corporatePresets = [
    {
      label: 'Leverage Competencies',
      text: "Let's leverage our core competencies to move the needle on this deliverable.",
    },
    {
      label: 'Circle Back EOD',
      text: 'We need to circle back on this lowkey sus action item by EOD.',
    },
    {
      label: 'Paradigm Shift',
      text: 'This strategic initiative represents a paradigm shift for all key stakeholders.',
    },
  ];

  const genZPresets = [
    {
      label: 'Slapped Fr',
      text: 'No cap that proposal slapped fr, she ate and left no crumbs.',
    },
    {
      label: 'Lowkey Mid',
      text: 'That feature update was lowkey mid, not gonna lie.',
    },
    {
      label: 'Understood Assignment',
      text: 'The design team highkey understood the assignment, it’s giving luxury.',
    },
  ];

  const presets = userMode === 'corporate' ? corporatePresets : genZPresets;

  const handleTranslate = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const mode = translationMode === 'auto'
        ? (userMode === 'corporate' ? 'corporate_to_genz' : 'genz_to_corporate')
        : translationMode;

      const res = await requestTranslation(
        inputText.trim(),
        mode,
        customApiKey,
        token,
        conversationId
      );
      onTranslationComplete(res);
    } catch (err: any) {
      setError(err.message || 'Translation request failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (lastResult?.translation) {
      navigator.clipboard.writeText(lastResult.translation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="grid-2">
      {/* Input Pane */}
      <div className="glass-card" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {userMode === 'corporate' ? <Briefcase size={18} color="#3b82f6" /> : <Zap size={18} color="#ec4899" />}
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                {userMode === 'corporate' ? 'Corporate Speak Input' : 'Gen Z Slang Input'}
              </h2>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Tailored for {userMode === 'corporate' ? 'Business Professionals' : 'Gen Z Creators'}.
            </p>
          </div>
          <span className={userMode === 'corporate' ? 'badge badge-corp' : 'badge badge-genz'}>
            {userMode === 'corporate' ? 'Corporate Mode' : 'Gen Z Mode'}
          </span>
        </div>

        <div>
          <label className="label">Sample Presets</label>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {presets.map((preset) => (
              <button
                key={preset.label}
                id={`preset-${preset.label.toLowerCase().replace(/\s+/g, '-')}-btn`}
                className="btn btn-secondary btn-sm"
                style={{ flex: 1, minWidth: '130px' }}
                onClick={() => setInputText(preset.text)}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        <textarea
          id="translate-input-textarea"
          className="textarea-field"
          style={{ height: '180px', resize: 'vertical' }}
          placeholder={userMode === 'corporate' ? "Enter corporate executive jargon..." : "Enter Gen Z slang or culture phrases..."}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />

        <p style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.76rem' }}>
          <ShieldCheck size={14} color="var(--accent-primary)" />
          Language safety is active. Abusive content is blocked before processing.
        </p>

        {error && (
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '0.6rem',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              fontSize: '0.82rem',
            }}
          >
            {error}
          </div>
        )}

        <button
          id="translate-submit-btn"
          className="btn btn-primary"
          style={{ width: '100%', padding: '0.85rem' }}
          onClick={handleTranslate}
          disabled={loading || !inputText.trim()}
        >
          {loading ? (
            <span>Processing RAG Retrieval & Translation...</span>
          ) : (
            <>
              <Sparkles size={16} /> Translate to {userMode === 'corporate' ? 'Gen Z Slang' : 'Corporate English'} <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>

      {/* Output Pane */}
      <div className="glass-card" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              Translation Output
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              RAG-enhanced dialect mapping output.
            </p>
          </div>
          {lastResult && (
            <button
              id="copy-translation-btn"
              className="btn btn-secondary btn-sm"
              onClick={handleCopy}
              title="Copy Output"
            >
              {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}
        </div>

        {lastResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
              <span className="badge badge-accent">
                Direction: {lastResult.translation_direction}
              </span>
              <span className={lastResult.detected_style.toLowerCase().includes('gen') ? "badge badge-genz" : "badge badge-corp"}>
                Detected: {lastResult.detected_style}
              </span>
              {lastResult.saved_to_history && (
                <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
                  ✓ Saved to PostgreSQL history
                </span>
              )}
            </div>

            <div
              style={{
                padding: '1.25rem',
                borderRadius: '0.85rem',
                backgroundColor: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                fontSize: '1.1rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
                lineHeight: 1.6,
                minHeight: '100px',
              }}
            >
              {lastResult.translation}
            </div>

            {/* Terms Used */}
            {lastResult.terms_used && lastResult.terms_used.length > 0 && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  <BookOpen size={14} color="var(--accent-primary)" /> Terms & Definitions Mapped
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {lastResult.terms_used.map((t, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.5rem 0.75rem',
                        borderRadius: '0.5rem',
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-color)',
                        fontSize: '0.82rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <span style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>
                        {t.term || t.key || Object.keys(t)[0]}
                      </span>
                      <span style={{ color: 'var(--text-secondary)' }}>
                        {t.translation || t.meaning || Object.values(t)[0]}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Retrieved Context Docs */}
            {lastResult.retrieved_docs && lastResult.retrieved_docs.length > 0 && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  <Layers size={14} color="var(--accent-primary)" /> RAG Context Documents ({lastResult.retrieved_docs.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '180px', overflowY: 'auto' }}>
                  {lastResult.retrieved_docs.map((doc, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '0.6rem 0.8rem',
                        borderRadius: '0.5rem',
                        background: 'var(--bg-input)',
                        border: '1px solid var(--border-color)',
                        fontSize: '0.78rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
                        {doc.metadata?.term || `Doc #${idx + 1}`}
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)' }}>{doc.page_content}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div
            style={{
              height: '100%',
              minHeight: '260px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              textAlign: 'center',
              padding: '2rem',
              border: '2px dashed var(--border-color)',
              borderRadius: '0.85rem',
            }}
          >
            <Sparkles size={36} color="var(--text-muted)" style={{ marginBottom: '0.8rem', opacity: 0.5 }} />
            <p style={{ fontWeight: 600 }}>Enter text on the left and click Translate Now</p>
            <p style={{ fontSize: '0.78rem', marginTop: '0.3rem' }}>
              RAG will retrieve relevant terms from the knowledge base to generate accurate translations.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
