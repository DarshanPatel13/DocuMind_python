"""Document upload + listing endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session
from app.models.schemas import DocumentResponse, UploadResponse
from app.services import document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> UploadResponse:
    """Store a PDF and ingest it asynchronously. Returns 202 immediately."""
    content = await file.read()
    return await document_service.upload(session, file.filename, file.content_type, content)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    session: AsyncSession = Depends(get_session),
) -> list[DocumentResponse]:
    return await document_service.list_documents(session)
