# 플랫폼 운영 준비도 분석 보고서

> **문서 번호**: Plan-11
> **작성일**: 2026-03-10
> **목적**: 현재 플랫폼의 실제 운영 가능 여부를 전문가 관점에서 평가하고, 보완 항목과 필요 인프라를 제시

---

## 1. 실제 운영 환경

```
┌─────────────────────────────────────────────────────────────────┐
│                        사내 폐쇄망                               │
│                                                                 │
│  ┌─ 플랫폼 서버 (Windows VM) ──────────┐   ┌─ GPU 서버 (Linux) ┐│
│  │ CPU: 12코어 (VM, 확장 가능)          │   │ NVIDIA L40-48Q    ││
│  │ RAM: (확장 가능)                     │   │ Ollama :11434     ││
│  │ OS: Windows                         │   │ gemma3:27b        ││
│  │                                     │   │ bge-m3 (임베딩)   ││
│  │ Tomcat :8080 ← 프론트엔드 (정적파일) │   │                   ││
│  │ uvicorn :8000 ← 백엔드 (FastAPI)    │   └───────▲───────────┘│
│  │ SQLite, FAISS, 리랭커               │           │            │
│  │                                     │───────────┘            │
│  └─────────────────────────────────────┘  사내망 통신            │
│                                           (Ollama API 호출)     │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 특징**:
- 프론트엔드 + 백엔드: **동일 Windows VM** (Tomcat + uvicorn)
- GPU 서버: **별도 Linux 서버** (Ollama + LLM/임베딩 모델)
- 리랭커(bge-reranker): **Windows VM의 CPU**에서 실행 (GPU 서버와 무관)
- 네트워크: 폐쇄망, 두 서버 간 사내망 통신

---

## 2. 총평

### 결론부터 말하면

> **현재 수준: 소규모 팀 내부 운용은 가능, 부서/조직 단위 정식 운영에는 보완 필요**

잘 되어 있는 것:
- 인증/인가 구조 (PBKDF2 해싱, RBAC 3단계, HttpOnly 쿠키)
- SQL 인젝션 방어 (파라미터화 쿼리 전수 적용)
- 경로 탐색 방어 (Path traversal 검증)
- 파일 업로드 검증 (확장자, 크기 제한)
- 검색 파이프라인 품질 (하이브리드 검색 + 리랭킹)
- 에러 폴백 체인 (벡터→키워드, 리랭커→원본순위)

보완이 필요한 것:
- 백엔드 프로세스 관리 (크래시 시 수동 재시작)
- 로깅/모니터링
- DB 백업 체계
- 보안 세부 설정

---

## 3. 영역별 상세 분석

### 3.1 서버 아키텍처

| 항목 | 현재 상태 | 평가 | 비고 |
|------|-----------|:---:|------|
| 프론트엔드 서버 | Tomcat :8080 | ✅ | 프로덕션급 서블릿 컨테이너 |
| 백엔드 서버 | `uvicorn` 단일 프로세스 | ⚠️ | 워커 1개, 프로세스 관리 없음 |
| 리버스 프록시 | 없음 (Tomcat 직접 노출) | ⚠️ | 필수는 아님, 있으면 좋음 |
| HTTPS | 미적용 (`secure=False`) | ⚠️ | 폐쇄망이므로 위험 낮음 |
| 프로세스 관리 (백엔드) | 없음 | ❌ | 크래시 시 수동 재시작 필요 |
| CORS | localhost만 허용 | ⚠️ | 운영 호스트명/IP 등록 필요 |
| Ollama 연결 | `config.py` → GPU 서버 IP | ✅ | 이미 분리 운영 중 |

**Tomcat에 대한 평가**:

Tomcat은 정적 파일 서빙에 과한 측면이 있지만 (본래 Java 서블릿 컨테이너), 이미 설치·운영 중이고 다음을 제공:
- gzip 압축 (server.xml에서 `compression="on"`)
- 접속 로그 (`AccessLogValve`)
- 안정적인 다중 접속 처리
- Windows 서비스 등록 가능 (자동 시작)

> **판정: Tomcat 유지가 현실적.** nginx로 교체할 필요 없음.

**백엔드(FastAPI) 프로세스 관리가 유일한 갭**:

Windows에서는 Linux의 systemd/gunicorn이 없으므로, 대안:

| 방법 | 설명 | 난이도 |
|------|------|:---:|
| **NSSM** (추천) | Non-Sucking Service Manager — 모든 exe를 Windows 서비스로 등록 | 쉬움 |
| **Task Scheduler** | Windows 작업 스케줄러로 시작 시 실행 + 실패 시 재시작 | 쉬움 |
| **bat + 감시 스크립트** | 루프에서 uvicorn 실행, 종료 시 재시작 | 가장 간단 |

```bat
:: 방법 1: NSSM으로 Windows 서비스 등록
nssm install SmartDocAPI "C:\Python310\python.exe" "-m" "uvicorn" "main:app" "--host" "0.0.0.0" "--port" "8000"
nssm set SmartDocAPI AppDirectory "C:\AHS_Proj\smart-document-platform\backend"
nssm set SmartDocAPI AppRestartDelay 5000
nssm start SmartDocAPI
```

```bat
:: 방법 2: 간단한 감시 스크립트 (run-backend.bat)
@echo off
:loop
echo [%date% %time%] Starting backend server...
cd /d C:\AHS_Proj\smart-document-platform\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
echo [%date% %time%] Server stopped. Restarting in 5 seconds...
timeout /t 5
goto loop
```

---

### 3.2 데이터베이스

| 항목 | 현재 상태 | 평가 | 비고 |
|------|-----------|:---:|------|
| DBMS | SQLite (WAL 모드) | ✅ | 소규모에 적합, 충분 |
| 연결 관리 | 매 쿼리마다 새 연결 | ⚠️ | SQLite에서는 허용 범위 |
| SQL 인젝션 방어 | 파라미터화 쿼리 (`?`) | ✅ | 전수 적용 |
| 마이그레이션 | `executescript`로 초기화 | ⚠️ | 스키마 변경 시 수동 대응 |
| 백업 | 없음 | ❌ | DB 파일 손상 시 복구 불가 |
| 암호화 | 없음 (평문 파일) | — | 폐쇄망에서는 수용 가능 |

**현재 DB 구조**:

```
data/
├── auth.db          ← 사용자/세션 (SQLite, ~100KB)
├── analytics.db     ← 이벤트 로그 (SQLite, 성장)
├── settings.json    ← 런타임 설정 (JSON 파일)
├── search-index.json← 검색 인덱스 (JSON, ~수 MB)
├── vector-index/    ← FAISS 벡터 인덱스
├── menu.json        ← 메뉴 구조
└── translator/      ← 개인별 번역 문서
    └── {username}/
        └── {doc_id}/
