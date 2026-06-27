import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

import type { DocumentStatus } from "../types";

const MAP = {
  UPLOADED: { variant: "secondary", icon: Clock },
  PROCESSING: { variant: "warning", icon: Loader2 },
  READY: { variant: "success", icon: CheckCircle2 },
  FAILED: { variant: "destructive", icon: XCircle },
} as const;

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const { variant, icon: Icon } = MAP[status];
  return (
    <Badge variant={variant} className="gap-1">
      <Icon className={cn("h-3 w-3", status === "PROCESSING" && "animate-spin")} />
      {status}
    </Badge>
  );
}
