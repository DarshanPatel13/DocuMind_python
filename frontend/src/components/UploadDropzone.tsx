import { UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";

import { useUpload } from "../hooks/useUpload";

const MAX_BYTES = 20 * 1024 * 1024;

/**
 * Drag-and-drop (or click-to-pick) PDF upload. Validates type and size on the
 * client for instant feedback; the backend re-validates authoritatively.
 */
export function UploadDropzone() {
  const { mutate, isPending, progress, isError, isSuccess } = useUpload();
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isSuccess) toast.success("Uploaded — ingestion has started");
  }, [isSuccess]);
  useEffect(() => {
    if (isError) toast.error("Upload failed. Please try again.");
  }, [isError]);

  const handleFile = (file: File | undefined): void => {
    setError(null);
    if (!file) return;
    const isPdf =
      file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setError("Only PDF files are accepted");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("File exceeds the 20 MB limit");
      return;
    }
    mutate(file);
  };

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
        className={cn(
          "group flex cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed p-14 text-center shadow-soft transition-all duration-200",
          dragOver
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border bg-card hover:border-primary/40 hover:shadow-card",
        )}
      >
        <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-secondary text-muted-foreground transition-colors group-hover:bg-primary/10 group-hover:text-primary">
          <UploadCloud className="h-7 w-7" />
        </div>
        <p className="text-[17px] font-medium">Drag &amp; drop a PDF here</p>
        <p className="mt-1 text-sm text-muted-foreground">or click to choose a file · max 20 MB</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="sr-only"
          data-testid="file-input"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      {isPending && (
        <div className="mt-3">
          <div className="h-2 w-full overflow-hidden rounded bg-muted">
            <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Uploading… {progress}%</p>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
    </div>
  );
}
