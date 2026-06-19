import { useEffect, useState } from "react";

import { useAsk } from "../hooks/useAsk";
import { CitationChip } from "./CitationChip";

interface ChatViewProps {
  /** When set, scopes the question to a single document. */
  documentId?: string;
  /** Called whenever the backend assigns/continues a conversation id. */
  onConversationId?: (id: string) => void;
}

export function ChatView({ documentId, onConversationId }: ChatViewProps) {
  const { answer, citations, conversationId, isStreaming, error, ask } = useAsk();
  const [question, setQuestion] = useState("");

  useEffect(() => {
    if (conversationId) onConversationId?.(conversationId);
  }, [conversationId, onConversationId]);

  const onSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isStreaming) return;
    void ask(trimmed, documentId);
  };

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your documents…"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={isStreaming || question.trim().length === 0}
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isStreaming ? "Asking…" : "Ask"}
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {(answer || isStreaming) && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="whitespace-pre-wrap text-gray-800">
            {answer}
            {isStreaming && <span className="ml-0.5 animate-pulse">▋</span>}
          </p>
          {citations.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {citations.map((c) => (
                <CitationChip key={`${c.filename}-${c.chunk_index}`} citation={c} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
