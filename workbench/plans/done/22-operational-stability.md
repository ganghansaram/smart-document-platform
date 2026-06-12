# Plan 22: 운영 안정성 강화

## Context

운영 전문가 관점에서 플랫폼을 상세 검토한 결과, 코드 품질·보안·폐쇄망 호환성은 양호하나
**데이터 안전성**(JSON 원자 쓰기 부재), **프로세스 복원력**(shutdown 핸들러 부재),
**운영 가시성**(로깅/모니터링 부재) 3가지 영역에서 보완이 필요.

기존 `docs/10-PRODUCTION-READINESS.md`(Plan-11)에서 동일 갭을 식별한 바 있으나 미착수 상태.
이 계획서는 해당 갭을 **업계 표준 수준으로 해소**하는 것을 목표로 한다.

### 업계 표준 참조

| 영역 | 업계 표준 | 현재 상태 | 목표 |
|------|----------|----------|------|
| 파일 쓰기 | 원자적 쓰기 (tmp→rename) | settings_service.py만 적용 | 전체 JSON I/O 적용 |
| 프로세스 관리 | Supervisor/systemd/NSSM | 수동 실행 | NSSM 서비스 + 자동 재시작 |
| Graceful Shutdown | SIGTERM 핸들러 | 없음 | 태스크 취소 + 프로세스 정리 |
| 로깅 | 구조화 로깅 + 로테이션 | 산발적 logger 사용, 핸들러 없음 | RotatingFileHandler + 일관 포맷 |
| 헬스체크 | 의존성 포함 (DB/LLM/디스크) | `{"status":"ok"}` 고정 | 실제 상태 확인 |
| 백업 | 일일 자동 백업 + 보존 정책 | 없음 | 스크립트 + 30일 보존 |
| 상태 복구 | 서버 재시작 시 고착 태스크 해소 | translating 상태 영구 고착 | 시작 시 자동 리셋 |

### 제약 조건

- Vanilla Python (외부 패키지 추가 최소화 — logging, pathlib, shutil 등 표준 라이브러리 활용)
- 폐쇄망 환경 (Redis 등 인프라 추가 불가)
- 기존 기능 영향 0건

---

## Phase 1: JSON 원자 쓰기 (데이터 안전성)

> 기존 패턴: `settings_service.py:183-187`의 `tmp → replace` 패턴 재사용

### 1-1. 공통 유틸 함수 작성

**파일**: `backend/services/translator_service.py` 상단에 헬퍼 추가

```python
def _atomic_write_json(path: Path, data: dict):
    """원자적 JSON 저장 (tmp → rename). 크래시 시 원본 보존."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
```

### 1-2. 적용 대상 (6곳)

| 함수 | 라인 | 현재 패턴 | 변경 |
|------|------|----------|------|
| `_save_meta()` | ~208 | `json.dump(meta, f)` | → `_atomic_write_json(path, meta)` |
| `_save_user_index()` | ~190 | `json.dump(index, f)` | → `_atomic_write_json(path, index)` |
| `_save_search_index()` | ~231 | `json.dump(index, f)` | → `_atomic_write_json(path, index)` |
| `_save_user_folders()` | ~453 | `json.dump(folders, f)` | → `_atomic_write_json(path, folders)` |
| `_save_annotations()` | ~570 | `json.dump(data, f)` | → `_atomic_write_json(path, data)` |
| `save_glossary()` | ~93 | `write_text(json.dumps(...))` | → `_atomic_write_json(path, data)` |

### 1-3. JSON 로드 시 파손 복구

`_load_meta()` 등에서 `json.JSONDecodeError` 발생 시:
- `.tmp` 파일이 존재하면 복구 시도 (완전한 JSON일 가능성)
- 복구 실패 시 `None` 반환 + 로그 경고

---

## Phase 2: Graceful Shutdown (프로세스 복원력)

