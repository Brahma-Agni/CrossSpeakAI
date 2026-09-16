import { ConfigResponse, TranslationResult, HistoryItem, KBTerm, SlangSuggestion } from '../types';

const API_BASE = '/api';

export async function fetchConfig(): Promise<ConfigResponse> {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error('Failed to fetch config');
  return res.json();
}

export async function requestTranslation(
  inputText: string,
  mode: string,
  customApiKey?: string,
  token?: string,
  conversationId?: string
): Promise<TranslationResult> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/translate`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      input_text: inputText,
      translation_mode: mode,
      custom_api_key: customApiKey,
      conversation_id: conversationId,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Translation failed');
  }
  return res.json();
}

export async function authSignIn(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/sign-in`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Sign in failed');
  }
  return res.json();
}

export async function authSignUp(email: string, password: string, userMode: string = 'corporate') {
  const res = await fetch(`${API_BASE}/auth/sign-up`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, user_mode: userMode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Sign up failed');
  }
  return res.json();
}

export async function fetchCurrentAuthUser(token: string) {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Session expired');
  return res.json();
}

export async function fetchHistory(token: string): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to load history');
  return res.json();
}

export async function startNewConversation(token: string): Promise<string> {
  const res = await fetch(`${API_BASE}/conversations/new`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to create new conversation');
  const data = await res.json();
  return data.conversation_id;
}

export async function fetchKnowledgeBase(query?: string, category: string = 'All', token?: string): Promise<KBTerm[]> {
  const params = new URLSearchParams({ category });
  if (query) params.append('query', query);

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/knowledge-base?${params.toString()}`, { headers });
  if (!res.ok) throw new Error('Failed to load knowledge base');
  const data = await res.json();
  return data.terms;
}

export async function fetchUserSuggestions(token: string): Promise<SlangSuggestion[]> {
  const res = await fetch(`${API_BASE}/suggestions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to load suggestions');
  return res.json();
}

export async function submitSlangSuggestion(
  suggestion: { term: string; category: string; meaning: string; translation: string; example?: string; context?: string },
  token: string
) {
  const res = await fetch(`${API_BASE}/suggestions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(suggestion),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to submit suggestion');
  }
  return res.json();
}

export async function fetchAdminPendingSuggestions(token: string): Promise<SlangSuggestion[]> {
  const res = await fetch(`${API_BASE}/admin/suggestions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to load pending admin suggestions');
  return res.json();
}

export async function approveSuggestion(id: string, payload: any, token: string) {
  const res = await fetch(`${API_BASE}/admin/suggestions/${id}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Approval failed');
  }
  return res.json();
}

export async function rejectSuggestion(id: string, reason: string, token: string) {
  const res = await fetch(`${API_BASE}/admin/suggestions/${id}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Rejection failed');
  }
  return res.json();
}
