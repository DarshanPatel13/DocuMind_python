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
