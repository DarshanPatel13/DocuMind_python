import { useQuery } from "@tanstack/react-query";

import { getConversation } from "../api/documind";

/**
 * Loads one conversation's history. Disabled until an id is selected, so it
 * never fires for an empty selection.
 */
export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => getConversation(conversationId as string),
    enabled: conversationId !== null,
  });
}
