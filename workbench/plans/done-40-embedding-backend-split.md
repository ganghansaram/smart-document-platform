# Plan-40 — 임베딩 백엔드 용도별 분리 (Explorer 인덱싱 GPU 가속 복원)

**상태**: **완료** (Phase 0~5, Phase 4는 backlog 이관)
**작성**: 2026-04-23
**완료**: 2026-04-23
**관련 시스템**: `backend/services/embedding_client.py`, `backend/services/similarity_engine.py`, `backend/services/vector_search.py`, `backend/api/chat.py`, `backend/api/search.py`, `tools/build-vector-index.py`, `docker-compose.yml`, `backend/config.py`
**관련 메모리**: `memory/MEMORY.md` — "RAG 파이프라인", "Compare 시스템"
**전제 조사**: 본 대화 조사 내역 (커밋 `7c82945` 전환 이력 + GPU 패스스루 부재 확인)

---

## 1. 배경

### 1.1 전환 이력
- **2026-04-02 (커밋 `7c82945` Compare Phase 1f)** — 임베딩 백엔드를 Ollama HTTP → 로컬 sentence-transformers 로 전환
  - 목적: Compare 유사도 검사의 Ollama 배치 제약(`BATCH=2`) 해소 → "~25배 성능" 개선
  - 범위: 전역 `get_embeddings()` 공용 경로 교체 (용도별 분기 없음)
  - 부수 결과: **Explorer 인덱싱도 함께 로컬로 전환됨**
- **2026-04-09 (커밋 `4013ee1`)** — `EMBEDDING_BACKEND` 환경변수 도입 (전역 토글)
  - 기본값 `local` 유지 → 실질 영향 없음

### 1.2 현재 문제
- **백엔드 Docker 컨테이너에 GPU 접근 경로 없음**:
  - `requirements.txt`: `faiss-cpu`, torch CUDA 지정 없음 (sentence-transformers의 transitive로 **CPU-only torch** 설치)
  - `docker-compose.yml`: NVIDIA runtime 패스스루 미설정
  - `embedding_client._cuda_available()` 는 코드에 있지만 컨테이너에서 항상 `False`
- **Ollama 서버(회사 리눅스 VM, vGPU 24G L40)는 GPU 사용 중**
- **결과**: Explorer 인덱싱(대량 배치)이 컨테이너 CPU에서 돌아 이전 대비 현저히 느림
- **`docs/03-DOCKER-OPERATIONS.md` L127** 이미 경고: "GPU 없는 서버에서 local로 운영하면 CPU 폴백되어 임베딩이 **10분 이상** 걸릴 수 있음"

### 1.3 선택 방안 비교
| 방안 | 장점 | 단점 |
|------|------|------|
| A. 전역 Ollama 복귀 | 즉시, 코드 변경 0 | Compare 유사도 회귀 위험 (배치 제약), 검색 쿼리도 HTTP 왕복 |
| **B. 용도별 분리 (채택)** | 각 시나리오 최적 경로, Compare 회귀 없음, 실패 격리 | 설정 2개로 증가, 구현 필요 |
| C. Docker GPU 패스스루 | 근본 해결 | 이미지 +2~3GB, Windows PC 배포 환경에서 무용, NVIDIA Container Toolkit 필요 |

**결론: B 채택** — 3종 배포 환경 호환성 유지 + 리스크 최소 + 구현 비용 낮음.

---

## 2. 현재 구현 상태 분석

### 2.1 임베딩 호출 지점 전수 조사
| # | 파일:라인 | 용도 | 호출 패턴 | 권장 경로 |
|---|-----------|------|----------|----------|
| 1 | `backend/api/chat.py:64` | AI 챗봇 RAG 검색 쿼리 임베딩 | 단건, 실시간 | `local` (저지연) |
| 2 | `backend/api/search.py:119` | Explorer 검색창 쿼리 임베딩 | 단건, 실시간 | `local` (저지연) |
| 3 | `backend/services/similarity_engine.py:679` | Compare 유사도 문장 임베딩 | 수십~수백건 배치, 사용자 대기 | `local` (배치 64) |
| 4 | `backend/services/vector_search.py:120` (`append_documents`) | 업로드 시 증분 벡터 추가 | 업로드 문서의 섹션 배치 | `ollama` (GPU 가속, 업로드 지연 수용) |
| 5 | `tools/build-vector-index.py:54` (`batch_embed`) | Explorer 인덱싱 전체 재생성 | 수천 섹션 대량 배치 | `ollama` (GPU 가속 필수) |

