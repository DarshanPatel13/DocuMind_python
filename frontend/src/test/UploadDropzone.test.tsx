import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { UploadDropzone } from "../components/UploadDropzone";
import { renderWithClient } from "./utils";

describe("UploadDropzone", () => {
  it("shows the drop prompt", () => {
    renderWithClient(<UploadDropzone />);
    expect(screen.getByText(/drag .* drop a pdf/i)).toBeInTheDocument();
  });

  it("rejects a non-PDF file with a validation message", () => {
    renderWithClient(<UploadDropzone />);
    const input = screen.getByTestId("file-input");
    const txt = new File(["hello"], "notes.txt", { type: "text/plain" });

    fireEvent.change(input, { target: { files: [txt] } });

    expect(screen.getByText(/only pdf files are accepted/i)).toBeInTheDocument();
  });
});
