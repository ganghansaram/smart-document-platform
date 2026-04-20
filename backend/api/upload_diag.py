"""
업로드 진단 API (임시) — Plan-35
원격 업로드 장애 진단용. 원인 확정 후 제거.
제거 방법: 이 파일 삭제 + main.py에서 라우터 등록 1줄 삭제
"""
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

router = APIRouter(prefix="/api/diag", tags=["diag"])


class EchoRequest(BaseModel):
    message: str = "ping"


class EchoResponse(BaseModel):
    message: str
    method: str


class UploadTestResponse(BaseModel):
    success: bool
    filename: str
    size: int
    content_type: str


@router.post("/echo", response_model=EchoResponse)
async def diag_echo(body: EchoRequest):
    """Step 4: POST 메서드 도달 확인 (빈 JSON → 그대로 반환)"""
    return EchoResponse(message=body.message, method="POST")


@router.post("/upload-test", response_model=UploadTestResponse)
async def diag_upload_test(file: UploadFile = File(...)):
    """Step 5: multipart 파일 수신 확인 (저장/변환 없이 메타만 반환)"""
    contents = await file.read()
    return UploadTestResponse(
        success=True,
        filename=file.filename,
        size=len(contents),
        content_type=file.content_type or "unknown",
    )