### 2.2 핵심 구조
- `embedding_client.get_embeddings(texts)` — 현재 시그니처는 `backend` 파라미터 없음
- `_encode_local()` — 로컬 sentence-transformers, `config.EMBEDDING_BATCH_SIZE=64` 사용
- `_encode_ollama()` — Ollama HTTP, **청크 분할 루프 없음** (커밋 `7c82945`에서 제거됨)
- `_load_model()` — 싱글턴, 최초 호출 시 로드 (컨테이너 기동 후 첫 요청 지연 발생)

### 2.3 부차 이슈
- **`tools/build-vector-index.py:46`** — `batch_embed(texts, batch_size=32)` 하드코딩
  - 외부 루프가 32건씩 끊어 `get_embeddings`에 전달 → 내부 ST 모델 `batch_size=64` 활용 불가
  - **분리 작업 시 함께 정리** — 하드코딩 제거, `get_embeddings`에 일괄 위임
- **관리자 UI** (`backend/services/settings_service.py:19`, `js/admin-settings.js`)
  - 현재 `embedding_model` 필드 1개 — 로컬 모드일 때 실제로는 `EMBEDDING_LOCAL_MODEL` 경로 사용 (무효 필드)
  - `backlog.md` L85-91 기존 이슈와 통합 해결 가능

---

## 3. Ollama 배치 허용량 사전 검증 — **실측 완료 (2026-04-23)**

### 3.1 측정 환경
- 개발 PC Windows, Ollama 네이티브 구동, `bge-m3:latest` (F16 quant, 566M 파라미터)
- 텍스트 길이: 560 chars/문장 (~60단어 수준)

### 3.2 실측 결과
| batch | 응답시간 | throughput |
|-------|---------|-----------|
| 1 | 49.51s (cold start, 모델 로딩 포함) | — |
| 10 | 2.36s | 4.2/s |
| 50 | 3.17s | 15.8/s |
| 100 | 3.82s | 26.2/s |
| 200 | 5.38s | 37.2/s |
| 500 | 10.19s | **49.1/s** |

### 3.3 결론
- Ollama `/api/embed`는 **500건 단일 호출까지 오류 없이 안정 수용**
- 배치 클수록 throughput 증가 (1→500 스케일)
- 청크 분할은 **안전망으로만 유지**, 기본값 `EMBEDDING_OLLAMA_BATCH=256` 설정
- L40 24GB 환경에서는 512~1024까지 상향 여유 있음 (권장값은 문서 갱신 후 조정)

---

## 4. 설계

### 4.1 환경변수 2개 체제
| 변수 | 기본값 | 적용 대상 |
|------|--------|----------|
| `EMBEDDING_BACKEND_INDEX` | `ollama` | build-vector-index.py, vector_search.append_documents |
| `EMBEDDING_BACKEND_RUNTIME` | `local` | similarity_engine, chat.py, search.py |
| `EMBEDDING_BACKEND` (기존) | `local` | **하위호환** — `_INDEX`/`_RUNTIME` 미설정 시 양쪽 기본값으로 사용 |

- 레거시 `EMBEDDING_BACKEND`는 남겨 두되 deprecated 표기
- `config.py` 로드 순서: 개별(`_INDEX`/`_RUNTIME`) > 전역(`EMBEDDING_BACKEND`) > 코드 기본값

### 4.2 `embedding_client.get_embeddings` 시그니처 확장
```python
def get_embeddings(
    texts: List[str],
    *,
    purpose: Literal["index", "runtime"] = "runtime",
) -> List[List[float]]:
    backend = _resolve_backend(purpose)
    if backend == "local":
        return _encode_local(texts)
    return _encode_ollama(texts)

def _resolve_backend(purpose: str) -> str:
    per_purpose = getattr(config, f"EMBEDDING_BACKEND_{purpose.upper()}", None)
    if per_purpose:
        return per_purpose
    return getattr(config, "EMBEDDING_BACKEND", "local")
```

