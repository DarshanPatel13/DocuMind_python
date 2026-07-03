import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getEvalStatus, runEvals } from "../api/documind";
import type { EvalStatus } from "../types";

export const EVAL_STATUS_QUERY_KEY = ["evalStatus"] as const;

/** Polls /api/evals/status every 2s while a run is in progress, else rests. */
export function useEvalStatus() {
  return useQuery({
    queryKey: EVAL_STATUS_QUERY_KEY,
    queryFn: getEvalStatus,
    refetchInterval: (query) => {
      const status = (query.state.data as EvalStatus | undefined)?.status;
      return status === "running" ? 2000 : false;
    },
  });
}

/** Starts a run, then re-fetches status immediately so the UI flips to "running". */
export function useRunEvals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: runEvals,
    onSettled: () => queryClient.invalidateQueries({ queryKey: EVAL_STATUS_QUERY_KEY }),
  });
}
