import type { DocumentStatus } from "../types";

const STYLES: Record<DocumentStatus, string> = {
  UPLOADED: "bg-gray-100 text-gray-700",
  PROCESSING: "bg-amber-100 text-amber-800",
  READY: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {status}
    </span>
  );
}