> FastAPI lifespan 패턴 적용 (현재 `@app.on_event("startup")` → 최신 `lifespan` 컨텍스트 매니저)

### 2-1. main.py에 lifespan 핸들러 추가

**파일**: `backend/main.py`

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # ── startup ──
    init_db()
    init_analytics_db()
    apply_settings_on_startup()
    yield
    # ── shutdown ──
    await _graceful_shutdown()

app = FastAPI(lifespan=lifespan)
```

### 2-2. _graceful_shutdown() 구현

**파일**: `backend/main.py` 또는 `translator_service.py`에 추가

```python
async def _graceful_shutdown():
    """서버 종료 시 진행 중 태스크 정리."""
    # 1. 번역 태스크 취소
    for key, task in list(_active_tasks.items()):
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    _active_tasks.clear()

    # 2. 서브프로세스 종료
    for key, proc in list(_active_procs.items()):
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5)
        except:
            proc.kill()
    _active_procs.clear()

    # 3. 웹뷰/요약 태스크도 동일 처리
    for tasks_dict in [_web_active_tasks, _summary_active_tasks]:
        for key, task in list(tasks_dict.items()):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        tasks_dict.clear()
```

### 2-3. 서버 시작 시 고착 태스크 리셋

**파일**: `backend/services/translator_service.py`

서버 시작 시 호출되는 함수 추가:
- `data/translator/*/*/meta.json` 스캔
- `page_status`가 `"translating"`인 항목 → `"pending"` 리셋
- `summary_status`가 `"generating"`인 항목 → `"pending"` 리셋
- 로그: "고착 태스크 N건 리셋"

---

## Phase 3: 로깅 체계 구축 (운영 가시성)

> 업계 표준: Python `logging` + `RotatingFileHandler` + 구조화 포맷

### 3-1. 로깅 설정 모듈

**파일**: `backend/logging_config.py` (신규)

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: str = "logs", level: str = "INFO"):
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 파일 핸들러 (10MB × 5 로테이션)
    file_handler = RotatingFileHandler(
        log_path / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(file_handler)
    root.addHandler(console_handler)
```

### 3-2. main.py에서 호출

```python
from logging_config import setup_logging
# lifespan startup 내에서:
setup_logging()
```

### 3-3. 핵심 이벤트 로깅 추가

| 파일 | 이벤트 | 레벨 |
|------|--------|------|
| `translator_service.py` | 번역 시작/완료/실패/취소 | INFO/ERROR |
| `translator_service.py` | JSON 쓰기/읽기 실패 | WARNING |
| `ai_summary.py` | 요약 생성 시작/완료 (소요시간) | INFO |
| `notebook_chat.py` | Q&A 질문 수신 (문서 ID) | INFO |
| `main.py` | 서버 시작/종료 | INFO |
| `auth.py` | 로그인 성공/실패 (username) | INFO/WARNING |

기존 `logger = logging.getLogger(__name__)` 패턴이 18개 파일에 이미 존재하므로,
핸들러 설정만 추가하면 기존 로그 호출이 자동 활성화됨.

---

## Phase 4: 헬스체크 확장

> 업계 표준: 의존성 포함 헬스체크 (Kubernetes readiness probe 패턴)

### 4-1. /api/health 확장

**파일**: `backend/main.py`

```python
@app.get("/api/health")
async def health_check():
    checks = {}

    # DB 확인
    try:
        conn = sqlite3.connect(config.AUTH_DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        checks["database"] = "ok"
    except:
        checks["database"] = "error"

    # Ollama 확인
    try:
        resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=3)
        checks["ollama"] = "ok" if resp.status_code == 200 else "unreachable"
    except:
        checks["ollama"] = "unreachable"

    # 디스크 확인
    try:
        usage = shutil.disk_usage(config.TRANSLATOR_DATA_DIR)
        free_gb = usage.free / (1024**3)
        checks["disk_free_gb"] = round(free_gb, 1)
        checks["disk"] = "ok" if free_gb > 1.0 else "low"
    except:
        checks["disk"] = "unknown"

    overall = "ok" if all(v == "ok" for k, v in checks.items() if k != "disk_free_gb") else "degraded"
    return {"status": overall, "checks": checks}
```

