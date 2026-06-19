import { useRef, useState } from "react";

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
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
          dragOver ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white hover:border-gray-400"
        }`}
      >
        <p className="font-medium text-gray-700">Drag &amp; drop a PDF here</p>
        <p className="mt-1 text-sm text-gray-500">or click to choose a file (max 20 MB)</p>
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
          <div className="h-2 w-full overflow-hidden rounded bg-gray-200">
            <div className="h-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-1 text-xs text-gray-500">Uploading… {progress}%</p>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {isError && <p className="mt-3 text-sm text-red-600">Upload failed. Please try again.</p>}
      {isSuccess && !error && (
        <p className="mt-3 text-sm text-green-600">Uploaded — processing has started.</p>
      )}
    </div>
  );
}