- keyword-only 인자로 기본값 `"runtime"` → 기존 호출부 미수정 안전
- 인덱싱 경로에서만 `purpose="index"` 명시

### 4.3 호출부 수정 (5곳)
| 파일 | 수정 |
|------|------|
| `tools/build-vector-index.py` | `get_embeddings(texts, purpose="index")`, `batch_size=32` 제거 |
| `backend/services/vector_search.py` | `get_embeddings(..., purpose="index")` |
| `backend/services/similarity_engine.py` | 변경 없음 (기본 `runtime`) |
| `backend/api/chat.py` | 변경 없음 (`get_embedding`은 `get_embeddings` 래퍼 — 자동 `runtime`) |
| `backend/api/search.py` | 변경 없음 (동일) |

### 4.4 폴백 전략
- Ollama 경로 실패 시(네트워크/서버 다운):
  - **인덱싱**: 즉시 실패하여 관리자에게 알림 (자동 폴백 X — 사용자가 재시도하거나 `_RUNTIME` 쪽으로 임시 전환)
    - 근거: 인덱싱은 관리자 수동 트리거. CPU로 자동 폴백되면 "느린데 왜 느린지 모름" 상태 발생 — 명시적 실패가 바람직
  - **런타임**: 현행 유지 (실시간 경로는 `local` 기본이라 Ollama 장애 영향 없음)
- `_encode_ollama`에 `requests.RequestException` 명시 catch + 상세 로그

### 4.5 관리자 UI (별도 Phase)
- `settings_service.py`의 `embedding_model` 필드를 두 경로로 분리 표기
- Phase 5에서 처리 (핵심 동작 검증 후)

---

## 5. 영향 범위 분석

### 5.1 긍정 영향
- Explorer 인덱싱 소요시간 대폭 단축 (예상: CPU 대비 5~20배, 실측 필요)
- Compare 유사도 성능 현상 유지 (회귀 없음)
- 업로드 증분 인덱싱 가속

### 5.2 잠재 회귀 포인트
| 지점 | 회귀 가능성 | 대응 |
|------|------------|------|
| Compare 유사도 품질 | 낮음 (경로 동일) | 골드셋 재검증 |
| 검색 결과 품질 | 낮음 (쿼리 로컬 유지) | smoke 테스트 |
| Ollama 서버 부하 | 중간 (인덱싱 시 spike) | 인덱싱 빈도 낮음 — OK |
| 배치 한도 초과 | 중간 | Phase 1에서 사전 검증 |
| 폐쇄망 환경 (Ollama 없음) | 해당 없음 | `EMBEDDING_BACKEND_INDEX=local` 오버라이드 가능 |

### 5.3 3종 배포 환경별 권장 설정
| 환경 | `_INDEX` | `_RUNTIME` | 비고 |
|------|---------|-----------|------|
| 개발 PC (WSL Docker) | `ollama` | `local` | Ollama 접근 가능 시 (아니면 `local`/`local`) |
| 회사 리눅스 VM | **`ollama`** | **`local`** | L40 GPU 활용 — **본 계획의 주 타겟** |
| 회사 Windows PC | `local` | `local` | Ollama 미구동 시 — 기존 동작 유지 |

---

## 6. 실행 Phase (완료 이력)

### Phase 0 — 사전 실측 ✅
- [x] Ollama `/api/embed` 배치 한도 실측 (10/50/100/200/500) — §3 참조
- [x] 청크 분할은 안전망 유지, 기본값 256 확정

### Phase 1 — 코드 분리 ✅
- [x] `config.py`: `EMBEDDING_BACKEND_INDEX`, `EMBEDDING_BACKEND_RUNTIME`, `EMBEDDING_OLLAMA_BATCH` 추가
- [x] `embedding_client.py`: `get_embeddings(purpose=...)` 분기, `_resolve_backend`, `_encode_ollama` 청크 분할 지원
- [x] `tools/build-vector-index.py`: `purpose="index"` + `batch_size=32` 하드코딩 제거 + 시작 로그 개선
- [x] `backend/services/vector_search.py`: `purpose="index"` 지정

