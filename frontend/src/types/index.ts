// Shared types — these mirror the backend Pydantic models in
// backend/app/models/schemas.py. Keep them in sync.

export interface Citation {
  filename: string;
  chunk_index: number;
  snippet?: string | null;
}

export type DocumentStatus = "UPLOADED" | "PROCESSING" | "READY" | "FAILED";

export interface DocumentResponse {
  id: string;
  filename: string;
  status: DocumentStatus;
  uploaded_at: string;
  chunk_count: number;
  failure_reason?: string | null;
}

export interface UploadResponse {
  document_id: string;
  status: string;
  message: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AskRequest {
  question: string;
  document_id?: string;
  conversation_id?: string;
}

export interface ConversationTurn {
  question: string;
  answer: string;
  citations: Citation[];
  timestamp: string;
}

export interface ConversationHistory {
  conversation_id: string;
  turns: ConversationTurn[];
}

// Parsed Server-Sent Events from POST /api/ask.
export interface CitationsEvent {
  conversation_id: string;
  citations: Citation[];
}

export type StreamEvent =
  | { type: "citations"; conversation_id: string; citations: Citation[] }
  | { type: "token"; token: string }
  | { type: "done" };

export interface AskStreamHandlers {
  onCitations: (event: CitationsEvent) => void;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (error: Error) => void;
}

// ---- Behavioural evals (GET/POST /api/evals/*) ----

export type EvalBehavior = "answer" | "refuse" | "resist_injection";

export interface EvalCaseResult {
  id: string;
  behavior: EvalBehavior;
  question: string;
  answer: string;
  groundedness: number | null;
  unsupported_claims: string[];
  citations_valid: number;
  citations_invalid: number;
  citations_supported: number;
  refusal?: number;
  guardrail?: number;
  errored: boolean;
  passed: boolean;
}

export interface EvalReport {
  base_url: string;
  judge_model: string;
  document_id: string;
  aggregates: Record<string, number | null>;
  failures: string[];
  cases: EvalCaseResult[];
}

export interface EvalStatus {
  status: "idle" | "running" | "done" | "error";
  progress: { done: number; total: number; current: string } | null;
  report: EvalReport | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}
