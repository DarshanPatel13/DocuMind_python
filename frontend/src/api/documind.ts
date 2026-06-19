import type { AxiosProgressEvent } from "axios";

import type {
  AskRequest,
  AskStreamHandlers,
  ConversationHistory,
  DocumentResponse,
  StreamEvent,
  UploadResponse,
} from "../types";
import { API_BASE_URL, apiClient } from "./client";

export async function listDocuments(): Promise<DocumentResponse[]> {
  const { data } = await apiClient.get<DocumentResponse[]>("/api/documents");
  return data;
}

export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<UploadResponse>("/api/documents", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event: AxiosProgressEvent) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return data;
}

export async function getConversation(conversationId: string): Promise<ConversationHistory> {
  const { data } = await apiClient.get<ConversationHistory>(
    `/api/conversations/${conversationId}`,
  );
  return data;
}

/**
 * POST /api/ask and consume the Server-Sent Events stream, dispatching each
 * parsed event to the handlers. Uses fetch + ReadableStream because we need
 * incremental reads — axios buffers the whole response.
 */
export async function streamAsk(
  body: AskRequest,
  handlers: AskStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    handlers.onError(error instanceof Error ? error : new Error("Network error"));
    return;
  }

  if (!response.ok || !response.body) {
    handlers.onError(new Error(`Request failed with status ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by a blank line.
      let separator = buffer.indexOf("\n\n");
      while (separator !== -1) {
        const rawEvent = buffer.slice(0, separator);
        buffer = buffer.slice(separator + 2);
        dispatchEvent(rawEvent, handlers);
        separator = buffer.indexOf("\n\n");
      }
    }
    handlers.onDone();
  } catch (error) {
    handlers.onError(error instanceof Error ? error : new Error("Stream error"));
  }
}

function dispatchEvent(rawEvent: string, handlers: AskStreamHandlers): void {
  const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data:"));
  if (!dataLine) return;
  const payload = dataLine.slice(5).trim();
  if (!payload) return;

  const event = JSON.parse(payload) as StreamEvent;
  if (event.type === "citations") {
    handlers.onCitations({
      conversation_id: event.conversation_id,
      citations: event.citations,
    });
  } else if (event.type === "token") {
    handlers.onToken(event.token);
  }
  // "done" is signalled by the reader finishing; handled in the caller.
}
