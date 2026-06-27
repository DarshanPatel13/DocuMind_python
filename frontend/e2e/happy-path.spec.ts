import { expect, test } from "@playwright/test";

// One end-to-end happy path: login → ask → streamed answer → citation preview.
// All gateway endpoints are mocked, so this runs hermetically (no backend).

const SSE = [
  'data: {"type":"citations","conversation_id":"c1","citations":[{"filename":"acme_handbook.md","chunk_index":1,"snippet":"Full-time employees receive 20 days of paid time off (PTO) per year."}]}',
  "",
  'data: {"type":"token","token":"You get "}',
  "",
  'data: {"type":"token","token":"20 days of PTO. [acme_handbook.md, chunk 1]"}',
  "",
  'data: {"type":"done"}',
  "",
  "",
].join("\n");

test.beforeEach(async ({ page }) => {
  await page.route("**/auth/login", (route) =>
    route.fulfill({ json: { access_token: "test-token", token_type: "bearer" } }),
  );

  await page.route("**/api/documents", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 202,
        json: { document_id: "d1", status: "UPLOADED", message: "accepted" },
      });
    }
    return route.fulfill({
      json: [
        {
          id: "d1",
          filename: "acme_handbook.md",
          status: "READY",
          uploaded_at: new Date().toISOString(),
          chunk_count: 3,
          failure_reason: null,
        },
      ],
    });
  });

  await page.route("**/api/ask", (route) =>
    route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: SSE,
    }),
  );
});

test("login, ask a question, and preview the cited source", async ({ page }) => {
  await page.goto("/");

  // Login page is pre-filled with the demo credentials.
  await page.getByRole("button", { name: /sign in/i }).click();

  // Navigate to Ask and submit a question.
  await page.getByRole("link", { name: /ask/i }).click();
  await page.getByPlaceholder(/ask a question/i).fill("How many PTO days do I get?");
  await page.getByRole("button", { name: /^ask/i }).click();

  // The streamed answer renders.
  await expect(page.getByText(/20 days of PTO/)).toBeVisible();

  // Clicking the citation chip opens the source-text preview.
  await page.getByRole("button", { name: /\[acme_handbook\.md, chunk 1\]/ }).click();
  await expect(page.getByText(/Full-time employees receive 20 days/)).toBeVisible();
});
