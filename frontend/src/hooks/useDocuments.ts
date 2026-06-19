import { useQuery } from "@tanstack/react-query";

import { listDocuments } from "../api/documind";
import type { DocumentResponse } from "../types";

export const DOCUMENTS_QUERY_KEY = ["documents"] as const;

/**
 * Fetches the document list and auto-polls every 3s while any document is still
 * being ingested (UPLOADED/PROCESSING), so the status badges advance to READY
 * on their own. Polling stops once everything is settled.
 */
export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: listDocuments,
    refetchInterval: (query) => {
      const docs = query.state.data as DocumentResponse[] | undefined;
      const stillWorking = docs?.some(
        (d) => d.status === "UPLOADED" || d.status === "PROCESSING",
      );
      return stillWorking ? 3000 : false;
    },
  });
}
