import { DocumentList } from "../components/DocumentList";
import { UploadDropzone } from "../components/UploadDropzone";

export function UploadPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <section>
        <h1 className="mb-1 text-2xl font-semibold text-gray-900">Upload documents</h1>
        <p className="mb-4 text-gray-600">
          Upload a PDF; it is ingested in the background. Watch the status move to READY, then
          head to Ask.
        </p>
        <UploadDropzone />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Your documents</h2>
        <DocumentList />
      </section>
    </div>
  );
}