```

**SQLite 적합성 판단**:

| 기준 | 우리 환경 | 판정 |
|------|----------|:---:|
| 동시 사용자 | 10-30명 (팀 단위) | ✅ SQLite 충분 |
| 쓰기 빈도 | 낮음 (로그인, 설정 변경 정도) | ✅ SQLite 충분 |
| 읽기 빈도 | 중간 (검색, 문서 조회) | ✅ SQLite 충분 |
| 데이터 크기 | 수십 MB 이하 | ✅ SQLite 충분 |
| 트랜잭션 복잡도 | 단순 CRUD | ✅ SQLite 충분 |

> **판정: SQLite 유지가 적절**. PostgreSQL/MySQL로 교체할 이유 없음. 다만 **백업 체계는 필수**.

**보완 방법 — Windows 일일 백업**:

```bat
:: daily-backup.bat (Windows 작업 스케줄러: 매일 02:00)
@echo off
set BACKUP_DIR=C:\AHS_Proj\backups
set DATE=%date:~0,4%%date:~5,2%%date:~8,2%
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: SQLite 안전 백업 (.backup 명령은 WAL 모드에서도 안전)
sqlite3 "C:\AHS_Proj\smart-document-platform\data\auth.db" ".backup '%BACKUP_DIR%\auth_%DATE%.db'"
sqlite3 "C:\AHS_Proj\smart-document-platform\data\analytics.db" ".backup '%BACKUP_DIR%\analytics_%DATE%.db'"

