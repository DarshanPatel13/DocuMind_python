import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import type { Citation } from "../types";

/** Renders a citation as the chip [filename, chunk N]; clicking opens a preview
 * of the exact source chunk the answer was grounded on. */
export function CitationChip({ citation }: { citation: Citation }) {
  const label = `[${citation.filename}, chunk ${citation.chunk_index}]`;
  return (
    <Dialog>
      <DialogTrigger className="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        {label}
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="break-all">{citation.filename}</DialogTitle>
          <DialogDescription>Chunk {citation.chunk_index} · retrieved source</DialogDescription>
        </DialogHeader>
        <div className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-md bg-muted p-3 text-sm leading-relaxed">
          {citation.snippet ?? "No preview available for this source."}
        </div>
      </DialogContent>
    </Dialog>
  );
}
