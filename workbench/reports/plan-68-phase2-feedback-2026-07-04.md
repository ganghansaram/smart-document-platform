# plan 68 Phase 2 실행 피드백 — 성능복원·관측
> 실행일 2026-07-04 · 실행자 Claude(/run-plan) · 대상 plans/68-explorer-stabilization-perf-adminreset.md

## 요약
- 완료 Task: **C1·C2·C3 구현 + C4 정책 결정** (Phase 2 코드 범위 완료)
- 변경 파일 **5** (backend 3 · frontend 2)
- Critical 0 / Warning 0 / Suggestion — 자체 리뷰에서 async 블로킹 1건 발견·즉시 수정
- 핵심 전제: **GPU 전환 자체는 코드가 아니라 VM `.env` 한 줄**(Phase 0 확정). Phase 2 코드 작업은 "다시 CPU로 새는 걸 **보이게** 만드는" 관측성 + 실패 명확화 + 정직한 라벨.

## 구현 결과
| 영역 | 상태 | 변경 파일 | 메모 |
|------|------|-----------|------|
| **C1** 인덱싱 관측 | ✅ | `embedding_client.py` `upload.py` `analytics.py` `analytics.js` | `get_backend_info()`+`get_ollama_ps()`(GPU=Ollama `/api/ps`)+`index-meta.json` 재빌드 통계 → 대시보드 payload `indexing` → 관측 카드(배지 4종) |
| **C2** Ollama 실패 명확화 | ✅ | `embedding_client.py` `upload.py` | `EmbeddingBackendError(reason)` 연결/타임아웃/모델/HTTP 구분. 서브프로세스 stderr 에서 `_extract_embedding_error()` 로 원인 한 줄 추출 → 재인덱싱 스트림에 명확 노출 |
| **C3** 증분 우선(라벨) | ✅ | `index.html` | 재빌드 버튼 툴팁 정직화("전체 재구축=정합성 안전망 · 평소 업로드·삭제는 자동 증분"). 별도 증분 버튼 신설은 후속(범위) |
| **C4** CPU 폴백 정책 | ✅ 결정 | `upload.py`(타임아웃 메시지) | **명시적 실패 채택**(자동 CPU 폴백 반대 — 사용자가 겪은 600초 타임아웃을 *조용히* 되살림). 타임아웃 메시지에 "index=ollama(GPU) 확인 권장" 안내 |

## 검증 결과
- **게이트**: `py_compile` 4파일 OK · `node --check analytics.js` OK · 변경 모듈 전체 import OK · `/api/health` overall=ok(ollama·faiss ok). 자동 테스트 스위트는 Compare/Verify 유사도 전용(`tests/sim_*`)이라 이 영역 미커버 → **직접 실행으로 검증**(추정 아님).
- **실 Ollama 관통 검증**(개발 PC Docker, host.docker.internal):
  - 백엔드 정보: `index=ollama, runtime=local, model=bge-m3` ✅
  - **GPU 감지**: bge-m3 로드 후 `/api/ps` → `embed_loaded:true, on_gpu:true, vram_ratio:1.0` ✅ (개발 PC Ollama 실제 GPU 사용 확인)
  - **C2 오류 분류**: 잘못된 URL → `reason=connection, "Ollama 연결 실패: ... 서버 미기동 또는 주소·네트워크 오류."` ✅
  - **메타 왕복**: `_record_reindex_meta` → `get_indexing_status().last_reindex` 왕복 ✅
- **UI 검증**(Playwright, testbot=admin): 대시보드 "인덱싱 백엔드" 카드가 "AI 동시성 상태"와 "서브시스템 현황" 사이에 렌더 · 배지 4종(인덱싱 경로=GPU 위임[초록]/임베딩 실행=모델 미로드[앰버]/런타임=local[중립]/마지막 재빌드=기록 없음[중립]) · **콘솔 에러 0** · 스크린샷 `workbench/screenshots/plan68-phase2-indexing-card.png`. C3 툴팁 실페이지 확인.
- **자체 코드리뷰 → 즉시 수정**: `get_ollama_ps()`(동기 requests, 최대 3초)가 `async def dashboard`에서 직접 호출 → 이벤트 루프 블로킹(Ollama 지연=관측 최다 필요 시점에 대시보드 정지). → `await asyncio.to_thread(_safe_indexing_status)` 오프로드. 재검증 통과.
- **회귀 스팟체크**: 대시보드 기존 10개 섹션 전부 유지 · `_safe_*` 방어(조회 실패 시 카드만 비노출, 대시보드 무손상) · 증분 업로드 경로(`_run_vector_incremental`)는 기존 try/except가 EmbeddingBackendError 메시지를 문자열로 흡수(동작 보존) · RAG/검색/트리/편집 미변경.