:: JSON 설정 백업
copy "C:\AHS_Proj\smart-document-platform\data\settings.json" "%BACKUP_DIR%\settings_%DATE%.json"
copy "C:\AHS_Proj\smart-document-platform\data\menu.json" "%BACKUP_DIR%\menu_%DATE%.json"

:: 30일 이전 백업 삭제
forfiles /p "%BACKUP_DIR%" /d -30 /c "cmd /c del @file" 2>nul

echo [%date% %time%] Backup completed.
```

---

### 3.3 인증/보안

| 항목 | 현재 상태 | 평가 | 비고 |
|------|-----------|:---:|------|
| 비밀번호 해싱 | PBKDF2-SHA256, 260K iterations | ✅ | 업계 권장 수준 |
| 세션 토큰 | `secrets.token_hex(32)` (256bit) | ✅ | 충분한 엔트로피 |
| 타이밍 공격 방어 | `secrets.compare_digest()` | ✅ | 적용됨 |
| HttpOnly 쿠키 | 적용 | ✅ | JS에서 세션 접근 불가 |
| SameSite | `lax` | ✅ | CSRF 기본 방어 |
| Secure 플래그 | `False` | — | 폐쇄망 HTTP 환경이므로 현재는 정상 |
| 로그인 Rate Limit | 없음 | ⚠️ | 브루트포스 가능 (폐쇄망이라 위험 낮음) |
| 보안 헤더 (CSP 등) | 없음 | ⚠️ | Tomcat에서 설정 가능 |
| RBAC | 3단계 (viewer/editor/admin) | ✅ | 역할별 엔드포인트 제한 |
| 감사 로깅 | 없음 | ⚠️ | 관리자 작업 추적 불가 |

**폐쇄망 환경 보안 재평가**:

일반적인 웹 서비스와 달리, 폐쇄망에서는 외부 공격 벡터가 차단되어 있으므로:
- HTTPS: **nice-to-have** (필수 아님, 인증서 관리 부담도 있음)
- Rate Limit: **낮은 우선순위** (내부 사용자만 접근)
- CSP/보안 헤더: **낮은 우선순위** (XSS 공격자 = 내부 사용자뿐)

> **폐쇄망에서 진짜 중요한 것**: 인증 체계(✅ 완료), RBAC(✅ 완료), 데이터 백업(❌ 보완 필요)

---

### 3.4 로깅/모니터링

| 항목 | 현재 상태 | 평가 | 비고 |
|------|-----------|:---:|------|
| 애플리케이션 로그 | `logging.getLogger(__name__)` | ⚠️ | 있으나 설정 미흡 |
| 로그 레벨 설정 | 없음 (기본값) | ⚠️ | 디버그/프로덕션 구분 불가 |
| 로그 파일 출력 | 없음 (콘솔만) | ❌ | 서버 재시작 시 소실 |
| 로그 로테이션 | 없음 | ❌ | 파일 출력이 없으니 해당 없음 |
| 요청/응답 로깅 | 없음 | ⚠️ | API 호출 추적 불가 |
| Tomcat 접속 로그 | 있음 (AccessLogValve) | ✅ | 프론트엔드 접속은 추적 가능 |
| 헬스 체크 | `GET /api/health` 존재 | ✅ | 모니터링 연계 가능 |

**보완 방법**:

```python
# backend/main.py에 추가
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        RotatingFileHandler(
            "logs/app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)
```

---

### 3.5 파일 저장 및 보호

| 항목 | 현재 상태 | 평가 | 비고 |
|------|-----------|:---:|------|
| 경로 탐색 방어 | `resolve()` + `startswith()` | ✅ | 적용됨 |
| 업로드 확장자 검증 | `.docx`, `.pdf`만 허용 | ✅ | 화이트리스트 |
| 업로드 크기 제한 | 500MB (설정 가능) | ✅ | 적절 |
| 임시 파일 정리 | `finally` 블록에서 삭제 | ✅ | 누수 방지 |
| 문서 백업 | 업로드/저장 시 `.bak` 생성 | ✅ | 있음 |
| 백업 보존 정책 | 없음 (무한 누적) | ⚠️ | 디스크 관리 필요 |

---

### 3.6 프론트엔드

| 항목 | 현재 상태 | 평가 | 비고 |
|------|-----------|:---:|------|
| JS 프레임워크 | Vanilla JS (의도적) | ✅ | 폐쇄망 제약, 의존성 제로 |
| 정적 파일 서빙 | Tomcat | ✅ | 프로덕션급 |
| 에셋 압축 | Tomcat gzip 설정 여부 미확인 | ⚠️ | server.xml에서 활성화 가능 |
| XSS 방어 | `_escHtml()` 부분 적용 | ⚠️ | innerHTML 다수 사용 |
| 에러 처리 | try-catch + 조용한 실패 | ⚠️ | 사용자 피드백 부족 |
| 401 처리 | `handleApiUnauthorized()` | ✅ | 세션 만료 시 로그인 리다이렉트 |

**innerHTML 관련**:

innerHTML 사용이 많지만, 입력 소스가 대부분 **서버 응답(신뢰 데이터)** 이거나 **정적 HTML 템플릿**이므로 실질적 XSS 위험은 낮다. 폐쇄망 환경에서는 더욱 그렇다.

---

### 3.7 에러 처리 및 복원력

| 항목 | 현재 상태 | 평가 | 비고 |
|------|-----------|:---:|------|
| API 에러 응답 | HTTPException + 상태 코드 | ✅ | 구조화됨 |
| 검색 폴백 체인 | 벡터 실패→키워드, 리랭커 실패→원본 | ✅ | 잘 설계됨 |
| 쿼리 재작성 폴백 | LLM 실패→키워드 결합 | ✅ | 안전 |
| 번역 중 취소 | `proc.kill()` + 상태 복원 | ✅ | 처리됨 |
| 에러 메시지 노출 | `str(e)` 직접 반환 | ⚠️ | 내부 경로 등 노출 가능 |
| 글로벌 에러 핸들러 | 없음 | ⚠️ | 미처리 예외 시 스택트레이스 |
| GPU 서버 연결 실패 | Ollama 타임아웃 → 에러 반환 | ✅ | 챗봇 실패 시 검색만 동작 |
| 번역 태스크 유실 | 서버 재시작 시 소실 | ⚠️ | 인메모리 태스크 관리 |

---

## 4. 종합 평가 매트릭스

| 영역 | 점수 | 운영 가능? | 보완 공수 |
|------|:---:|:---:|:---:|
| **인증/인가** | 8/10 | ✅ | Rate Limit 추가 시 (0.5일) |
| **데이터 보호** | 6/10 | ⚠️ | 백업 스크립트 (0.5일) |
| **API 보안** | 7/10 | ✅ | 에러 메시지 정리 (0.5일) |
| **서버 구성** | 5/10 | ⚠️ | 백엔드 서비스화 (0.5일) |
| **로깅/모니터링** | 3/10 | ❌ | 로깅 설정 + 파일 출력 (1일) |
| **에러 처리** | 7/10 | ✅ | 폴백 체인 잘 구성됨 |
| **프론트엔드** | 8/10 | ✅ | Tomcat이 이미 프로덕션급 |
| **DB 구조** | 7/10 | ✅ | SQLite 유지, 백업만 추가 |

---

## 5. 운영 전 보완 항목 (우선순위순)

### Priority 1: 백엔드 서비스화 + 자동 재시작

| # | 항목 | 현재 | 변경 | 공수 |
|:-:|------|------|------|:---:|
| 1 | 백엔드 프로세스 관리 | 수동 실행 | NSSM으로 Windows 서비스 등록 | 0.5일 |
| 2 | CORS 설정 | localhost | 운영 호스트명/IP 추가 | 설정 1줄 |

```bat
:: NSSM으로 백엔드를 Windows 서비스로 등록
nssm install SmartDocAPI "C:\Python310\python.exe" "-m" "uvicorn" "main:app" "--host" "0.0.0.0" "--port" "8000"
nssm set SmartDocAPI AppDirectory "C:\AHS_Proj\smart-document-platform\backend"
nssm set SmartDocAPI AppStdout "C:\AHS_Proj\smart-document-platform\logs\backend-stdout.log"
nssm set SmartDocAPI AppStderr "C:\AHS_Proj\smart-document-platform\logs\backend-stderr.log"
nssm set SmartDocAPI AppRestartDelay 5000
nssm set SmartDocAPI AppRotateFiles 1
nssm set SmartDocAPI AppRotateBytes 10485760
nssm start SmartDocAPI
```

> NSSM을 사용하면 서버 재부팅 시 자동 시작, 크래시 시 5초 후 자동 재시작, 로그 파일 자동 로테이션까지 한번에 해결.

### Priority 2: 로깅

| # | 항목 | 변경 | 공수 |
|:-:|------|------|:---:|
| 3 | 로깅 설정 | `RotatingFileHandler` 추가, INFO 레벨 | 0.5일 |
| 4 | 요청 로깅 | FastAPI 미들웨어로 API 호출 기록 | 0.5일 |
| 5 | 에러 메시지 | `str(e)` → 사용자용 메시지 (내부 정보 숨김) | 0.5일 |

### Priority 3: 데이터 백업

| # | 항목 | 변경 | 공수 |
|:-:|------|------|:---:|
| 6 | DB 백업 | Windows 작업 스케줄러 + bat 스크립트 | 0.5일 |
| 7 | 백업 파일 정리 | 30일 보존 정책 | 스크립트에 포함 |

### Priority 4: 선택적 보안 강화 (폐쇄망이므로 낮은 우선순위)

| # | 항목 | 변경 | 공수 |
|:-:|------|------|:---:|
| 8 | 로그인 Rate Limit | IP당 5회/분 제한 미들웨어 | 0.5일 |
| 9 | Tomcat gzip | server.xml에서 compression 활성화 | 설정 변경 |
| 10 | 보안 헤더 | Tomcat Filter 또는 web.xml | 설정 변경 |

### 총 보완 공수: 약 3-4일

> 이전 분석(5-6일)보다 줄어든 이유: Tomcat이 이미 프론트엔드를 프로덕션급으로 서빙 중이므로, nginx 도입이 불필요. 보완 범위가 **백엔드 서비스화 + 로깅 + 백업**으로 축소됨.

---

## 6. 장비 사양 권장

### 6.1 플랫폼 서버 (Windows VM) — 이미 보유

| 항목 | 현재 | 권장 최소 | 권장 | 비고 |
|------|:---:|:---:|:---:|------|
| **CPU** | 12코어 | 4코어 | 8코어 | ✅ 현재 충분 (여유 있음) |
| **RAM** | 미확인 | 8GB | 16GB | 리랭커(bge-reranker) CPU 추론에 ~2GB 사용 |
| **스토리지** | 미확인 | 50GB SSD | 100GB SSD | 콘텐츠 + 번역 데이터 + 백업 |

**RAM 산정 (상세)**:

```
Windows OS + Tomcat:          ~3GB
Python + FastAPI (uvicorn):   ~500MB
bge-reranker-v2-m3 (CPU):    ~2GB (모델 로드 시)
FAISS 인덱스 (260 섹션):     ~100MB
search-index.json 메모리:    ~50MB
Translator 동시 번역 4건:    ~1GB (PDF 처리)
여유:                         ~2GB
──────────────────────────────────
합계:                         ~9GB
```

> **권장: 16GB RAM**. 12코어 CPU는 충분하고도 남음.

**디스크 산정**:

| 항목 | 예상 크기 |
|------|----------|
| 플랫폼 코드 + 정적 자산 | ~50MB |
| 콘텐츠 (HTML 문서) | ~100MB |
| 검색 인덱스 (JSON + FAISS) | ~50MB |
| 리랭커 모델 (bge-reranker-v2-m3) | ~1GB |
| Translator 사용자 데이터 | ~10GB (성장) |
| 로그 파일 | ~500MB (로테이션) |
| 백업 (30일) | ~2GB |
| Tomcat + Python 런타임 | ~2GB |
| **합계** | **~16GB (현재), ~30GB (1년 운용 예상)** |

> **권장: 100GB SSD** (여유 충분)

### 6.2 GPU 서버 (Linux) — 이미 보유

| 항목 | 현재 | 용도 | 비고 |
|------|:---:|------|------|
| **GPU** | L40-48Q (48GB) | Ollama LLM + 임베딩 | ✅ 충분 |
| **Ollama 모델** | gemma3:27b | 챗봇 + 번역 | Q8_0 ~28GB, 여유 20GB |
| **bge-m3** | 임베딩 | 벡터 검색 | ~2GB |

**VRAM 산정**:

```
gemma3:27b Q8_0:              ~28GB
bge-m3 임베딩:                ~2GB
KV 캐시 (8K 컨텍스트):       ~4GB
──────────────────────────────────
합계:                         ~34GB / 48GB (여유 14GB)
```

> 현재 구성으로 **충분**. 번역(PMT)도 동일 GPU에서 실행 가능하나, 챗봇과 번역을 동시에 활용하는 사용자가 많아지면 GPU 1장 추가 고려.

### 6.3 동시 접속 용량 예상

| 시나리오 | 예상 동시 접속 | 병목 | 비고 |
|----------|:-:|------|------|
| 문서 탐색만 (챗봇 미사용) | ~100명 | Tomcat/디스크 I/O | 정적 파일이므로 부하 매우 낮음 |
| 검색 사용 | ~50명 | FAISS + 리랭커 CPU | 리랭커가 CPU 바운드 |
| AI 챗봇 사용 | ~5-10명 동시 | GPU LLM 추론 | 27b 모델 15-20 tok/s, 순차 처리 |
| 번역 사용 | ~4명 동시 | GPU + 동시성 제한 | `TRANSLATOR_MAX_CONCURRENT=4` |

> **핵심 병목: GPU 서버의 LLM 추론 처리량**. 문서 탐색/검색은 충분, AI 챗봇은 순차 처리라 동시 다수 사용 시 대기 발생.

---

## 7. 운영 권장 아키텍처 (실제 환경 반영)

```
                          ┌───────────────────┐
                          │    사용자 브라우저   │
                          └─────────┬─────────┘
                                    │ HTTP (사내망)
          ┌─────────────────────────▼─────────────────────────┐
          │             플랫폼 서버 (Windows VM)                │
          │             CPU 12코어 / RAM 16GB                  │
          │                                                    │
          │  ┌────────────────┐    ┌────────────────────────┐  │
          │  │  Tomcat :8080  │    │  uvicorn :8000         │  │
          │  │  (프론트엔드)   │    │  (FastAPI 백엔드)       │  │
          │  │                │    │                        │  │
          │  │ HTML/CSS/JS    │    │ /api/search  검색      │  │
          │  │ 정적 파일 서빙  │    │ /api/chat    챗봇  ────┼──┼──→ GPU 서버
          │  │ 접속 로그       │    │ /api/auth    인증      │  │   Ollama API
          │  │ gzip 압축      │    │ /api/translator 번역 ──┼──┼──→ (:11434)
          │  └────────────────┘    │ /api/upload  업로드    │  │
          │                        │ /api/settings 설정     │  │
          │                        │                        │  │
          │                        │ bge-reranker (CPU)     │  │
          │                        │ FAISS (CPU)            │  │
          │                        └────────────────────────┘  │
          │                                                    │
          │  ┌──────────────────────────────────────────────┐  │
          │  │ data/                                        │  │
          │  │ ├── auth.db, analytics.db  (SQLite)          │  │
          │  │ ├── settings.json, menu.json                 │  │
          │  │ ├── search-index.json, vector-index/         │  │
          │  │ └── translator/{user}/{doc}/                  │  │
          │  └──────────────────────────────────────────────┘  │
          │                                                    │
          │  Windows 작업 스케줄러: 매일 02:00 DB 백업          │
          │  NSSM: 백엔드 자동 재시작                           │
          └────────────────────────────────────────────────────┘

          ┌────────────────────────────────────────────────────┐
          │             GPU 서버 (Linux)                        │
          │             NVIDIA L40-48Q (48GB VRAM)              │
          │                                                    │
          │  ┌────────────────────────────────────────────┐    │
          │  │ Ollama :11434                              │    │
          │  │ ├── gemma3:27b  → LLM 추론 (챗봇/번역)    │    │
          │  │ └── bge-m3      → 벡터 임베딩              │    │
          │  └────────────────────────────────────────────┘    │
          │                                                    │
          │  systemd: ollama.service 자동 시작                  │
          └────────────────────────────────────────────────────┘
```

---

## 8. 결론

### 잘 만들어진 부분 (건드릴 필요 없음)

- **인증 체계**: PBKDF2 + RBAC + HttpOnly 쿠키 — 업계 표준 수준
- **검색 파이프라인**: 하이브리드 검색 + 리랭킹 + 폴백 체인 — 상용 RAG 수준
- **API 구조**: FastAPI + Pydantic 모델 — 타입 안전, 자동 문서화
- **파일 보호**: 경로 탐색 방어 + 확장자 검증 + 크기 제한
- **DB 선택**: SQLite는 이 규모에 최적 (과도한 RDBMS 불필요)
- **프론트엔드 서빙**: Tomcat이 이미 프로덕션급 처리

### 운영을 위해 보완할 것 (3-4일 공수)

| 순서 | 항목 | 공수 | 효과 |
|:---:|------|:---:|------|
| 1 | **NSSM 백엔드 서비스화** | 0.5일 | 크래시 자동 복구, 서버 재부팅 시 자동 시작 |
| 2 | **로깅 설정** | 1일 | 파일 출력 + 로테이션 + 요청 로깅 |
| 3 | **DB 백업 스크립트** | 0.5일 | 일일 자동 백업, 30일 보존 |
| 4 | **CORS 운영 도메인** | 0.5일 | 운영 호스트명 등록 |
| 5 | **에러 메시지 정리** | 1일 | 내부 정보 노출 방지 |

### 장비 사양 판정

| 서버 | 현재 사양 | 판정 |
|------|----------|:---:|
| 플랫폼 (Windows VM) | 12코어, RAM 미확인 | ✅ CPU 충분, **RAM 16GB 확인/확보 필요** |
| GPU (Linux) | L40-48Q 48GB | ✅ 충분 (여유 14GB) |

### 한 문장 요약

> **코드 품질과 기능은 운영 가능 수준. 장비도 충분. "백엔드 서비스화(NSSM) + 로깅 + DB 백업" 3가지만 보완하면 3-4일 안에 정식 운영 가능.**
