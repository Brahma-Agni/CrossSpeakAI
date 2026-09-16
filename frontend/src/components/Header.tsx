import React from 'react';
import { Sun, Moon, User, LogOut, ShieldCheck, Sparkles, Briefcase, Zap } from 'lucide-react';
import { AuthState } from '../types';

interface HeaderProps {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  auth: AuthState;
  onOpenAuth: () => void;
  onSignOut: () => void;
  apiKeyConnected: boolean;
  userMode: 'corporate' | 'genz';
}

export const Header: React.FC<HeaderProps> = ({
  theme,
  toggleTheme,
  auth,
  onOpenAuth,
  onSignOut,
  apiKeyConnected,
  userMode,
}) => {
  return (
    <header className="glass-card" style={{ padding: '0.85rem 1.5rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div
          style={{
            width: '2.6rem',
            height: '2.6rem',
            borderRadius: '0.8rem',
            background: 'var(--accent-gradient)',
            display: 'grid',
            placeItems: 'center',
            color: 'white',
            fontWeight: 800,
            fontSize: '1rem',
            boxShadow: '0 6px 16px var(--accent-glow)',
          }}
        >
          CS
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              Cross Speak AI
            </h1>
            <span className="badge badge-accent">
              <Sparkles size={12} style={{ marginRight: '3px' }} /> Dialect Intelligence
            </span>
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Bridging Business Speak & Gen Z Slang with RAG
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <span
          className="btn btn-secondary btn-sm"
          style={{
            borderColor: userMode === 'genz' ? '#ec4899' : '#3b82f6',
            color: userMode === 'genz' ? '#ec4899' : '#3b82f6',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            background: userMode === 'genz' ? 'rgba(236,72,153,0.08)' : 'rgba(59,130,246,0.08)',
          }}
          title="Persona selected at registration"
        >
          {userMode === 'genz' ? <Zap size={15} color="#ec4899" /> : <Briefcase size={15} color="#3b82f6" />}
          {userMode === 'genz' ? 'Gen Z Persona' : 'Corporate Persona'}
        </span>

        <span
          className="badge badge-accent"
          title={auth.plan === 'paid' ? 'Unlimited translations' : 'Free-plan usage'}
        >
          {auth.plan === 'paid'
            ? 'Paid · Unlimited'
            : `Free · ${auth.usageCount}/${auth.usageLimit}`}
        </span>

        {/* API Status Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-input)', padding: '0.4rem 0.8rem', borderRadius: '2rem', border: '1px solid var(--border-color)', fontSize: '0.8rem' }}>
          <div className={apiKeyConnected ? "pulse-dot" : ""} style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: apiKeyConnected ? '#10b981' : '#f59e0b' }} />
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
            {apiKeyConnected ? 'API Connected' : 'No Gemini Key'}
          </span>
        </div>

        {/* Dark/Light Theme Toggle */}
        <button
          id="theme-toggle-btn"
          className="btn btn-secondary btn-sm"
          onClick={toggleTheme}
          title="Toggle Dark/Light Mode"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Auth Profile Menu */}
        {auth.user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {auth.user.email}
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                {auth.role === 'admin' && <ShieldCheck size={11} />} {auth.role.toUpperCase()}
              </span>
            </div>
            <button
              id="sign-out-btn"
              className="btn btn-secondary btn-sm"
              onClick={onSignOut}
              title="Sign Out"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <button
            id="open-auth-btn"
            className="btn btn-primary btn-sm"
            onClick={onOpenAuth}
          >
            <User size={15} /> Sign In
          </button>
        )}
      </div>
    </header>
  );
};
