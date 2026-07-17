"""
문서 저장 API
"""
import os
import re
import json
import shutil
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from dependencies import require_editor

logger = logging.getLogger(__name__)

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


# ── 저작 마크다운 저장 (Plan-60 Phase 2a · Plan-72 P4 소유권) ─────────────
# 기존 save_document(HTML, prettify 적용, 기존 파일만)와 별개:
#  - data/authored/ 전용 저장 (신규 파일 생성 지원, 원문 그대로 — prettify 미적용)
#  - Plan-72 P4: 저작 .md 는 정적 서빙 루트(contents/) 밖 data/authored/ 에 둔다.
#    contents/ 는 nginx/http.server/Tomcat 이 무인증 정적 서빙 → 소유권 누수.
#    data/ 는 nginx 403(화이트리스트 3파일 제외) → 정적 접근 차단, API 경유(소유자 인증)만 허용.
#  - 소유권 SSOT = 서버측 _owners.json (front matter author 는 표시용·위조가능이라 권한 판정 미사용)
AUTHORED_STORE_DIR = os.path.join(PROJECT_ROOT, "data", "authored")
AUTHORED_OWNERS_PATH = os.path.join(AUTHORED_STORE_DIR, "_owners.json")
# 허용 파일명: 한글·영숫자·공백·- _ . ( ) + 확장자 .md (디렉토리 성분 불허)
_SAFE_MD_NAME = re.compile(r"^[\w\-. ()가-힣]+\.md$")


def _resolve_store_path(name: str) -> str:
    """저작 .md 파일명(단일, 디렉토리 성분 없음)만 허용하고 data/authored/ 물리 경로를 반환한다."""
    base = os.path.basename((name or "").strip().replace("\\", "/"))
    if not _SAFE_MD_NAME.match(base):
        raise HTTPException(status_code=400,
                            detail="Invalid filename (허용: 한글·영숫자·공백·-_.() + .md)")
    return os.path.join(AUTHORED_STORE_DIR, base)


def _load_owners() -> dict:
    """소유권 인덱스 로드 ({ '<파일명>.md': {owner, created_at, modified} })."""
    if not os.path.exists(AUTHORED_OWNERS_PATH):
        return {}
    try:
        with open(AUTHORED_OWNERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_owners(data: dict):
    """소유권 인덱스 원자적 저장 (compare._save_history 패턴: tmp write → replace)."""
    os.makedirs(AUTHORED_STORE_DIR, exist_ok=True)
    tmp = AUTHORED_OWNERS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, AUTHORED_OWNERS_PATH)


class SaveMarkdownRequest(BaseModel):
    name: str            # 저작 .md 파일명 (디렉토리 성분 없음, 예: 제목.md)
    content: str
    createBackup: bool = True
    overwrite: bool = True


class SaveMarkdownResponse(BaseModel):
    success: bool
    message: str
    name: str
    created: bool = False
    backupPath: str | None = None


