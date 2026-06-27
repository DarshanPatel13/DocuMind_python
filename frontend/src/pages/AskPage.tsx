import { useCallback, useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";

import { ChatView } from "../components/ChatView";
import { CitationChip } from "../components/CitationChip";
import { HistorySidebar } from "../components/HistorySidebar";
import { useConversation } from "../hooks/useConversation";
import { useDocuments } from "../hooks/useDocuments";

const STORAGE_KEY = "documind.conversationIds";

function loadIds(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as string[];
  } catch {
    return [];
  }
}

export function AskPage() {
  const { data: documents } = useDocuments();
  const [selectedDoc, setSelectedDoc] = useState("");
  const [conversationIds, setConversationIds] = useState<string[]>(loadIds);
  const [historyId, setHistoryId] = useState<string | null>(null);
  const history = useConversation(historyId);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversationIds));
  }, [conversationIds]);

  const rememberConversation = useCallback((id: string) => {
    setConversationIds((prev) => (prev.includes(id) ? prev : [id, ...prev]));
  }, []);

  const readyDocs = (documents ?? []).filter((d) => d.status === "READY");

  return (
    <div className="mx-auto flex max-w-5xl gap-8">
      <HistorySidebar
        conversationIds={conversationIds}
        selectedId={historyId}
        onSelect={setHistoryId}
      />

      <div className="flex-1 space-y-6">
        <div>
          <h1 className="mb-1 text-2xl font-semibold tracking-tight">Ask</h1>
          <label className="text-sm text-muted-foreground">
            Scope:{" "}
            <select
              value={selectedDoc}
              onChange={(e) => setSelectedDoc(e.target.value)}
              className="ml-1 rounded-md border border-input bg-background px-2 py-1 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">All documents</option>
              {readyDocs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))}
            </select>
          </label>
        </div>

        <ChatView documentId={selectedDoc || undefined} onConversationId={rememberConversation} />

        {historyId && (
          <section className="border-t pt-4">
            <h2 className="mb-3 text-lg font-semibold tracking-tight">
              History · {historyId.slice(0, 8)}…
            </h2>
            {history.isLoading && <p className="text-muted-foreground">Loading…</p>}
            {history.isError && (
              <p className="text-destructive">Could not load this conversation.</p>
            )}
            <div className="space-y-4">
              {history.data?.turns.map((turn, i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <p className="font-medium">Q: {turn.question}</p>
                    <p className="mt-1 whitespace-pre-wrap text-foreground/90">{turn.answer}</p>
                    {turn.citations.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {turn.citations.map((c, j) => (
                          <CitationChip key={j} citation={c} />
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
