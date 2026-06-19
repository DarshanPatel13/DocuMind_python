import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { uploadDocument } from "../api/documind";
import { DOCUMENTS_QUERY_KEY } from "./useDocuments";

/**
 * Upload mutation. On success it invalidates the documents query so the list
 * refreshes immediately (and the polling in useDocuments takes over to watch
 * the new doc progress to READY).
 */
export function useUpload() {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file, setProgress),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
    onSettled: () => setProgress(0),
  });

  return { ...mutation, progress };
}
