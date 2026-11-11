from __future__ import annotations

import base64
import os
from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from legal_matter_service import InfraiError, LegalMatterIndex
from matter_follow_up import decide_follow_up


app = FastAPI(title="Legal matter document answers")


class MatterIntake(BaseModel):
    matter_id: str
    document_id: str
    scanned_pdf_base64: str
    deadline: date
    signed_delivered_on: date | None = None


class IntakeResult(BaseModel):
    matter_id: str
    indexed_characters: int
    status: str
    follow_up_on: date | None


class MatterQuestion(BaseModel):
    matter_id: str
    question: str = Field(min_length=3)


class MatterAnswer(BaseModel):
    answer: str
    source_document_ids: list[str]


def index() -> LegalMatterIndex:
    return LegalMatterIndex(os.environ.get("INFRAI_COLLECTION", "legal-matters"))


@app.exception_handler(InfraiError)
async def infrai_error_handler(_, exc: InfraiError):
    from fastapi.responses import JSONResponse

    client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=client_status, content={"error": exc.detail})


@app.post("/matters/intake", response_model=IntakeResult)
def intake_matter(request: MatterIntake) -> IntakeResult:
    try:
        pdf_bytes = base64.b64decode(request.scanned_pdf_base64, validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="scanned_pdf_base64 must be valid base64") from exc
    client = index()
    try:
        count = client.ingest_scan(request.matter_id, request.document_id, pdf_bytes)
    finally:
        client.close()
    decision = decide_follow_up(request.signed_delivered_on, request.deadline)
    return IntakeResult(
        matter_id=request.matter_id,
        indexed_characters=count,
        status=decision.status,
        follow_up_on=decision.follow_up_on,
    )


@app.post("/matters/answer", response_model=MatterAnswer)
def answer_matter(request: MatterQuestion) -> MatterAnswer:
    client = index()
    try:
        answer, sources = client.answer(request.matter_id, request.question)
    finally:
        client.close()
    return MatterAnswer(answer=answer, source_document_ids=sources)
