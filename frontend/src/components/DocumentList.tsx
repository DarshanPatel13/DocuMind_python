import { FileText } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";

import { useDocuments } from "../hooks/useDocuments";
import { StatusBadge } from "./StatusBadge";

export function DocumentList() {
  const { data, isLoading, isError } = useDocuments();

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }
  if (isError) return <p className="text-sm text-destructive">Failed to load documents.</p>;
  if (!data || data.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
        No documents yet. Upload a PDF to begin.
      </div>
    );
  }

  return (
    <ul className="divide-y rounded-xl border bg-card">
      {data.map((doc) => (
        <li key={doc.id} className="flex items-center justify-between gap-4 px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="truncate font-medium">{doc.filename}</p>
              <p className="text-xs text-muted-foreground">
                {doc.chunk_count} chunk{doc.chunk_count === 1 ? "" : "s"}
                {doc.failure_reason ? ` · ${doc.failure_reason}` : ""}
              </p>
            </div>
          </div>
          <StatusBadge status={doc.status} />
        </li>
      ))}
    </ul>
  );
}
