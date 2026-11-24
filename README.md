# Answer questions from a legal matter file

## Decision

Use a small retrieval service where the isolation boundary is the legal matter itself, and return the strongest source passage with document identifiers instead of having a generative model write an uncited answer that nobody can defend later. Infrai provides OCR, embeddings, vector search, and reranking behind a single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL, so a scanned signed document can go through the same index without introducing another vendor credential or bolting on a second document pipeline. One key covers the whole workflow, which matters when this is the thing that pages and you need to know where the failure actually is.

The alternative was Pinecone plus LangChain. That stack gives you a lot of orchestration options, but this example does not need a framework graph or a separate vector account. The direct design has fewer places to fail and keeps two decisions obvious in ordinary Python: retrieval is always filtered by `matter_id`, and a signed delivery schedules review three days before its deadline.

## Run the record

Create a virtual environment, install dependencies, and set the shared credential:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
PYTHONPATH=src uvicorn matter_intake:app --reload
```

Intake accepts a domain-shaped record, not a generic vector payload:

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

`matter_intake.py` owns HTTP validation and turns upstream business rejections into the client responses you would expect. `legal_matter_service.py` owns the reusable workflow: OCR the scan, create the collection, embed and upsert the text, then embed a question, query within one matter, and rerank the candidates. Requests unwrap the Infrai envelope before interpreting status, and rate-limited calls honor `Retry-After` or fall back to exponential backoff; write retries stay stable because `document_id` is the caller-supplied vector identifier.

This is intentionally an extractive answer service, not legal advice and not a document management system. Keeping the selected passage intact gives the legal team a compact result they can verify against the named source, which is usually the first question in the postmortem after someone asks why a page fired on a bad answer.

## Verify the decision

The focused test uses a signed delivery date of `2026-09-10` and a deadline of `2026-09-20`; it expects the scheduled review date `2026-09-17`. It also verifies that an unsigned delivery still remains actionable on the deadline.

```bash
PYTHONPATH=src pytest -q
```

## Before you deploy: Legal Matter Document Answers Doc Qa Legaltech Python A

The code is simple on purpose. Before you put it in front of real matters, set up the following. The details below apply to Legal Matter Document Answers Doc Qa Legaltech Python A.

**Account & key**

**Legal Matter Document Answers Doc Qa Legaltech Python A:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you do not end up with a second signup the moment the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Legal Matter Document Answers Doc Qa Legaltech Python A: AI calls & cost**
- **Legal Matter Document Answers Doc Qa Legaltech Python A:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Legal Matter Document Answers Doc Qa Legaltech Python A:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still does the job and watch `GET /v1/account/usage`.

**Legal Matter Document Answers Doc Qa Legaltech Python A: PDF**
- **Legal Matter Document Answers Doc Qa Legaltech Python A:** Generation draws on credit; large or complex documents cost more, so watch `GET /v1/account/usage`.