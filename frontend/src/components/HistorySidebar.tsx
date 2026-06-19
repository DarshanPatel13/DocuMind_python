interface HistorySidebarProps {
  conversationIds: string[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Lists conversation ids seen this session; clicking loads that history. */
export function HistorySidebar({ conversationIds, selectedId, onSelect }: HistorySidebarProps) {
  return (
    <aside className="w-60 shrink-0">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
        Conversations
      </h2>
      {conversationIds.length === 0 ? (
        <p className="text-sm text-gray-400">No conversations yet.</p>
      ) : (
        <ul className="space-y-1">
          {conversationIds.map((id) => (
            <li key={id}>
              <button
                type="button"
                onClick={() => onSelect(id)}
                className={`w-full truncate rounded px-2 py-1 text-left text-sm ${
                  id === selectedId ? "bg-blue-100 text-blue-800" : "text-gray-700 hover:bg-gray-100"
                }`}
                title={id}
              >
                {id.slice(0, 8)}…
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
