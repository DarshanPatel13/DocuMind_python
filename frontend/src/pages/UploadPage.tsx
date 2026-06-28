import { DocumentList } from "../components/DocumentList";
import { UploadDropzone } from "../components/UploadDropzone";

export function UploadPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <section className="text-center">
        <h1 className="text-[34px] font-semibold leading-tight tracking-tight sm:text-[40px]">
          Bring your documents to life.
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-[17px] text-muted-foreground">
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
