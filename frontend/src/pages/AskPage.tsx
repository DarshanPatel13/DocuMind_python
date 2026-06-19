import { useCallback, useEffect, useState } from "react";

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
          <h1 className="mb-1 text-2xl font-semibold text-gray-900">Ask</h1>
          <label className="text-sm text-gray-600">
            Scope:{" "}
            <select
              value={selectedDoc}
              onChange={(e) => setSelectedDoc(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1"
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

        <ChatView
          documentId={selectedDoc || undefined}
          onConversationId={rememberConversation}
        />

        {historyId && (
          <section className="border-t border-gray-200 pt-4">
            <h2 className="mb-3 text-lg font-semibold text-gray-900">
              History · {historyId.slice(0, 8)}…
            </h2>
            {history.isLoading && <p className="text-gray-500">Loading…</p>}
            {history.isError && <p className="text-red-600">Could not load this conversation.</p>}
            <div className="space-y-4">
              {history.data?.turns.map((turn, i) => (
                <div key={i} className="rounded-lg border border-gray-200 bg-white p-4">
                  <p className="font-medium text-gray-900">Q: {turn.question}</p>
                  <p className="mt-1 whitespace-pre-wrap text-gray-800">{turn.answer}</p>
                  {turn.citations.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {turn.citations.map((c, j) => (
                        <CitationChip key={j} citation={c} />
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