@router.post("/save-markdown", response_model=SaveMarkdownResponse)
async def save_markdown(request: SaveMarkdownRequest, user: dict = Depends(require_editor)):
    """저작 마크다운(.md)을 data/authored/ 에 저장하고 소유자를 서버측에 캡처한다.

    - 신규 생성 + 기존 덮어쓰기 모두 지원 (overwrite=False 면 기존 존재 시 409)
    - 기존 문서는 소유자 본인만 덮어쓰기 가능 (타인 문서 403)
    - 덮어쓰기 시 기존본을 backups/ 에 백업 · HTML prettify 미적용(원문 그대로)
    """
    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="빈 내용은 저장할 수 없습니다.")
    try:
        file_path = _resolve_store_path(request.name)
        base = os.path.basename(file_path)
        owners = _load_owners()
        exists = os.path.exists(file_path)

        # 소유권 검사 — 기존 문서면 소유자 본인만 수정 가능.
        # fail-closed: 소유자 미기록(고아·인덱스 파싱실패) 파일도 '타인 소유'로 간주해 거부한다
        # (읽기 경로 list/content 와 대칭 — write 만 열려 소유권 탈취되는 것을 차단).
        if exists:
            if (owners.get(base) or {}).get("owner") != user["username"]:
                raise HTTPException(status_code=403, detail="다른 사용자의 문서는 수정할 수 없습니다.")
            if not request.overwrite:
                raise HTTPException(status_code=409, detail="이미 존재하는 문서입니다 (overwrite=false).")

        os.makedirs(AUTHORED_STORE_DIR, exist_ok=True)

        # 백업은 best-effort — 실패해도 저장(주 작업)은 진행한다(안전망 상실 뿐, 저장 차단 아님).
        backup_path = None
        if exists and request.createBackup:
            try:
                backup_dir = os.path.join(PROJECT_ROOT, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = os.path.splitext(base)[0]
                backup_filename = f"{stem}_{timestamp}.md.bak"
                shutil.copy2(file_path, os.path.join(backup_dir, backup_filename))
                backup_path = f"backups/{backup_filename}"
            except OSError as e:
                logger.warning("저작 문서 백업 실패 (저장은 계속): %s — %s", base, e)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.content)

        # 소유권 인덱스 갱신 — 신규면 owner 캡처(서버측 신뢰 user), 기존이면 owner 유지
        now = datetime.now().isoformat()
        rec = owners.get(base) or {}
        if not rec.get("owner"):
            rec["owner"] = user["username"]
            rec["created_at"] = now
        rec["modified"] = now
        owners[base] = rec
        _save_owners(owners)

        return SaveMarkdownResponse(
            success=True,
            message="Markdown saved successfully",
            name=base,
            created=not exists,
            backupPath=backup_path,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save markdown: {str(e)}")


def _read_front_matter_fields(abs_path: str, keys) -> dict:
    """파일 선두 front matter 에서 지정 키들의 값을 추출한다 (없으면 빈 dict).

    md-editor.js buildFrontMatter 형식과 일치: `key: "값"` (BOM·따옴표 허용).
    """
    out = {}
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            head = f.read(2048)
    except OSError:
        return out
    head = head.lstrip("﻿")
    if not head.startswith("---"):
        return out
    end = head.find("\n---", 3)
    if end == -1:
        return out
    wanted = set(keys)
    for line in head[3:end].splitlines():
        m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.+?)\s*$", line)
        if m and m.group(1) in wanted:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


@router.get("/authored")
def list_authored(user: dict = Depends(require_editor)):
    """로그인 사용자가 소유한 저작 마크다운 목록을 반환한다 (Author 좌측 패널용).

    각 항목: { label(front matter title→없으면 파일명), author, name, modified }. 최신 수정순.
    Plan-72 P4: 인증 필수 + 소유자 한정 (admin 예외 없음). data/authored/ 에서 읽는다.
    """
    owners = _load_owners()
    docs = []
    if os.path.isdir(AUTHORED_STORE_DIR):
        for name in os.listdir(AUTHORED_STORE_DIR):
            if not name.lower().endswith(".md"):
                continue
            abs_path = os.path.join(AUTHORED_STORE_DIR, name)
            if not os.path.isfile(abs_path):
                continue
            # 소유자 한정 — 인덱스에 없거나(고아) 타인 소유면 제외
            if (owners.get(name) or {}).get("owner") != user["username"]:
                continue
            try:
                mtime = os.stat(abs_path).st_mtime
            except OSError:
                continue
            fields = _read_front_matter_fields(abs_path, ("title", "author"))
            title = fields.get("title") or os.path.splitext(name)[0]
            docs.append({
                "label": title,
                "author": fields.get("author", ""),
                "name": name,
                "modified": datetime.fromtimestamp(mtime).isoformat(),
            })
    docs.sort(key=lambda d: d["modified"], reverse=True)
    return {"documents": docs}


@router.get("/authored/content", response_class=PlainTextResponse)
def get_authored_content(name: str, user: dict = Depends(require_editor)):
    """저작 .md 원문을 인증·소유자 확인 후 반환한다 (정적 서빙 대체 — Plan-72 P4).

    소유자 본인만 열람 가능. contents/ 정적 서빙을 우회하지 않고 이 엔드포인트를 경유해야
    소유권 게이팅이 성립한다 (data/authored/ 는 nginx 403).
    """
    file_path = _resolve_store_path(name)
    base = os.path.basename(file_path)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    if (_load_owners().get(base) or {}).get("owner") != user["username"]:
        raise HTTPException(status_code=403, detail="다른 사용자의 문서입니다.")
    with open(file_path, "r", encoding="utf-8") as f:
        return PlainTextResponse(f.read())


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
