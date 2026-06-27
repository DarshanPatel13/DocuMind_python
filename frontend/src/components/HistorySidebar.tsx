import { MessageSquare } from "lucide-react";

import { cn } from "@/lib/utils";

interface HistorySidebarProps {
  conversationIds: string[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Lists conversation ids seen this session; clicking loads that history. */
export function HistorySidebar({ conversationIds, selectedId, onSelect }: HistorySidebarProps) {
  return (
    <aside className="w-60 shrink-0">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Conversations
      </h2>
      {conversationIds.length === 0 ? (
        <p className="text-sm text-muted-foreground/70">No conversations yet.</p>
      ) : (
        <ul className="space-y-1">
          {conversationIds.map((id) => (
            <li key={id}>
              <button
                type="button"
                onClick={() => onSelect(id)}
                className={cn(
                  "flex w-full items-center gap-2 truncate rounded-md px-2 py-1.5 text-left text-sm transition-colors",
                  id === selectedId
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
                title={id}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                {id.slice(0, 8)}…
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
