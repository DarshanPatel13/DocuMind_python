import { AnimatePresence, motion } from "framer-motion";
import { Loader2, SendHorizonal } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

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

  const showSkeleton = isStreaming && !answer;

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={onSubmit} className="flex gap-2">
        <Input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your documents…"
        />
        <Button type="submit" disabled={isStreaming || question.trim().length === 0}>
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <SendHorizonal className="h-4 w-4" />
          )}
          {isStreaming ? "Asking…" : "Ask"}
        </Button>
      </form>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <AnimatePresence>
        {(answer || isStreaming) && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Card>
              <CardContent className="p-4">
                {showSkeleton ? (
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap leading-relaxed">
                    {answer}
                    {isStreaming && <span className="ml-0.5 animate-pulse">▋</span>}
                  </p>
                )}
                {citations.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {citations.map((c) => (
                      <CitationChip key={`${c.filename}-${c.chunk_index}`} citation={c} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
