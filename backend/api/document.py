"""
문서 저장 API
"""
import os
import re
import shutil
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from dependencies import require_editor

router = APIRouter(tags=["document"])


def prettify_html(html: str) -> str:
    """
    HTML을 읽기 쉽게 포맷팅
    - 블록 태그 앞뒤로 줄바꿈 추가
    - 들여쓰기 적용
    """
    # 블록 레벨 태그 목록
    block_tags = ['html', 'head', 'body', 'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
                  'header', 'footer', 'nav', 'section', 'article', 'aside',
                  'blockquote', 'pre', 'figure', 'figcaption', 'hr', 'br']

    # 여는 태그 앞에 줄바꿈
    for tag in block_tags:
        html = re.sub(rf'(<{tag}[^>]*>)', r'\n\1', html, flags=re.IGNORECASE)
        # 닫는 태그 뒤에 줄바꿈
        html = re.sub(rf'(</{tag}>)', r'\1\n', html, flags=re.IGNORECASE)

    # 연속된 줄바꿈 정리
    html = re.sub(r'\n\s*\n+', '\n\n', html)

    # 앞뒤 공백 제거
    html = html.strip()

    return html

# 프로젝트 루트 디렉토리 (backend 폴더의 상위)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SaveDocumentRequest(BaseModel):
    path: str
    content: str
    createBackup: bool = True


class SaveDocumentResponse(BaseModel):
    success: bool
    message: str
    backupPath: str | None = None


@router.post("/save-document", response_model=SaveDocumentResponse)
async def save_document(request: SaveDocumentRequest, user: dict = Depends(require_editor)):
    """
    문서 저장 API
    - path: contents/ 하위 경로 (예: contents/doc1.html)
    - content: HTML 콘텐츠
    - createBackup: 백업 파일 생성 여부
    """
    try:
        # 경로 검증 (보안: contents 폴더 외부 접근 방지)
        if not request.path.startswith("contents/"):
            raise HTTPException(status_code=400, detail="Invalid path: must be under contents/")

        # 절대 경로 생성
        file_path = os.path.normpath(os.path.join(PROJECT_ROOT, request.path))

        # 경로 탈출 방지 (path traversal 공격 방지)
        if not file_path.startswith(os.path.join(PROJECT_ROOT, "contents")):
            raise HTTPException(status_code=400, detail="Invalid path: path traversal detected")

        # 파일 존재 확인
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Document not found")

        backup_path = None

        # 백업 생성
        if request.createBackup:
            backup_dir = os.path.join(PROJECT_ROOT, "backups")
            os.makedirs(backup_dir, exist_ok=True)

            # 백업 파일명: 원본파일명_YYYYMMDD_HHMMSS.bak
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = os.path.basename(file_path)
            backup_filename = f"{os.path.splitext(original_name)[0]}_{timestamp}.bak"
            backup_path = os.path.join(backup_dir, backup_filename)

            # 기존 파일 백업
            shutil.copy2(file_path, backup_path)
            backup_path = f"backups/{backup_filename}"  # 상대 경로로 반환

        # HTML 포맷팅 후 저장
        formatted_content = prettify_html(request.content)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted_content)

        return SaveDocumentResponse(
            success=True,
            message="Document saved successfully",
            backupPath=backup_path
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save document: {str(e)}")


@router.get("/document-history/{path:path}")
async def get_document_history(path: str):
    """
    문서 백업 히스토리 조회
    """
    try:
        if not path.startswith("contents/"):
            raise HTTPException(status_code=400, detail="Invalid path")

        backup_dir = os.path.join(PROJECT_ROOT, "backups")
        if not os.path.exists(backup_dir):
            return {"history": []}

        # 해당 문서의 백업 파일 목록
        original_name = os.path.basename(path)
        base_name = os.path.splitext(original_name)[0]

        backups = []
        for filename in os.listdir(backup_dir):
            if filename.startswith(base_name) and filename.endswith(".bak"):
                backup_path = os.path.join(backup_dir, filename)
                stat = os.stat(backup_path)
                backups.append({
                    "filename": filename,
                    "path": f"backups/{filename}",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        # 최신순 정렬
        backups.sort(key=lambda x: x["modified"], reverse=True)

        return {"history": backups}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.post("/restore-document")
async def restore_document(path: str, backup_path: str, user: dict = Depends(require_editor)):
    """
    백업에서 문서 복원
    """
    try:
        # 경로 검증
        if not path.startswith("contents/"):
            raise HTTPException(status_code=400, detail="Invalid path")

        file_path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
        backup_full_path = os.path.normpath(os.path.join(PROJECT_ROOT, backup_path))

        # 경로 탈출 방지
        if not file_path.startswith(os.path.join(PROJECT_ROOT, "contents")):
            raise HTTPException(status_code=400, detail="Invalid document path")
        if not backup_full_path.startswith(os.path.join(PROJECT_ROOT, "backups")):
            raise HTTPException(status_code=400, detail="Invalid backup path")

        if not os.path.exists(backup_full_path):
            raise HTTPException(status_code=404, detail="Backup not found")

        # 현재 파일 백업 후 복원
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = os.path.basename(file_path)
        temp_backup = os.path.join(
            PROJECT_ROOT, "backups",
            f"{os.path.splitext(original_name)[0]}_{timestamp}_before_restore.bak"
        )
        shutil.copy2(file_path, temp_backup)

        # 백업 파일로 복원
        shutil.copy2(backup_full_path, file_path)

        return {
            "success": True,
            "message": "Document restored successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore: {str(e)}")
