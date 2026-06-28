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
  documentId?: string;
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
          className="h-14 rounded-2xl border-border/60 bg-card/50 px-5 text-base shadow-soft backdrop-blur"
        />
        <Button
          type="submit"
          size="lg"
          disabled={isStreaming || question.trim().length === 0}
          aria-label="Ask"
          className="h-14 rounded-2xl px-6 shadow-glow"
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
            className="flex flex-col items-center gap-5 rounded-3xl border border-border/60 bg-card/40 py-16 text-center backdrop-blur-xl"
          >
            <div className="grid h-16 w-16 animate-float place-items-center rounded-2xl brand-gradient text-white shadow-glow-lg">
              <Sparkles className="h-8 w-8" />
            </div>
            <div>
              <p className="text-xl font-semibold tracking-tight">
                Ask anything about your documents
              </p>
              <p className="mt-1.5 text-muted-foreground">
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
                  className="rounded-full border bg-background/50 px-4 py-2 text-sm text-muted-foreground backdrop-blur transition-colors hover:border-primary/50 hover:text-foreground"
                >
                  {ex}
                </button>
              ))}
            </div>
          </motion.div>
        ) : (answer || isStreaming) ? (
          <motion.div
            key="answer"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <Card className="rounded-3xl border-border/60 bg-card/60 shadow-card backdrop-blur-xl">
              <CardContent className="p-6">
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
                  <div className="mt-4 flex flex-wrap gap-2 border-t border-border/60 pt-4">
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
