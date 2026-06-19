import type { Citation } from "../types";

/** Renders a citation as the chip [filename, chunk N]. */
export function CitationChip({ citation }: { citation: Citation }) {
  return (
    <span className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
      [{citation.filename}, chunk {citation.chunk_index}]
    </span>
  );
}
