import { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AuthModal } from './components/AuthModal';
import { TranslateTab } from './components/TranslateTab';
import { HistoryTab } from './components/HistoryTab';
import { KnowledgeBaseTab } from './components/KnowledgeBaseTab';
import { SuggestSlangTab } from './components/SuggestSlangTab';
import { AdminReviewTab } from './components/AdminReviewTab';
import { UpgradeModal } from './components/UpgradeModal';
import { AuthState, ConfigResponse, TranslationResult } from './types';
import { fetchConfig, fetchCurrentAuthUser, startNewConversation } from './services/api';
import { Languages, Clock, Database, Send, ShieldCheck, LogIn, Briefcase, Zap, ArrowRight, Moon, Sun } from 'lucide-react';

export function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const savedTheme = localStorage.getItem('cs_theme');
    if (savedTheme === 'dark' || savedTheme === 'light') return savedTheme;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  const [userMode, setUserMode] = useState<'corporate' | 'genz'>('corporate');
  const [activeTab, setActiveTab] = useState<'translate' | 'history' | 'knowledge' | 'suggest' | 'admin'>('translate');
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [customApiKey, setCustomApiKey] = useState<string>('');

  const [auth, setAuth] = useState<AuthState>(() => {
    const savedToken = localStorage.getItem('cs_token');
    return {
      user: null,
      role: 'user',
      userMode: 'corporate',
      accessToken: savedToken,
      conversationId: null,
      plan: 'free',
      usageCount: 0,
      usageLimit: 3,
    };
  });

  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [authChecking, setAuthChecking] = useState(Boolean(localStorage.getItem('cs_token')));
  const [isUpgradeOpen, setIsUpgradeOpen] = useState(false);
  const [authDefaultRegister, setAuthDefaultRegister] = useState(false);
  const [localHistory, setLocalHistory] = useState<TranslationResult[]>([]);
  const [lastResult, setLastResult] = useState<TranslationResult | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cs_theme', theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute('data-persona', userMode);
  }, [userMode]);

  useEffect(() => {
    fetchConfig()
      .then((cfg) => setConfig(cfg))
      .catch((err) => console.warn('Failed to fetch config', err));
  }, []);

  useEffect(() => {
    if (!auth.accessToken || auth.user) {
      setAuthChecking(false);
      return;
    }
    setAuthChecking(true);
    fetchCurrentAuthUser(auth.accessToken)
      .then((res) => {
        const mode = res.user_mode || 'corporate';
        setAuth((prev) => ({
          ...prev,
          user: res.user,
          role: res.role,
          userMode: mode,
          conversationId: res.conversation_id,
          plan: res.plan,
          usageCount: res.usage_count,
          usageLimit: res.usage_limit,
        }));
        setUserMode(mode);
      })
      .catch(() => {
        localStorage.removeItem('cs_token');
        setAuth({ user: null, role: 'user', userMode: 'corporate', accessToken: null, conversationId: null, plan: 'free', usageCount: 0, usageLimit: 3 });
      })
      .finally(() => setAuthChecking(false));
  }, [auth.accessToken, auth.user]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleUserModeChange = (mode: 'corporate' | 'genz') => {
    if (auth.role !== 'admin' || auth.user?.email.toLowerCase() !== 'admin@csai.com') return;
    setUserMode(mode);
    setLastResult(null);
  };

  const openAuth = (defaultToRegister = false) => {
    setAuthDefaultRegister(defaultToRegister);
    setIsAuthOpen(true);
  };

  const handleAuthSuccess = (data: {
    user: { id: string; email: string; user_mode?: 'corporate' | 'genz' };
    role: 'user' | 'admin';
    userMode?: 'corporate' | 'genz';
    accessToken: string;
    conversationId: string;
    plan: 'free' | 'paid';
    usageCount: number;
    usageLimit: number;
  }) => {
    localStorage.setItem('cs_token', data.accessToken);
    const mode = data.userMode || data.user.user_mode || 'corporate';
    setUserMode(mode);
    setAuth({
      user: data.user,
      role: data.role,
      userMode: mode,
      accessToken: data.accessToken,
      conversationId: data.conversationId,
      plan: data.plan,
      usageCount: data.usageCount,
      usageLimit: data.usageLimit,
    });
  };

  const handleSignOut = () => {
    localStorage.removeItem('cs_token');
    setAuth({ user: null, role: 'user', userMode: 'corporate', accessToken: null, conversationId: null, plan: 'free', usageCount: 0, usageLimit: 3 });
  };

  const handleNewConversation = async () => {
    if (auth.accessToken) {
      try {
        const convId = await startNewConversation(auth.accessToken);
        setAuth((prev) => ({ ...prev, conversationId: convId }));
        setLocalHistory([]);
        setLastResult(null);
        setActiveTab('translate');
      } catch (err: any) {
        alert(`Error starting conversation: ${err.message}`);
      }
    }
  };

  const handleTranslationComplete = (result: TranslationResult) => {
    setLastResult(result);
    setLocalHistory((prev) => [...prev, result]);
    setAuth((prev) => ({ ...prev, plan: result.plan, usageCount: result.usage_count, usageLimit: result.usage_limit }));
  };

  const refreshAccount = async () => {
    if (!auth.accessToken) return;
    const res = await fetchCurrentAuthUser(auth.accessToken);
    const mode = res.user_mode || 'corporate';
    setAuth((prev) => ({
      ...prev,
      user: res.user,
      role: res.role,
      userMode: mode,
      conversationId: res.conversation_id,
      plan: res.plan,
      usageCount: res.usage_count,
      usageLimit: res.usage_limit,
    }));
  };

  if (authChecking) {
    return (
      <div className="auth-loading-page">
        <img className="brand-logo brand-logo-large" src="/crossspeak-logo.png" alt="CrossSpeak AI logo" />
        <strong>Opening your workspace</strong>
        <span>Checking your secure session…</span>
      </div>
    );
  }

  // ── Auth-gated landing screen ─────────────────────────────────────────────
  if (!auth.user && !auth.accessToken) {
    return (
      <div className="landing-page">
        <div className="landing-bg-orb orb-1" />
        <div className="landing-bg-orb orb-2" />

        <nav className="landing-nav">
          <div className="landing-logo">
            <img className="brand-logo" src="/crossspeak-logo.png" alt="CrossSpeak AI logo" />
            <span>CrossSpeak <strong>AI</strong></span>
          </div>
          <div className="landing-nav-actions">
            <button className="icon-btn" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button
              id="landing-sign-in-btn"
              className="btn btn-secondary"
              style={{ fontSize: '0.88rem', padding: '0.55rem 1.25rem' }}
              onClick={() => openAuth(false)}
            >
              <LogIn size={16} /> Sign In
            </button>
            <button
              id="landing-register-btn"
              className="btn btn-primary"
              style={{ fontSize: '0.88rem', padding: '0.55rem 1.25rem' }}
              onClick={() => openAuth(true)}
            >
              Get Started <ArrowRight size={16} />
            </button>
          </div>
        </nav>

        <div className="landing-hero">
          <div className="landing-badge">
            <span className="pulse-dot" />
            AI-Powered Dialect Bridge
          </div>
          <h1 className="landing-title">
            Speak Every<br />
            <span className="gradient-text">Business Language</span>
          </h1>
          <p className="landing-subtitle">
            CrossSpeak AI bridges the gap between Corporate English and Gen Z slang
            using a RAG-powered translation engine. Your persona. Your history. Your dialect.
          </p>
          <div className="landing-cta-row">
            <button
              id="landing-cta-register-btn"
              className="btn btn-primary landing-cta-btn"
              onClick={() => openAuth(true)}
            >
              Register Your Persona <ArrowRight size={18} />
            </button>
            <button
              id="landing-cta-signin-btn"
              className="btn btn-secondary landing-cta-btn"
              onClick={() => openAuth(false)}
            >
              <LogIn size={18} /> Sign In
            </button>
          </div>
        </div>

        <div className="landing-modes">
          <div className="landing-mode-card mode-corporate">
            <div className="landing-mode-icon">
              <Briefcase size={28} />
            </div>
            <h3>Corporate Mode</h3>
            <p>Executive-level communication, business jargon, boardroom fluency. Turn Gen Z speak into polished professional language.</p>
            <div className="badge badge-corp" style={{ marginTop: '0.75rem' }}>Business English</div>
          </div>
          <div className="landing-mode-card mode-genz">
            <div className="landing-mode-icon">
              <Zap size={28} />
            </div>
            <h3>Gen Z Mode</h3>
            <p>Slang, culture, vibes. Decode the latest Gen Z lexicon or translate corporate speak into something that actually hits different.</p>
            <div className="badge badge-genz" style={{ marginTop: '0.75rem' }}>Gen Z Slang</div>
          </div>
        </div>

        <section className="landing-plans" aria-labelledby="plans-heading">
          <h2 id="plans-heading">Simple plans for every workflow</h2>
          <div className="landing-modes">
            <div className="landing-mode-card">
              <span className="badge badge-corp">Free</span>
              <h3>Explore CrossSpeak AI</h3>
              <p>Up to 3 successful translations, with saved history and persona-based terminology.</p>
            </div>
            <div className="landing-mode-card paid-plan-card">
              <span className="badge badge-accent">Paid</span>
              <h3>Unlimited Translation</h3>
              <p>
                Unlimited translations for {config?.paid_plan_duration_days || 30} days
                {config ? ` for ${new Intl.NumberFormat('en-IN', { style: 'currency', currency: config.paid_plan_currency, maximumFractionDigits: 0 }).format(config.paid_plan_amount_subunits / 100)}` : ''}, with the same protected workspace, history, and language-safety controls.
              </p>
            </div>
          </div>
        </section>

        <p className="landing-footer-note">
          Sign in or register to unlock your persona workspace and translation history.
        </p>

        <AuthModal
          isOpen={isAuthOpen}
          onClose={() => setIsAuthOpen(false)}
          onAuthSuccess={handleAuthSuccess}
          defaultRegister={authDefaultRegister}
        />
      </div>
    );
  }

  // ── Authenticated app ─────────────────────────────────────────────────────
  return (
    <div className="app-container">
      <div className="main-content">
        <Header
          theme={theme}
          toggleTheme={toggleTheme}
          auth={auth}
          onSignOut={handleSignOut}
          onOpenUpgrade={() => setIsUpgradeOpen(true)}
          userMode={userMode}
          onUserModeChange={handleUserModeChange}
        />

        <div className="workspace-layout">
          <main className="workspace-main">
            <nav className="tab-bar" aria-label="Workspace sections">
              <button
                id="tab-translate-btn"
                className={`tab-btn ${activeTab === 'translate' ? 'active' : ''}`}
                onClick={() => setActiveTab('translate')}
              >
                <Languages size={18} /> Translate
              </button>
              <button
                id="tab-history-btn"
                className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
                onClick={() => setActiveTab('history')}
              >
                <Clock size={18} /> History
              </button>
              <button
                id="tab-knowledge-btn"
                className={`tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
                onClick={() => setActiveTab('knowledge')}
              >
                <Database size={18} /> Knowledge Base
              </button>
              {config?.supabase_enabled && (
                <button
                  id="tab-suggest-btn"
                  className={`tab-btn ${activeTab === 'suggest' ? 'active' : ''}`}
                  onClick={() => setActiveTab('suggest')}
                >
                  <Send size={18} /> Suggest Slang
                </button>
              )}
              {config?.supabase_enabled && auth.role === 'admin' && (
                <button
                  id="tab-admin-btn"
                  className={`tab-btn ${activeTab === 'admin' ? 'active' : ''}`}
                  onClick={() => setActiveTab('admin')}
                >
                  <ShieldCheck size={18} /> Admin Review
                </button>
              )}
            </nav>

            {activeTab === 'translate' && (
              <TranslateTab
                customApiKey={customApiKey}
                token={auth.accessToken || undefined}
                conversationId={auth.conversationId || undefined}
                userMode={userMode}
                onTranslationComplete={handleTranslationComplete}
                lastResult={lastResult}
              />
            )}

            {activeTab === 'history' && (
              <HistoryTab token={auth.accessToken || undefined} localHistory={localHistory} />
            )}

            {activeTab === 'knowledge' && (
              <KnowledgeBaseTab token={auth.accessToken || undefined} userMode={userMode} />
            )}

            {activeTab === 'suggest' && (
              <SuggestSlangTab
                token={auth.accessToken || undefined}
                onOpenAuth={() => openAuth(false)}
              />
            )}

            {activeTab === 'admin' && (
              <AdminReviewTab token={auth.accessToken || undefined} role={auth.role} />
            )}
          </main>

          <Sidebar
            config={config}
            customApiKey={customApiKey}
            setCustomApiKey={setCustomApiKey}
            historyCount={localHistory.length}
            onClearLocalHistory={() => {
              setLocalHistory([]);
              setLastResult(null);
            }}
            onNewConversation={handleNewConversation}
            plan={auth.plan}
            usageCount={auth.usageCount}
            usageLimit={auth.usageLimit}
          />
        </div>
      </div>

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={handleAuthSuccess}
        defaultRegister={authDefaultRegister}
      />
      <UpgradeModal
        isOpen={isUpgradeOpen}
        onClose={() => setIsUpgradeOpen(false)}
        onActivated={refreshAccount}
        token={auth.accessToken || ''}
        email={auth.user?.email || ''}
        config={config}
      />
    </div>
  );
}

export default App;
