import { AnimatePresence, motion } from "framer-motion";
import { Loader2, SendHorizonal, Sparkles } from "lucide-react";
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

const EXAMPLES = [
  "Summarize this document",
  "What are the key points?",
  "What does it say about pricing?",
];

export function ChatView({ documentId, onConversationId }: ChatViewProps) {
  const { answer, citations, conversationId, isStreaming, error, ask } = useAsk();
  const [question, setQuestion] = useState("");

  useEffect(() => {
    if (conversationId) onConversationId?.(conversationId);
  }, [conversationId, onConversationId]);

  const submit = (q: string): void => {
    const trimmed = q.trim();
    if (!trimmed || isStreaming) return;
    void ask(trimmed, documentId);
  };

  const onSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    submit(question);
  };

  const showSkeleton = isStreaming && !answer;
  const idle = !answer && !isStreaming && !error;

  return (
    <div className="flex flex-col gap-5">
      <form onSubmit={onSubmit} className="flex gap-2.5">
        <Input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your documents…"
          className="h-12 rounded-full px-5 text-[15px] shadow-soft"
        />
        <Button
          type="submit"
          size="lg"
          disabled={isStreaming || question.trim().length === 0}
          aria-label="Ask"
        >
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <SendHorizonal className="h-4 w-4" />
          )}
          {isStreaming ? "Asking…" : "Ask"}
        </Button>
      </form>

      {error && <p className="px-1 text-sm text-destructive">{error}</p>}

      <AnimatePresence>
        {idle ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-4 rounded-3xl border border-dashed py-14 text-center"
          >
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-secondary text-primary">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[17px] font-medium">Ask anything about your documents</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Answers are grounded in your files, with citations.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onClick={() => {
                    setQuestion(ex);
                    submit(ex);
                  }}
                  className="rounded-full border bg-card px-3.5 py-1.5 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                >
                  {ex}
                </button>
              ))}
            </div>
          </motion.div>
        ) : (answer || isStreaming) ? (
          <motion.div
            key="answer"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          >
            <Card className="rounded-2xl shadow-card">
              <CardContent className="p-5">
                {showSkeleton ? (
                  <div className="space-y-2.5">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
                    {answer}
                    {isStreaming && <span className="ml-0.5 animate-pulse">▋</span>}
                  </p>
                )}
                {citations.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">
                    {citations.map((c) => (
                      <CitationChip key={`${c.filename}-${c.chunk_index}`} citation={c} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