### Phase 2 — 설정 / 문서 ✅
- [x] `docker-compose.yml`: 신규 3개 환경변수 추가
- [x] `.env.example`: 환경별 권장 매트릭스 + 실측 기본값 주석
- [x] `docs/03-DOCKER-OPERATIONS.md`: 환경변수 표 + 선택 기준 + 실측 표 갱신
- [x] `docs/01-DEPLOYMENT-GUIDE.md`: 표·설명 갱신
- [x] `docs/05-ARCHITECTURE.md`: Ollama 서버 박스 설명 갱신

### Phase 3 — 회귀 검증 ✅ (개발 PC, 회사 환경과 동일한 "Ollama 원격 GPU + 백엔드 CPU" 조건)
- [x] Compare 유사도 smoke: 대각선 0.82~0.91, off-diagonal 최대 0.52 (회귀 없음)
- [x] `tests/verify/test_scoring.py`: 10 passed (선재 Verify 룰 4건 실패는 무관)
- [x] RAG 챗봇 UI 테스트: KF-21 개발 단계 질문 정상 응답, 로그에 `device=cpu`로 runtime local 검증
- [x] Search API smoke: hybrid 검색 3건 반환
- [x] **인덱싱 성능 측정 (358 섹션)**:
  - `INDEX=local` (CPU, before 재현): **575.7초** (9분 35초)
  - `INDEX=ollama` (GPU 위임, Plan-40): **18.5초** (스크립트 직접) / **28.3초** (UI end-to-end)
  - **개선: 20~31배** (스크립트 기준 31.1x, UI 기준 20.3x)

### Phase 4 — 관리자 UI 보강 → **backlog 이관**
- 시간 제약 + 현재 환경변수 설정만으로 충분히 동작 (UX 추가 보강은 후속 작업)
- `backlog.md` L85-91 기존 항목과 병합하여 처리 예정

### Phase 5 — 정리 / 커밋 ✅
- [x] 본 계획서 완료 처리 → `done-40-embedding-backend-split.md` 리네이밍
- [x] `memory/MEMORY.md` RAG 파이프라인 섹션 갱신
- [x] `backlog.md` 항목 병합
- [x] 커밋

---

## 7. 최종 성능 측정 (358 섹션, 컨테이너 CPU-only + Ollama GPU)

| 시나리오 | 경로 구성 | 소요 시간 | 증감 |
|----------|----------|----------|------|
| Before (Plan-40 적용 전) | INDEX=local(CPU) | **575.7s** | 기준 |
| After (스크립트 직접) | INDEX=ollama(GPU) | **18.5s** | **-96.8% (31.1x)** |
| After (UI end-to-end) | INDEX=ollama(GPU) | **28.3s** | **-95.1% (20.3x)** |
| 런타임 경로 일관성 | RUNTIME=local | 회귀 없음 | Compare 스코어 동일 |

UI end-to-end 28.3초 = 검색 인덱스(~0.6s) + FAISS 로드/저장 + Python subprocess 오버헤드(~10s) + 순수 임베딩(~18s).

L40 24GB 환경에서는 더 큰 배치가 가능해 **추가 20~50% 단축 여지** 있음.

---

## 8. 롤백 전략
- 단일 환경변수로 되돌림: `EMBEDDING_BACKEND=local` 설정 시 두 경로 모두 local (기존 동작)
- 코드 시그니처는 keyword-only 기본값이라 호출부 수정 안 해도 안전
- Phase별 커밋 분리 → 문제 시 역순 revert 용이

---

## 9. 전문가·사용자 관점 피드백

