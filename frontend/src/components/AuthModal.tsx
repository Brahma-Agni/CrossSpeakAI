import React, { useState } from 'react';
import { X, Lock, Mail, UserPlus, LogIn, Briefcase, Zap } from 'lucide-react';
import { authSignIn, authSignUp } from '../services/api';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess: (authData: { user: { id: string; email: string; user_mode?: 'corporate' | 'genz' }; role: 'user' | 'admin'; userMode?: 'corporate' | 'genz'; accessToken: string; conversationId: string; plan: 'free' | 'paid'; usageCount: number; usageLimit: number }) => void;
  defaultRegister?: boolean;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onAuthSuccess, defaultRegister = false }) => {
  const [isRegister, setIsRegister] = useState(defaultRegister);

  // Sync when caller changes defaultRegister (e.g., switching between sign-in & register CTAs)
  React.useEffect(() => {
    if (isOpen) setIsRegister(defaultRegister);
  }, [isOpen, defaultRegister]);
  const [userMode, setUserMode] = useState<'corporate' | 'genz'>('corporate');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);

    if (!email || !email.includes('@') || password.length < 6) {
      setError('Please enter a valid email address and a password of at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        const res = await authSignUp(email, password, userMode);
        if (res.confirmed && res.access_token) {
          onAuthSuccess({
            user: res.user,
            role: res.role,
            userMode: res.user_mode || userMode,
            accessToken: res.access_token,
            conversationId: res.conversation_id,
            plan: res.plan,
            usageCount: res.usage_count,
            usageLimit: res.usage_limit,
          });
          onClose();
        } else {
          setInfo(res.message || 'Registration submitted. Check your inbox to confirm.');
        }
      } else {
        const res = await authSignIn(email, password);
        onAuthSuccess({
          user: res.user,
          role: res.role,
          userMode: res.user_mode || 'corporate',
          accessToken: res.access_token,
          conversationId: res.conversation_id,
          plan: res.plan,
          usageCount: res.usage_count,
          usageLimit: res.usage_limit,
        });
        onClose();
      }
    } catch (err: any) {
      setError(err.message || 'Authentication error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'grid',
        placeItems: 'center',
        padding: '1rem',
      }}
    >
      <div
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '2rem',
          position: 'relative',
          background: 'var(--bg-secondary)',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        <button
          id="close-auth-modal-btn"
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '1.25rem',
            right: '1.25rem',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <X size={20} />
        </button>

        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div
            style={{
              width: '3.2rem',
              height: '3.2rem',
              margin: '0 auto 0.75rem',
              borderRadius: '1rem',
              background: 'var(--accent-gradient)',
              display: 'grid',
              placeItems: 'center',
              color: 'white',
              boxShadow: '0 6px 16px var(--accent-glow)',
            }}
          >
            {isRegister ? <UserPlus size={22} /> : <LogIn size={22} />}
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            {isRegister ? 'Register Account Persona' : 'Welcome Back'}
          </h2>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {isRegister ? 'Select your persona mode to customize your dialect workspace.' : 'Sign in to access your persona mode and PostgreSQL translation history.'}
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: '0.75rem 1rem',
              borderRadius: '0.6rem',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#f87171',
              fontSize: '0.85rem',
              marginBottom: '1rem',
            }}
          >
            {error}
          </div>
        )}

        {info && (
          <div
            style={{
              padding: '0.75rem 1rem',
              borderRadius: '0.6rem',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              fontSize: '0.85rem',
              marginBottom: '1rem',
            }}
          >
            {info}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Persona Mode Selection Cards for Registration */}
          {isRegister && (
            <div>
              <label className="label">Select Persona Mode</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div
                  id="select-mode-corporate"
                  onClick={() => setUserMode('corporate')}
                  style={{
                    padding: '0.85rem 0.75rem',
                    borderRadius: '0.75rem',
                    border: `2px solid ${userMode === 'corporate' ? '#3b82f6' : 'var(--border-color)'}`,
                    background: userMode === 'corporate' ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-input)',
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <Briefcase size={20} color="#3b82f6" style={{ margin: '0 auto 0.3rem' }} />
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: userMode === 'corporate' ? '#3b82f6' : 'var(--text-primary)' }}>
                    Corporate Mode
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                    Executive & Business Speak
                  </div>
                </div>

                <div
                  id="select-mode-genz"
                  onClick={() => setUserMode('genz')}
                  style={{
                    padding: '0.85rem 0.75rem',
                    borderRadius: '0.75rem',
                    border: `2px solid ${userMode === 'genz' ? '#ec4899' : 'var(--border-color)'}`,
                    background: userMode === 'genz' ? 'rgba(236, 72, 153, 0.08)' : 'var(--bg-input)',
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <Zap size={20} color="#ec4899" style={{ margin: '0 auto 0.3rem' }} />
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: userMode === 'genz' ? '#ec4899' : 'var(--text-primary)' }}>
                    Gen Z Mode
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>
                    Gen Z Slang & Culture
                  </div>
                </div>
              </div>
            </div>
          )}

          <div>
            <label className="label">Email Address</label>
            <div style={{ position: 'relative' }}>
              <Mail size={16} style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                id="auth-email-input"
                type="email"
                className="input-field"
                style={{ paddingLeft: '2.5rem' }}
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="label">Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                id="auth-password-input"
                type="password"
                className="input-field"
                style={{ paddingLeft: '2.5rem' }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button
            id="auth-submit-btn"
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '0.5rem', padding: '0.75rem' }}
            disabled={loading}
          >
            {loading ? 'Processing...' : isRegister ? `Register as ${userMode === 'genz' ? 'Gen Z' : 'Corporate'} Mode` : 'Sign In'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            id="auth-toggle-mode-btn"
            type="button"
            onClick={() => { setIsRegister(!isRegister); setError(null); setInfo(null); }}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--accent-primary)',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {isRegister ? 'Sign In' : 'Register Persona'}
          </button>
        </div>
      </div>
    </div>
  );
};
