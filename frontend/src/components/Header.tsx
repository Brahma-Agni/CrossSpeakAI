import React from 'react';
import { Sun, Moon, LogOut, ShieldCheck, Briefcase, Zap, CreditCard } from 'lucide-react';
import { AuthState } from '../types';

interface HeaderProps {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  auth: AuthState;
  onSignOut: () => void;
  onOpenUpgrade: () => void;
  userMode: 'corporate' | 'genz';
}

export const Header: React.FC<HeaderProps> = ({
  theme,
  toggleTheme,
  auth,
  onSignOut,
  onOpenUpgrade,
  userMode,
}) => {
  return (
    <header className="glass-card app-header">
      <div className="app-brand">
        <div className="app-brand-mark">CS</div>
        <div>
          <h1>CrossSpeak AI</h1>
          <p>Clear communication across generations</p>
        </div>
      </div>

      <div className="header-actions">
        <span
          className={`persona-chip ${userMode}`}
          title="Persona selected at registration"
        >
          {userMode === 'genz' ? <Zap size={14} /> : <Briefcase size={14} />}
          {userMode === 'genz' ? 'Gen Z' : 'Corporate'}
        </span>

        {auth.plan === 'paid' ? (
          <span className="badge badge-accent" title="Unlimited translations">
            Paid · Unlimited
          </span>
        ) : (
          <button
            id="open-upgrade-btn"
            className="btn btn-primary btn-sm"
            onClick={onOpenUpgrade}
            title={`Free plan: ${auth.usageCount} of ${auth.usageLimit} translations used`}
          >
            <CreditCard size={14} /> Upgrade · {auth.usageCount}/{auth.usageLimit}
          </button>
        )}

        <button
          id="theme-toggle-btn"
          className="icon-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {auth.user && (
          <div className="account-menu">
            <div className="account-copy">
              <strong>{auth.user.email}</strong>
              <span>{auth.role === 'admin' && <ShieldCheck size={11} />} {auth.role}</span>
            </div>
            <button id="sign-out-btn" className="icon-btn" onClick={onSignOut} title="Sign out" aria-label="Sign out">
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