---

## Phase 5: 백업 스크립트

> 업계 표준: 일일 자동 백업 + N일 보존 + 무결성 검증

### 5-1. 백업 스크립트 작성

**파일**: `tools/daily-backup.py` (신규)

```python
"""일일 백업 — Windows Task Scheduler 또는 cron으로 실행"""
# 1. SQLite .backup 명령으로 auth.db, analytics.db 백업
# 2. data/settings.json 복사
# 3. data/translator/ 전체를 날짜별 디렉토리에 복사 (또는 증분)
# 4. 30일 초과 백업 삭제
# 5. 백업 결과 로그 기록
```

### 5-2. 백업 디렉토리 구조

```
backups/
├── 2026-03-31/
│   ├── auth.db
│   ├── analytics.db
│   ├── settings.json
│   └── translator/       ← data/translator/ 미러
├── 2026-03-30/
└── ...
```

### 5-3. .gitignore에 backups/ 추가

---

## Phase 6: CORS 런타임 설정 + 환경변수 지원

### 6-1. config.py에 환경변수 폴백

```python
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080"
).split(",")
```

### 6-2. settings.json 반영 시 재시작 안내

현재 `settings_service.py`에서 CORS는 `restart_needed` 목록에 포함됨 — 변경 사항 없음.
환경변수 지원만 추가하여 배포 시 코드 수정 없이 설정 가능하게 함.

---

## 실행 순서 및 예상 공수

| Phase | 내용 | 예상 | 수정 파일 |
|:-----:|------|:----:|----------|
| 1 | JSON 원자 쓰기 | ~0.5일 | `translator_service.py` |
| 2 | Graceful Shutdown + 고착 리셋 | ~0.5일 | `main.py`, `translator_service.py` |
| 3 | 로깅 체계 | ~0.5일 | `logging_config.py`(신규), `main.py` |
| 4 | 헬스체크 확장 | ~0.25일 | `main.py` |
| 5 | 백업 스크립트 | ~0.5일 | `tools/daily-backup.py`(신규), `.gitignore` |
| 6 | CORS 환경변수 | ~0.25일 | `config.py` |
| **합계** | | **~2.5일** | |

## 범위 외 (현 단계에서 불필요)

| 항목 | 사유 |
|------|------|
| HTTPS/SSL | 폐쇄망 내부 운영, 물리 보안 확보 |
| Redis 세션 | 10~30명 규모, 인메모리 LRU 충분 |
| Rate Limiting | 내부 사용자만 접근 |
| DB 마이그레이션 프레임워크 | 스키마 변경 빈도 낮음 |
| 디스크 쿼터/자동 정리 | 초기 운영 후 데이터 증가 추이 관찰 후 판단 |
| N+1 파일 읽기 최적화 | 문서 50개 미만 환경에서 체감 영향 없음 |
| NSSM 서비스 등록 | 인프라 설정이므로 문서 안내로 대체 (코드 작업 아님) |

## 검증

- Phase 1: 서버 기동 → 문서 업로드 → 번역 실행 → 서버 강제 종료 → meta.json 파손 없음 확인
- Phase 2: 번역 진행 중 서버 종료 → 재시작 → 고착 없이 pending 상태 확인
- Phase 3: `logs/app.log` 파일 생성, 번역 이벤트 기록 확인
- Phase 4: `/api/health` 응답에 database/ollama/disk 상태 포함 확인
- Phase 5: `python tools/daily-backup.py` 실행 → backups/ 디렉토리 생성 확인
- Phase 6: `CORS_ORIGINS=http://192.168.1.100:8080 python main.py` → CORS 헤더 확인
