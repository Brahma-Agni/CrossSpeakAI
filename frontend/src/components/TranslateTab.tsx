import React, { useState } from 'react';
import { ArrowRight, BookOpen, Briefcase, Check, Copy, Layers, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import { TranslationResult } from '../types';
import { requestTranslation } from '../services/api';

interface TranslateTabProps {
  customApiKey: string;
  token?: string;
  conversationId?: string;
  userMode: 'corporate' | 'genz';
  onTranslationComplete: (result: TranslationResult) => void;
  lastResult: TranslationResult | null;
}

export const TranslateTab: React.FC<TranslateTabProps> = ({
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
    ['Leverage competencies', "Let's leverage our core competencies to move the needle on this deliverable."],
    ['Circle back EOD', 'We need to circle back on this lowkey sus action item by EOD.'],
    ['Paradigm shift', 'This strategic initiative represents a paradigm shift for all key stakeholders.'],
  ];
  const genZPresets = [
    ['Slapped fr', 'No cap that proposal slapped fr, she ate and left no crumbs.'],
    ['Lowkey mid', 'That feature update was lowkey mid, not gonna lie.'],
    ['Understood assignment', 'The design team highkey understood the assignment, it’s giving luxury.'],
  ];
  const presets = userMode === 'corporate' ? corporatePresets : genZPresets;
  const sourceLabel = userMode === 'corporate' ? 'Corporate English' : 'Gen Z language';
  const targetLabel = userMode === 'corporate' ? 'Gen Z language' : 'Corporate English';

  const handleTranslate = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await requestTranslation(
        inputText.trim(),
        userMode === 'corporate' ? 'corporate_to_genz' : 'genz_to_corporate',
        customApiKey,
        token,
        conversationId,
      );
      onTranslationComplete(response);
    } catch (err: any) {
      setError(err.message || 'Translation request failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!lastResult?.translation) return;
    await navigator.clipboard.writeText(lastResult.translation);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="translator-shell" aria-labelledby="translator-heading">
      <div className="translator-intro">
        <div>
          <span className="eyebrow">PERSONA TRANSLATOR</span>
          <h2 id="translator-heading">Translate without losing the meaning</h2>
          <p>CrossSpeak adapts tone, terminology, and context—not just individual words.</p>
        </div>
        <div className="direction-pill" aria-label={`Translation direction: ${sourceLabel} to ${targetLabel}`}>
          {userMode === 'corporate' ? <Briefcase size={16} /> : <Zap size={16} />}
          <span>{sourceLabel}</span>
          <ArrowRight size={15} />
          <span>{targetLabel}</span>
        </div>
      </div>

      <div className="translator-grid">
        <div className="glass-card translator-panel input-panel">
          <div className="panel-heading">
            <div>
              <span className="panel-step">1</span>
              <div>
                <h3>Add your message</h3>
                <p>Paste text or start with an example.</p>
              </div>
            </div>
            <span className={userMode === 'corporate' ? 'badge badge-corp' : 'badge badge-genz'}>
              {sourceLabel}
            </span>
          </div>

          <div className="preset-row" aria-label="Example messages">
            {presets.map(([label, text]) => (
              <button
                key={label}
                id={`preset-${label.toLowerCase().replace(/\s+/g, '-')}-btn`}
                className="preset-chip"
                onClick={() => setInputText(text)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="textarea-wrap">
            <textarea
              id="translate-input-textarea"
              className="textarea-field translator-textarea"
              placeholder={`Enter ${sourceLabel.toLowerCase()} here…`}
              value={inputText}
              maxLength={10000}
              onChange={(event) => setInputText(event.target.value)}
              onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                  event.preventDefault();
                  handleTranslate();
                }
              }}
            />
            <span>{inputText.length.toLocaleString()} / 10,000</span>
          </div>

          <div className="safety-note">
            <ShieldCheck size={14} /> Language safety is active
            <span>Ctrl/⌘ + Enter to translate</span>
          </div>

          {error && <div className="form-error">{error}</div>}

          <button id="translate-submit-btn" className="btn btn-primary translate-button" onClick={handleTranslate} disabled={loading || !inputText.trim()}>
            <Sparkles size={17} />
            {loading ? 'Translating…' : `Translate to ${targetLabel}`}
            {!loading && <ArrowRight size={17} />}
          </button>
        </div>

        <div className="glass-card translator-panel output-panel" aria-live="polite">
          <div className="panel-heading">
            <div>
              <span className="panel-step">2</span>
              <div>
                <h3>Your translation</h3>
                <p>Ready to review, copy, and use.</p>
              </div>
            </div>
            {lastResult && (
              <button id="copy-translation-btn" className="btn btn-secondary btn-sm" onClick={handleCopy}>
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            )}
          </div>

          {lastResult ? (
            <div className="translation-result">
              <div className="result-meta">
                <span className="badge badge-accent">{targetLabel}</span>
                <span>Detected: {lastResult.detected_style}</span>
                {lastResult.saved_to_history && <span className="saved-label">Saved to history</span>}
              </div>

              <div className="result-copy">{lastResult.translation}</div>

              {lastResult.terms_used?.length > 0 && (
                <div className="result-section">
                  <h4><BookOpen size={15} /> Terms mapped</h4>
                  <div className="term-list">
                    {lastResult.terms_used.map((term, index) => (
                      <div key={index}>
                        <strong>{term.term || term.key || Object.keys(term)[0]}</strong>
                        <span>{term.translation || term.meaning || String(Object.values(term)[0])}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {lastResult.retrieved_docs?.length > 0 && (
                <details className="source-details">
                  <summary><Layers size={15} /> View {lastResult.retrieved_docs.length} knowledge sources</summary>
                  <div className="source-list">
                    {lastResult.retrieved_docs.map((doc, index) => (
                      <div key={index}>
                        <strong>{doc.metadata?.term || `Source ${index + 1}`}</strong>
                        <p>{doc.page_content}</p>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ) : (
            <div className="output-empty">
              <div><Sparkles size={28} /></div>
              <h3>Your translation will appear here</h3>
              <p>Add a message, choose an example if helpful, and translate when ready.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
