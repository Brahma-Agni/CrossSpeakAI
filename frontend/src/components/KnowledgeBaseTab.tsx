import React, { useEffect, useState } from 'react';
import { Search, Database } from 'lucide-react';
import { KBTerm } from '../types';
import { fetchKnowledgeBase } from '../services/api';

interface KnowledgeBaseTabProps {
  token?: string;
  userMode: 'corporate' | 'genz';
}

export const KnowledgeBaseTab: React.FC<KnowledgeBaseTabProps> = ({ token, userMode }) => {
  const [terms, setTerms] = useState<KBTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<string>(() => (userMode === 'corporate' ? 'Corporate' : 'Gen Z'));
  const [error, setError] = useState<string | null>(null);

  const loadTerms = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchKnowledgeBase(query, category, token);
      setTerms(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load knowledge base');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadTerms();
    }, 250);
    return () => clearTimeout(timer);
  }, [query, category, token]);

  return (
    <div className="glass-card" style={{ padding: '1.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Database size={20} color="var(--accent-primary)" />
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              Knowledge Base Terminology
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Curated RAG terminology index containing Corporate and Gen Z mappings.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Category Filter */}
          <div style={{ display: 'flex', gap: '0.3rem', background: 'var(--bg-input)', padding: '0.25rem', borderRadius: '0.6rem', border: '1px solid var(--border-color)' }}>
            {['All', 'Corporate', 'Gen Z'].map((cat) => (
              <button
                key={cat}
                id={`filter-cat-${cat.toLowerCase().replace(' ', '')}-btn`}
                onClick={() => setCategory(cat)}
                style={{
                  padding: '0.4rem 0.8rem',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  borderRadius: '0.45rem',
                  border: 'none',
                  background: category === cat ? 'var(--accent-primary)' : 'transparent',
                  color: category === cat ? '#ffffff' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div style={{ position: 'relative', width: '260px' }}>
            <Search size={16} style={{ position: 'absolute', left: '0.8rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              id="kb-search-input"
              type="text"
              className="input-field"
              style={{ paddingLeft: '2.4rem', height: '38px', fontSize: '0.85rem' }}
              placeholder="Search term or meaning..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.8rem', borderRadius: '0.6rem', backgroundColor: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', fontSize: '0.85rem', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="skeleton" style={{ height: '48px' }} />
          ))}
        </div>
      ) : terms.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          No matching terms found. Try adjusting your search query or filter.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Term</th>
                <th style={{ padding: '0.75rem 1rem' }}>Category</th>
                <th style={{ padding: '0.75rem 1rem' }}>Meaning</th>
                <th style={{ padding: '0.75rem 1rem' }}>Translation</th>
                <th style={{ padding: '0.75rem 1rem' }}>Examples</th>
              </tr>
            </thead>
            <tbody>
              {terms.map((row, idx) => (
                <tr
                  key={idx}
                  style={{
                    borderBottom: '1px solid var(--border-color)',
                    transition: 'background-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '0.85rem 1rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                    {row.term}
                  </td>
                  <td style={{ padding: '0.85rem 1rem' }}>
                    <span className={row.category?.toLowerCase().includes('gen') ? 'badge badge-genz' : 'badge badge-corp'}>
                      {row.category}
                    </span>
                  </td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-primary)', maxWidth: '280px' }}>
                    {row.meaning}
                  </td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)', maxWidth: '280px' }}>
                    {row.translation}
                  </td>
                  <td style={{ padding: '0.85rem 1rem', color: 'var(--text-muted)', fontSize: '0.82rem', fontStyle: 'italic', maxWidth: '240px' }}>
                    {row.examples}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
