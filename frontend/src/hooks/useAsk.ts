import { useCallback, useRef, useState } from "react";

import { streamAsk } from "../api/documind";
import type { Citation } from "../types";

/**
 * Drives one streamed Q&A exchange. `answer` grows token-by-token as the stream
 * arrives; `citations` and `conversationId` are set from the first SSE event.
 * The conversationId is threaded back into the next ask to continue the thread.
 */
export function useAsk() {
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (question: string, documentId?: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setAnswer("");
      setCitations([]);
      setError(null);
      setIsStreaming(true);

      await streamAsk(
        {
          question,
          document_id: documentId,
          conversation_id: conversationId ?? undefined,
        },
        {
          onCitations: (event) => {
            setCitations(event.citations);
            setConversationId(event.conversation_id);
          },
          onToken: (token) => setAnswer((prev) => prev + token),
          onDone: () => setIsStreaming(false),
          onError: (err) => {
            setError(err.message);
            setIsStreaming(false);
          },
        },
        controller.signal,
      );
    },
    [conversationId],
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setAnswer("");
    setCitations([]);
    setConversationId(null);
    setError(null);
    setIsStreaming(false);
  }, []);

  return { answer, citations, conversationId, isStreaming, error, ask, reset };
}
