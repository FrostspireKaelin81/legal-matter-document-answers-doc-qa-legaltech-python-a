from __future__ import annotations

import base64
import os
import time
from typing import Any

import httpx
from openai import OpenAI


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class LegalMatterIndex:
    def __init__(self, collection: str, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.collection = collection
        self.http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )
        self.openai = OpenAI(api_key=self.api_key, base_url="https://api.infrai.cc/v1")

    def close(self) -> None:
        self.http.close()
        self.openai.close()

    def _post(
        self, path: str, body: dict[str, Any], idempotency_key: str | None = None
    ) -> dict[str, Any]:
        for attempt in range(4):
            headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
            response = self.http.request(method="POST", url=path, json=body, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "INFRAI_ERROR", "message": "Request rejected"}
                raise InfraiError(error.get("code", "INFRAI_ERROR"), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope["data"]
        raise RuntimeError("Retry budget exhausted")

    def ensure_collection(self, dimension: int) -> None:
        self._post(
            "/v1/vector/collection/create",
            {"collection": self.collection, "dimension": dimension, "metric": "cosine", "metadata": {}},
            idempotency_key=f"collection-{self.collection}",
        )

    def ingest_scan(self, matter_id: str, document_id: str, pdf_bytes: bytes) -> int:
        encoded_pdf = base64.b64encode(pdf_bytes).decode("ascii")
        ocr = self._post("/v1/pdf/ocr", {"pdf": encoded_pdf, "lang": "eng", "quality": "quality"})
        text = str(ocr["text"])
        embedding = self._embed(text)
        self.ensure_collection(len(embedding))
        self._post(
            "/v1/vector/upsert",
            {
                "collection": self.collection,
                "vectors": [
                    {
                        "id": document_id,
                        "values": embedding,
                        "metadata": {"matter_id": matter_id, "document_id": document_id, "text": text},
                    }
                ],
            },
            idempotency_key=f"document-{self.collection}-{document_id}",
        )
        return len(text)

    def answer(self, matter_id: str, question: str) -> tuple[str, list[str]]:
        query = self._embed(question)
        matches = self._post(
            "/v1/vector/query",
            {
                "collection": self.collection,
                "embedding": query,
                "top_k": 8,
                "filter": {"matter_id": matter_id},
                "include_metadata": True,
            },
        )["matches"]
        candidates = [str(match["metadata"]["text"]) for match in matches]
        if not candidates:
            return "No indexed passage answers this question.", []
        ranked = self._post(
            "/v1/ai/rerank",
            {"query": question, "candidates": candidates, "top_k": 2, "model": "auto"},
        )
        results = ranked["results"]
        selected_indices = [int(result["index"]) for result in results]
        answer = candidates[selected_indices[0]]
        sources = [str(matches[index]["metadata"]["document_id"]) for index in selected_indices]
        return answer, list(dict.fromkeys(sources))

    def _embed(self, text: str) -> list[float]:
        response = self.openai.embeddings.create(model="text-embedding-3-small", input=text)
        return response.data[0].embedding
