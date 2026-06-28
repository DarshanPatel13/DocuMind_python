import { Sparkles } from "lucide-react";

import { DocumentList } from "../components/DocumentList";
import { UploadDropzone } from "../components/UploadDropzone";

export function UploadPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <section className="pt-6 text-center">
        <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border bg-secondary/50 px-3.5 py-1.5 text-xs font-medium text-muted-foreground backdrop-blur">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          Retrieval-augmented · grounded in your files
        </div>
        <h1 className="text-balance text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
          Bring your documents <span className="text-gradient">to life.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-lg leading-relaxed text-muted-foreground">
          Drop in a PDF and DocuMind reads, indexes, and answers questions about it —
          grounded, cited, and private to you.
        </p>
      </section>

      <section>
        <UploadDropzone />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Your documents</h2>
        <DocumentList />
      </section>
    </div>
  );
}
