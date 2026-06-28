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
      <div className="rounded-2xl border border-dashed p-10 text-center text-sm text-muted-foreground">
        No documents yet. Upload a PDF to begin.
      </div>
    );
  }

  return (
    <ul className="divide-y overflow-hidden rounded-2xl border bg-card shadow-soft">
      {data.map((doc) => (
        <li
          key={doc.id}
          className="flex items-center justify-between gap-4 px-4 py-3.5 transition-colors hover:bg-accent/50"
        >
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-secondary text-muted-foreground">
              <FileText className="h-5 w-5" />
            </div>
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