### 9.1 개발 전문가 관점
**잘된 점**
- 시그니처 호환성: `purpose`를 keyword-only + 기본값 `"runtime"`으로 설계해 **기존 4개 호출부(search/chat/similarity/vector_search 일부) 미수정**. 영향 범위를 인덱싱 2곳으로 국소화.
- 해석 순서 3단 계층(용도별 → 레거시 → 기본값)으로 **환경변수 점진 마이그레이션** 가능. 기존 `EMBEDDING_BACKEND=ollama` 사용자는 그대로 동작.
- 청크 분할은 "안전망" — 실측에서 500 배치도 통과했지만 기본 256으로 보수. 장애 시 1분 내 환경변수로 튜닝 가능.
- 동일 bge-m3 모델이 양쪽에서 동작하므로 **벡터 일관성 cosine=1.0000** — 두 경로 혼용해도 검색 품질 붕괴 없음 (스모크 확인).

**아쉬운 점 / 향후 개선**
- 관리자 UI에 두 변수가 노출되지 않음 (Phase 4 backlog). 운영자가 `.env` 접근 없이 토글 불가.
- 실패 시 로깅이 얕음: `_encode_ollama`가 `requests.RequestException`을 상위로 그대로 던짐 → 관리자가 뭐가 실패했는지 바로 파악 어려움. WARN 레벨 상세 로그 1줄 추가하면 좋음.
- `_cuda_available()` 체크는 아직 컨테이너에 torch CUDA가 없어서 실효 없음 — 향후 GPU 패스스루 시 자동 혜택.

### 9.2 UX 관점
**긍정**
- 사용자(관리자) 체감: 인덱싱 **10분 → 30초 내외** = 한 번의 "Coffee break" → "Just a moment". 대기 중 탭 이탈이 사라질 것.
- 기존 버튼·모달·신호등 UI는 **완전히 동일**하게 동작 — 학습 비용 0.
- 런타임(Compare/검색/챗봇)은 건드리지 않아 **일반 사용자는 변화 체감 없이 빠름만 얻음**.

**개선 여지**
- 인덱싱 모달에 "벡터 인덱스 재생성 중..." 외에 **진행률**(배치 n/total)이 없음. 짧아졌으니 덜 치명적이지만 장문 재인덱싱(수천 문서)에서는 여전히 답답할 수 있음 → Phase 4 이후 고려.
- "인덱스: 경신 필요" 배지가 신규 업로드 후에만 뜨는데, **모델이나 구성이 바뀌었을 때**도 뜨면 좋음 (예: 백엔드가 ollama ↔ local 변경 시 기존 인덱스 재생성 권고).

### 9.3 배포 환경별 안내
| 환경 | 권장 설정 | 예상 효과 |
|------|----------|----------|
| 회사 리눅스 VM (L40 24GB) | 기본값(`_INDEX=ollama`, `_RUNTIME=local`) | 인덱싱 10분 → **15~25초** 예상 (개발 PC 대비 더 빠를 수 있음) |
| 개발 PC (Ollama 네이티브) | 기본값 | 인덱싱 **28초** (실측) |
| 회사 Windows PC (Ollama 없음) | `_INDEX=local`, `_RUNTIME=local` | 기존 CPU 동작 유지 (변화 없음) |
| 폐쇄망 점검 중 | `_INDEX=local`, `_RUNTIME=local` | 임시 롤백, 정상화 후 복구 |

---

## 10. 미결/후속 과제 (backlog.md로 이관)
1. **관리자 UI 임베딩 백엔드 선택 필드** — 기존 `backlog.md` L85-91 항목과 병합. 두 경로 개별 노출 + 툴팁.
2. **Ollama 장애 로깅 개선** — `_encode_ollama` 실패 시 WARN 레벨 "Ollama 임베딩 실패: <url> <error>" 추가.
3. **인덱싱 진행률 표시** — 배치 N/총 M 형태 스트리밍 프로그레스.
4. **모델 변경 감지 배지** — 임베딩 차원·모델 변경 시 "인덱스: 재생성 권고" 신호.

---

## 11. 관련 참고
- 커밋 `7c82945` (Compare Phase 1f 임베딩 인프라 전환 — 로컬 전환 시점)
- 커밋 `4013ee1` (Docker EMBEDDING_BACKEND 환경변수)
- `backlog.md` L85-91 (관리자 UI 임베딩 모델 필드 개선)
- `docs/03-DOCKER-OPERATIONS.md` §2-2, §12-5 (신규 환경변수 선택 기준 + 문제해결)
