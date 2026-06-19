import { useDocuments } from "../hooks/useDocuments";
import { StatusBadge } from "./StatusBadge";

export function DocumentList() {
  const { data, isLoading, isError } = useDocuments();

  if (isLoading) return <p className="text-gray-500">Loading documents…</p>;
  if (isError) return <p className="text-red-600">Failed to load documents.</p>;
  if (!data || data.length === 0) {
    return <p className="text-gray-500">No documents yet. Upload a PDF to begin.</p>;
  }

  return (
    <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
      {data.map((doc) => (
        <li key={doc.id} className="flex items-center justify-between gap-4 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate font-medium text-gray-800">{doc.filename}</p>
            <p className="text-xs text-gray-500">
              {doc.chunk_count} chunk{doc.chunk_count === 1 ? "" : "s"}
              {doc.failure_reason ? ` · ${doc.failure_reason}` : ""}
            </p>
          </div>
          <StatusBadge status={doc.status} />
        </li>
      ))}
    </ul>
  );
}
