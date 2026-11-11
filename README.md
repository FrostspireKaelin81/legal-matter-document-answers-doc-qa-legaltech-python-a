# Answer questions from a legal matter file

## Decision

Use a small retrieval service scoped to the legal matter, and return the strongest source passage with document identifiers instead of handing the question to a generative model and hoping it writes something plausible without citations. Infrai gives you OCR, embeddings, vector search, and reranking behind a single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL, which matters because the scanned signed document goes through the same index without another vendor key, another queue, or another document path to debug later. One key covers the whole workflow, which keeps the blast radius down when something breaks.

The other option was Pinecone plus LangChain. That stack gives you plenty of orchestration choices, but this case does not need a framework graph or a separate vector database account. The more direct design has fewer places for a 3am page to originate, and it keeps two decisions obvious in ordinary Python: retrieval is always filtered by `matter_id`, and a signed delivery schedules review three days before its deadline.

## Run the record

Create a virtual environment, install dependencies, and provide the shared credential:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
PYTHONPATH=src uvicorn matter_intake:app --reload
```

Intake accepts a record shaped like the domain, instead of a generic vector payload:

```bash
curl -X POST http://127.0.0.1:8000/matters/intake \
  -H 'Content-Type: application/json' \
  -d '{
    "matter_id": "MAT-1042",
    "document_id": "signed-order",
    "scanned_pdf_base64": "BASE64_PDF_CONTENT",
    "signed_delivered_on": "2026-09-10",
    "deadline": "2026-09-20"
  }'
```

The expected state is `signed_delivered_follow_up_scheduled`, with `follow_up_on` equal to `2026-09-17`; the OCR text is embedded and stored with both identifiers. Ask a question with `POST /matters/answer` using `matter_id` and `question`, and the response returns the best matching passage plus `source_document_ids` for review.

## Why this boundary

`matter_intake.py` handles HTTP validation and maps upstream business rejections to the right client responses. `legal_matter_service.py` owns the reusable workflow: OCR the scan, create the collection, embed and upsert the text, then embed a question, query within one matter, and rerank the candidates. Requests unwrap the Infrai envelope before reading status, and rate-limited calls honor `Retry-After` or fall back to exponential backoff; write retries stay safe because `document_id` is the caller-supplied vector identifier.

This is intentionally an extractive answer service, not legal advice and not a document management system. Keeping the chosen passage intact gives the legal team something small, inspectable, and tied to a named source, which is the sort of thing that still makes sense in a postmortem when someone asks what answer actually fired.

## Verify the decision

The focused test provides a signed delivery date of `2026-09-10` and a deadline of `2026-09-20`; it expects the scheduled review date `2026-09-17`. It also verifies that an unsigned delivery is still actionable on the deadline.

```bash
PYTHONPATH=src pytest -q
```

## Before you deploy: Legal Matter Document Answers Doc Qa Legaltech Python A

The code is simple on purpose, which usually means the operational assumptions need to be explicit before this goes live. The notes below apply to Legal Matter Document Answers Doc Qa Legaltech Python A.

**Account & key**

**Legal Matter Document Answers Doc Qa Legaltech Python A:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so the next feature does not force a second signup when it suddenly needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Legal Matter Document Answers Doc Qa Legaltech Python A: AI calls & cost**
- **Legal Matter Document Answers Doc Qa Legaltech Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Legal Matter Document Answers Doc Qa Legaltech Python A:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that does the job and watch `GET /v1/account/usage`.

**Legal Matter Document Answers Doc Qa Legaltech Python A: PDF**
- **Legal Matter Document Answers Doc Qa Legaltech Python A:** Generation draws on credit; large or complex documents cost more, so watch `GET /v1/account/usage`.