## 5관점 피드백
- **개발책임자**: Phase 2의 본질은 재구현이 아니라 관측성 — "GPU 옵션이 안 보여"의 정면 해소. 저위험(순수 추가·`_safe` 방어)·고가치. GPU 전환은 배포(.env)로 별도.
- **코드전문가**: 관측 getter는 순수·부작용 0. 재빌드 통계는 작은 상태파일(쓰기 실패 무시=재인덱싱 불사). 오류 분류는 성공 경로 무변경, 예외 분기만 추가. async 오프로드로 이벤트 루프 위생 유지.
- **UI/UX**: 관측 카드를 AI 동시성 카드 형제로 배치 → 관리자가 한 화면에서 "AI·인덱싱" 건강 동시 확인. 빈 섹션 숨김 원칙 준수(조회 실패 시 비노출).
- **웹디자인**: 시스템 건강 배지(`.ad-badge-*`)·footer(`.ad-ai-footer`) 재사용 → **새 CSS 0, 다크모드 자동**. 하드코딩 0.
- **사용자**: 백엔드·GPU·마지막 재빌드가 숫자·색으로 보임. 재빌드 버튼 툴팁으로 "평소엔 자동 증분" 안심.

## 업계표준 재검토
- **관측성**(백엔드/GPU/최근 작업 노출)은 인덱싱 파이프라인 운영의 표준 — Elastic/OpenSearch 의 `_cat/indices`·`_nodes/stats` 처럼 "무엇이 어디서 도는지" 가시화. 본 카드는 그 최소판.
- **GPU 판정 소스**: 로컬 프로세스 지표(`torch.cuda`)가 아니라 **추론 서버 자체 상태(Ollama `/api/ps` `size_vram`)** 를 신뢰 — 위임형 아키텍처의 올바른 관측 지점(plan 경고와 일치).
- **폴백 정책**: 조용한 성능 강등(자동 CPU 폴백)보다 **빠른 명시적 실패 + 진단 힌트**가 SRE 표준(fail-fast, actionable error). 수용한 한계: Ollama 불가 시 재빌드는 실패로 남음(사용자가 index=local 로 의식적 전환 시에만 CPU 경로).

## 잔여·후속 제안
- **배포 반영(회사 VM)**: Phase 0 처방 — VM `.env` `EMBEDDING_BACKEND=local` 제거 + `EMBEDDING_BACKEND_INDEX=ollama` 추가 → `docker compose up -d`(recreate). 반영 후 대시보드 카드로 GPU 사용 확인. 프론트(analytics.js·index.html)는 **nginx 이미지 재빌드+tar** 필요(Phase 1과 함께 배포).
- **C3 실제 증분 버튼**(전체/증분 분리 엔드포인트)은 범위상 후속.
- 재빌드 통계에 search/vector 소요를 대시보드에 더 풍부히(현재 배지 요약).

## 커밋 제안 (요청 시)
3단위 권장:
1. `구현 [plan/68 Phase2]: 인덱싱 관측 백엔드 — 백엔드/GPU(/api/ps)/재빌드 통계` (`embedding_client.py` 관측 getter · `upload.py` 메타·집계 · `analytics.py` payload)
2. `구현 [plan/68 Phase2]: Ollama 임베딩 실패 원인 명확화(C2) + CPU 폴백=명시적 실패(C4)` (`embedding_client.py` `EmbeddingBackendError` · `upload.py` 오류 추출·타임아웃 메시지)
3. `구현 [plan/68 Phase2]: 대시보드 인덱싱 카드 + 재빌드 버튼 라벨 정직화(C3)` (`analytics.js` · `index.html`)
