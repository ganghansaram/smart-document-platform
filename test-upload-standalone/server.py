"""
Upload Standalone Test Server (Plan-35 격리 테스트)

플랫폼의 복잡한 레이어(Nginx 프록시, CORS, 쿠키 인증, NDJSON 스트리밍, RAG 재인덱싱)를
모두 배제한 최소 구현. 원격 DOCX 업로드가 되는지 판정하고, 성공 시 플랫폼과의 차이를 추적한다.

실행: python server.py  (또는 start.bat)
포트: 8080 / Host: 0.0.0.0
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn


BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
LOG_FILE = BASE_DIR / "server.log"
INDEX_HTML = BASE_DIR / "index.html"

UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
SUBPROCESS_TIMEOUT = 300

PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")


logger = logging.getLogger("upload-standalone")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)
logger.addHandler(_sh)
try:
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setFormatter(_fmt)
    logger.addHandler(_fh)
except OSError as exc:
    print(f"[warn] log file open failed: {exc}", file=sys.stderr)


def resolve_converter() -> tuple[list[str], str]:
    """변환기 명령 결정: exe > python script. (cmd_prefix, source_label)"""
    override = os.environ.get("DOCX2HTML_EXE", "").strip()
    if override:
        p = Path(override)
        if p.exists() and p.suffix.lower() == ".exe":
            return [str(p)], f"env:exe={p}"
        if p.exists() and p.suffix.lower() == ".py":
            return [sys.executable, str(p)], f"env:py={p}"
        return [override], f"env:raw={override}"

    exe = BASE_DIR.parent / "tools" / "docx2html-standalone" / "dist" / "docx2html.exe"
    if exe.exists():
        return [str(exe)], f"exe={exe}"

    py = BASE_DIR.parent / "tools" / "docx2html-standalone" / "docx2html.py"
    if py.exists():
        return [sys.executable, str(py)], f"py={py}"

    return [], "none"


CONVERTER_CMD, CONVERTER_SOURCE = resolve_converter()


app = FastAPI(title="Upload Standalone Test", docs_url=None, redoc_url=None)
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


@app.get("/")
async def index():
    if not INDEX_HTML.exists():
        raise HTTPException(500, "index.html not found")
    return FileResponse(INDEX_HTML, media_type="text/html; charset=utf-8")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "converter_source": CONVERTER_SOURCE,
        "converter_cmd": CONVERTER_CMD,
        "converter_ready": bool(CONVERTER_CMD),
        "uploads_dir": str(UPLOADS_DIR),
        "output_dir": str(OUTPUT_DIR),
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "host": HOST,
        "port": PORT,
        "python": sys.version.split()[0],
    }


def _sanitize_name(raw: str) -> str:
    safe = Path(raw).name.strip()
    return safe or "upload.docx"


@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    client_ip = request.client.host if request.client else "?"
    raw_name = file.filename or "unnamed"
    safe_name = _sanitize_name(raw_name)

    if not safe_name.lower().endswith(".docx"):
        logger.warning("reject [%s] %s — ext", client_ip, raw_name)
        raise HTTPException(400, "DOCX 파일만 허용됩니다.")

    data = await file.read()
    size = len(data)
    if size == 0:
        raise HTTPException(400, "빈 파일입니다.")
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"파일이 너무 큽니다. 최대 {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    if not data.startswith(b"PK\x03\x04"):
        raise HTTPException(400, "DOCX 파일 형식이 아닙니다 (ZIP 헤더 검증 실패).")

    if not CONVERTER_CMD:
        logger.error("converter not configured")
        raise HTTPException(
            500,
            "변환기가 없습니다. docx2html.exe 빌드 또는 DOCX2HTML_EXE 환경변수 설정 필요.",
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    stem = Path(safe_name).stem
    input_path = UPLOADS_DIR / f"{ts}_{safe_name}"
    job_out_dir = OUTPUT_DIR / f"{ts}_{stem}"
    job_out_dir.mkdir(parents=True, exist_ok=True)

    input_path.write_bytes(data)

    cmd = CONVERTER_CMD + [
        str(input_path),
        "-o",
        str(job_out_dir),
        "--no-preprocess",
    ]
    logger.info("convert [%s] %s (%d bytes) -> %s", client_ip, safe_name, size, job_out_dir.name)

    t0 = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=SUBPROCESS_TIMEOUT,
            encoding="utf-8",
            errors="replace",
            cwd=str(BASE_DIR),
            shell=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.error("timeout [%s] %s", client_ip, safe_name)
        raise HTTPException(504, f"변환 시간 초과 ({SUBPROCESS_TIMEOUT}s)")
    except FileNotFoundError as exc:
        logger.error("converter not found: %s", exc)
        raise HTTPException(500, f"변환기 실행 파일을 찾을 수 없습니다: {exc}")
    except Exception as exc:
        logger.exception("subprocess failed")
        raise HTTPException(500, f"변환기 실행 실패: {exc}")

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    output_html: Path | None = None
    if stdout.strip():
        last_line = stdout.strip().splitlines()[-1].strip()
        candidate = Path(last_line)
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() == ".html":
            output_html = candidate
    if output_html is None:
        html_files = sorted(job_out_dir.glob("*.html"))
        if html_files:
            output_html = html_files[0]

    # 변환기가 stdout 인코딩 문제 등으로 rc!=0 이어도 HTML이 생성됐으면 성공 간주
    soft_success = proc.returncode != 0 and output_html is not None
    success = proc.returncode == 0 or soft_success

    output_rel = None
    if output_html:
        try:
            output_rel = output_html.relative_to(OUTPUT_DIR).as_posix()
        except ValueError:
            output_rel = None

    result = {
        "success": success,
        "soft_success": soft_success,
        "input_name": safe_name,
        "input_size": size,
        "saved_to": input_path.relative_to(BASE_DIR).as_posix(),
        "output_dir": job_out_dir.relative_to(BASE_DIR).as_posix(),
        "output_html": output_rel,
        "output_url": f"/output/{output_rel}" if output_rel else None,
        "elapsed_ms": elapsed_ms,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "converter_source": CONVERTER_SOURCE,
    }

    if success:
        logger.info("done [%s] %s -> %s (%d ms)", client_ip, safe_name, output_rel, elapsed_ms)
    else:
        logger.error(
            "fail [%s] %s rc=%d (%d ms) stderr=%s",
            client_ip, safe_name, proc.returncode, elapsed_ms, stderr[:200],
        )

    return JSONResponse(result, status_code=200 if success else 500)


def main():
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    logger.info("=== Upload Standalone Test Server (Plan-35) ===")
    logger.info("python      : %s", sys.version.split()[0])
    logger.info("base_dir    : %s", BASE_DIR)
    logger.info("converter   : %s", CONVERTER_SOURCE)
    logger.info("converter_cmd: %s", CONVERTER_CMD or "(none)")
    logger.info("uploads_dir : %s", UPLOADS_DIR)
    logger.info("output_dir  : %s", OUTPUT_DIR)
    logger.info("listen      : %s:%d", HOST, PORT)
    logger.info("local URL   : http://localhost:%d/", PORT)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info", access_log=True)


if __name__ == "__main__":
    main()
