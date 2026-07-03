# plan 68 Phase 1 실행 피드백 — 업로드 대용량 수정
> 실행일 2026-07-03 · 실행자 Claude(/run-plan) · 대상 workbench/plans/68-explorer-stabilization-perf-adminreset.md

## 요약
- 완료 Task: 업로드 대용량 3세트(nginx 상향 · 청크 스트리밍 · 413/비-JSON 친절오류) + 사전 크기 체크
- 변경 파일: 4 (`backend/api/upload.py`, `docker/nginx.conf`, `docker/nginx.dev.conf`, `js/tree-menu.js`)
- 코드리뷰: Critical 0 / **Correctness 1(수정 완료)** / Suggestion 0
- 결정: 업로드 상한 **500MB** (사용자 결정) — nginx·백엔드 `MAX_FILE_SIZE`·프론트 `UPLOAD_CONFIG.maxFileSize` 3자 정합

> ⚠️ Phase 0 진단으로 A1 근본원인이 **nginx 100MB 초과(413)** 로 확정됨에 따라, 계획서 원안의 B1(`run_converter` 일반예외 catch)·B3(변환 예외 역추적)는 **본 버그와 무관**으로 판명 → 미적용. 실제 처방은 "제한 상향 + 적재 스트리밍 + 앞단 오류 친절화"로 재구성. Acceptance(“Unexpected token 소멸 + 성공복구/근거있는 실패안내”)는 충족.

## 구현 결과

| 영역 | 변경 | 파일 | 메모 |
|------|------|------|------|
| nginx 제한 | `100m → 500m` | `docker/nginx.conf:5-6`·`nginx.dev.conf:26-27` | 277MB docx 통과. ⚠️ 이미지 재빌드+tar 필요 |
| 백엔드 적재 | `await file.read()`(전체) → 4MB 청크 스트리밍 + 크기 가드 | `backend/api/upload.py:33,343-366` | RAM 피크 축소. `UPLOAD_CHUNK_SIZE=4MB` |
| 프론트 오류 | 413/비-JSON 응답 방어(`response.json()` 파싱 실패 대비) | `js/tree-menu.js:760-775` | `Unexpected token '<'` 소멸 → "파일이 너무 큽니다(최대 500MB)" |
| 프론트 사전체크 | 업로드 전 `file.size` 검사 | `js/tree-menu.js:742-749` | nginx 왕복 전 즉시 안내. `config.maxFileSize` 재사용 |

## 검증 결과
- **게이트:** 프로젝트 자동 lint/build/test 없음(Vanilla·무빌드). 백엔드 `python -m py_compile api/upload.py` → OK. 잔여 `contents` 참조 0.
- **코드리뷰(/code-review, high):** 실결함 1건 — **백업 실패 시 temp 파일 누수**(temp write를 백업 앞으로 옮긴 부작용). → 스트리밍~백업~mkdir을 단일 `try/except Exception`으로 묶어 어떤 실패든 `temp_file.unlink(missing_ok=True)` 하도록 수정. py_compile 재통과.
- **회귀 스팟체크:** 열람(nginx 정적 서빙)·RAG·인덱싱 경로 무변경 확인. `temp_file` 후속 사용처(`_upload_stream` `run_converter`·`finally` 정리) 정상. 정상 크기 업로드 흐름(변환→인덱싱 스트리밍) 로직 보존.
- **Docker 스모크 테스트(로컬 dev, 2026-07-03) ✅** — dev override 가 `nginx.dev.conf`·backend 소스 바인드 마운트라 재빌드 없이 검증. nginx 리로드+backend 재시작 후:
  - **120MB POST → HTTP 401**(413 아님) = 구 100m 초과분이 nginx 통과 → **500m 상향 기능 확인** (277MB docx 도 통과 가능 입증)
  - **550MB POST → HTTP 413** = 새 500m 상한 정상 작동
  - backend 재시작 후 `healthy`, contents/temp 잔여물 0
- **미검증(정직):** ①인증 상태 **end-to-end 업로드**(streaming→변환→인덱싱)는 미실행 — `require_editor` 401 이 함수 본문 전에 차단 + dev 컨테이너 변환 의존(word_com=Windows 전용/LibreOffice 불확실). ②프론트 413 친절메시지·사전 크기체크는 **정적 리뷰만**(순수 JS). 둘 다 저위험(메모리 최적화 + 리뷰 완료). 회사 실배포 후 실문서 1건 확인 권장.

## 5관점 피드백
- **개발책임자:** 회귀 표면 최소(순수 개선). 실배포는 이미지 재빌드+tar 필수 — 반영 경로 유의.
- **코드전문가:** 크기 가드 3중 정합(500MB). temp 누수 수정으로 오류 경로 견고. 과방어 없음.
- **UI/UX:** 암호같은 파싱에러 → 원인·한도 명시 메시지로 전환(핵심 가치).
- **웹디자인:** 기존 `showToast('error')` 재사용, 신규 UI 0.
- **사용자:** 큰 파일은 올리기 전에 막히고 이유를 앎. 277MB 문서는 이제 업로드 가능(배포 후).

## 업계표준 재검토
- 대용량 업로드는 (a) 프록시 한도 상향 (b) 서버 스트리밍 수신 (c) 클라 사전검증 (d) 명확한 413 처리 — 4개 표준 계층 모두 반영. 한계: 단일 프로세스 동기 변환(python-docx 전체 적재)은 여전 → 매우 큰 문서 동시 처리 시 메모리 압박 가능(Phase 6/후속 관찰, 24GB에선 단건 여유).

## ⚠️ 세션 인수인계 (로컬 dev 상태)
- 로컬 dev 컨테이너 `sdp-backend`·`sdp-nginx` 는 **이미 Phase 1 새 코드로 재시작됨**(backend restart + nginx `-s reload`, 2026-07-03). dev override 가 `nginx.dev.conf`·backend 소스를 바인드 마운트하므로 재빌드 없이 반영된 상태. 새 세션에서 다시 restart 불필요.
- 커밋 `2910c02`(main, origin 푸시됨)에 Phase 0·1 전부 포함. 무관 변경(`docx2html.py`·`__version__.py`·`data/verify/*.json`)·릴리즈 압축본은 미커밋으로 남아 있음(의도적).

## 잔여·후속
- **Docker e2e 스모크**(로컬) → **nginx+backend 이미지 재빌드 → tar 배포**(회사)
- (관찰) `proxy_read_timeout 600s`: 초대형 변환이 600s 넘게 이벤트 없이 블록되면 타임아웃 — 후속
- Phase 2(GPU) 는 VM compose `up -d` 로 별도(코드 아님)

## 커밋 제안 (요청 시)
```
구현 [plan/68 Phase1]: 업로드 대용량 지원 — nginx 500m·청크 스트리밍·413 친절오류

Phase 0 진단(277MB docx > nginx 100m → 413 HTML → Unexpected token '<')에 따라
업로드 상한을 500MB로 상향(nginx·백엔드·프론트 3자 정합)하고, 백엔드 파일 수신을
전체 메모리 적재에서 4MB 청크 스트리밍으로 전환, 프론트는 413/비-JSON 응답을
방어해 "파일이 너무 큽니다(최대 500MB)"로 안내 + 업로드 전 크기 사전 체크 추가.
temp 파일 누수(백업 실패 경로) 방지 포함.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```
