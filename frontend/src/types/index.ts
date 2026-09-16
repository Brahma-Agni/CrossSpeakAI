export interface ConfigResponse {
  gemini_api_keys_count: number;
  supabase_enabled: boolean;
  gemini_model: string;
  embedding_model: string;
  translation_modes: { label: string; value: string }[];
}

export interface RetrievedDocument {
  page_content: string;
  metadata: Record<string, any>;
}

export interface TranslationResult {
  translation: string;
  terms_used: { [key: string]: string }[];
  detected_style: string;
  translation_direction: string;
  retrieved_docs: RetrievedDocument[];
  conversation_id?: string;
  saved_to_history?: boolean;
  plan: 'free' | 'paid';
  usage_count: number;
  usage_limit: number;
}

export interface User {
  id: string;
  email: string;
  user_mode?: 'corporate' | 'genz';
}

export interface AuthState {
  user: User | null;
  role: 'user' | 'admin';
  userMode: 'corporate' | 'genz';
  accessToken: string | null;
  conversationId: string | null;
  plan: 'free' | 'paid';
  usageCount: number;
  usageLimit: number;
}

export interface HistoryItem {
  id: string;
  input_text: string;
  output_text: string;
  detected_style: string;
  translation_direction: string;
  terms_used: any[];
  created_at: string;
}

export interface KBTerm {
  term: string;
  category: string;
  meaning: string;
  translation: string;
  examples: string;
}

export interface SlangSuggestion {
  id: string;
  user_id?: string;
  term: string;
  category: string;
  meaning: string;
  translation: string;
  example?: string;
  context?: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at?: string;
}
