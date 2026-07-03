"""HTTP client for running eval cases against the real DocuMind API (gateway).

Handles JWT login, fixture ingestion (upload + poll to READY), and the SSE ask
stream — including the gateway's 10/min rate limit on /api/ask (429s are
retried with a backoff sleep instead of failing the run).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx


@dataclass
class AskResult:
    answer: str = ""
    citations: list[tuple[str, int]] = field(default_factory=list)   # (filename, chunk_index)
    context_chunks: list[dict] = field(default_factory=list)         # full text when debug=true


class DocuMindClient:
    def __init__(self, base_url: str, username: str = "demo", password: str = "demo12345") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=httpx.Timeout(30, read=600))
        token = self._client.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password},
        ).raise_for_status().json()["access_token"]
        self._headers = {"Authorization": f"Bearer {token}"}

    def upload(self, pdf_path: Path) -> str:
        with pdf_path.open("rb") as fh:
            response = self._client.post(
                f"{self.base_url}/api/documents",
                headers=self._headers,
                files={"file": (pdf_path.name, fh, "application/pdf")},
            )
        response.raise_for_status()
        return str(response.json()["document_id"])

    def wait_ready(self, document_id: str, timeout_s: int = 300) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            docs = self._client.get(
                f"{self.base_url}/api/documents", headers=self._headers
            ).raise_for_status().json()
            doc = next((d for d in docs if str(d["id"]) == document_id), None)
            if doc and doc["status"] == "READY":
                return
            if doc and doc["status"] == "FAILED":
                raise RuntimeError(f"fixture ingestion FAILED: {doc.get('failure_reason')}")
            time.sleep(2)
        raise TimeoutError(f"document {document_id} not READY within {timeout_s}s")

    def ask(self, question: str, document_id: str | None = None, *, debug: bool = True) -> AskResult:
        body: dict = {"question": question, "debug": debug}
        if document_id:
            body["document_id"] = document_id

        for attempt in range(6):
            result = AskResult()
            with self._client.stream(
                "POST", f"{self.base_url}/api/ask", headers=self._headers, json=body
            ) as response:
                if response.status_code == 429:   # gateway rate limit: wait out the window
                    time.sleep(15)
                    continue
                response.raise_for_status()
                tokens: list[str] = []
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    event = json.loads(line[5:].strip())
                    kind = event.get("type")
                    if kind == "citations":
                        result.citations = [
                            (c["filename"], int(c["chunk_index"])) for c in event.get("citations", [])
                        ]
                    elif kind == "context":
                        result.context_chunks = list(event.get("chunks", []))
                    elif kind == "token":
                        tokens.append(event.get("token", ""))
                result.answer = "".join(tokens).strip()
            return result
        raise RuntimeError("rate-limited on /api/ask after 6 attempts")
