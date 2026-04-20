# Upload Standalone Test (Plan-35 격리 테스트)

플랫폼의 복잡한 레이어(Nginx 프록시, CORS, 쿠키 인증, NDJSON 스트리밍, RAG 재인덱싱)를 모두 배제한
최소 구현으로 **원격 DOCX 업로드가 되는지** 판정한다.

- 성공 → 플랫폼 코드/설정에 원인이 있음 → Explorer 업로드 코드와 diff
- 실패 → 방화벽·네트워크·변환기 경로 문제

## 구성

| 파일 | 용도 |
|------|------|
| `server.py` | FastAPI 단일 파일 서버 (GET `/`, `/health`, POST `/upload`, GET `/output`) |
| `index.html` | 업로드 UI — JS XHR + HTML form 2가지 방식 제공 |
| `start.bat` | Windows 실행 배치 |
| `server.log` | 런타임 로그 (gitignore) |
| `uploads/`, `output/` | 런타임 디렉토리 (gitignore) |

## 전제

- **Python 설치** (서비스 PC에 이미 있음)
- **Python 패키지**: `fastapi`, `uvicorn`, `python-multipart`
  - 미설치 시: `pip install fastapi uvicorn python-multipart`
- **DOCX 변환기** — 다음 중 하나:
  - `../tools/docx2html-standalone/dist/docx2html.exe` (빌드된 exe)
  - `../tools/docx2html-standalone/docx2html.py` (Python 스크립트) + `python-docx`, `pywin32`
  - 또는 환경변수 `DOCX2HTML_EXE`로 임의 경로 지정
- **포트 8080이 비어 있음** — 서비스 PC에서 기존 플랫폼 프론트 중지
- **방화벽 8080 인바운드 허용** (회사 정책 기반)

`/health` 엔드포인트에서 변환기 탐색 결과를 확인할 수 있다.

## 실행

```bat
cd test-upload-standalone
start.bat
```

또는:
```bat
python server.py
```

포트 변경 시: `set PORT=8000 && python server.py`

## 접속

| 위치 | URL |
|------|-----|
| 같은 PC | http://localhost:8080/ |
| 원격 PC | http://<서비스PC-IP>:8080/ |

서비스 PC의 IP는 `ipconfig`로 확인.

## 테스트 절차

1. `start.bat` 실행 → 콘솔에 `listen: 0.0.0.0:8080` 표시 확인
2. 같은 PC에서 `http://localhost:8080/` 접속
   - "서버 상태" 카드의 dot이 녹색이면 변환기 발견됨
3. **방식 A (JS XHR)**: 파일 선택 후 "업로드 (XHR)" → 결과 JSON 확인
4. **방식 B (form)**: 파일 선택 후 "업로드 (form)" → 새 탭에 JSON
5. **원격 PC에서 동일 2회 반복**
6. 결과 기록 (Plan-35 §6에 추가):
   - 같은 PC A/B 결과
   - 원격 PC A/B 결과
   - 실패 시: HTTP 상태 코드, F12 Network 요청 URL, `server.log` 해당 라인

## 결과 해석

| 같은 PC A/B | 원격 PC A/B | 해석 |
|-----|-----|------|
| OK/OK | OK/OK | **플랫폼 코드 차이가 원인** → Explorer 업로드 코드와 diff |
| OK/OK | FAIL/FAIL | 네트워크·방화벽 (포트 8080도 막혀있음?) |
| OK/OK | FAIL/OK | JS XHR 계층 (CSP, credentials, 브라우저 정책) |
| FAIL/— | — | 변환기 경로 또는 패키지 누락 → `server.log`, `/health` 확인 |

## 제거

테스트 종료 후 전체 디렉토리 삭제:

```bat
cd ..
rmdir /s /q test-upload-standalone
```

플랫폼 본체와 공유되는 파일은 없으며, `backend/main.py`에서도 이 폴더를 참조하지 않는다.

## 플랫폼 Explorer 업로드와의 차이 (비교 체크리스트)

| 항목 | 이 테스트 | Explorer (플랫폼) |
|------|----------|-------------------|
| 리버스 프록시 | 없음 (직결 8080) | Nginx(Docker) / Tomcat(Win) |
| 인증 | 없음 | 쿠키 세션 + `credentials: include` |
| CORS | 불필요 (same-origin) | `allow_credentials=True` + origin 제한 |
| 응답 포맷 | 단일 JSON | NDJSON 스트리밍 (`application/x-ndjson`) |
| 변환 실행 | CLI subprocess | 백엔드 내부 모듈 호출 |
| 후속 처리 | 없음 | search-index → vector-index 재생성 |
| 오리진 | same (8080) | same(Docker) / cross(Tomcat 8080 → Python 8000) |
| 파일 크기 한도 | 50 MB (하드코딩) | 플랫폼 설정 |

테스트 성공 시 위 7개 항목을 하나씩 플랫폼에서 모사·제거해가며 어디서 깨지는지 특정한다.
