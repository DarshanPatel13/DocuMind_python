import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatView } from "../components/ChatView";
import { streamAsk } from "../api/documind";

// Mock the streaming API so the test drives the SSE handlers directly.
vi.mock("../api/documind");

describe("ChatView", () => {
  beforeEach(() => {
    vi.mocked(streamAsk).mockReset();
    vi.mocked(streamAsk).mockImplementation(async (_body, handlers) => {
      handlers.onCitations({
        conversation_id: "c1",
        citations: [{ filename: "policy.pdf", chunk_index: 2 }],
      });
      handlers.onToken("Refunds ");
      handlers.onToken("within 30 days.");
      handlers.onDone();
    });
  });

  it("streams the answer token-by-token and renders citations", async () => {
    const user = userEvent.setup();
    render(<ChatView />);

    await user.type(screen.getByPlaceholderText(/ask a question/i), "refund policy?");
    await user.click(screen.getByRole("button", { name: /ask/i }));

    expect(await screen.findByText(/Refunds within 30 days\./)).toBeInTheDocument();
    expect(screen.getByText(/\[policy\.pdf, chunk 2\]/)).toBeInTheDocument();
  });
});
