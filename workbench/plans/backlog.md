# 백로그 — 미착수 / 보류 항목

> 각 계획서에서 이관된 잔여 항목을 모아둔 파일.
> 필요 시 우선순위를 매겨 별도 계획서로 승격하여 진행.
> 최종 수정: 2026-04-24

---

## 대시보드 Phase 3 확장 (Plan-41/43 후속)

> 출처: `done-41-...` 잔여 / `done-43-...` 후속

핵심 UX (Plan-41/43) 완료. 다음은 운영 데이터 쌓인 뒤 실수요 기반으로 판단 권장:

- **타일·사용자 드릴다운** — 타일 클릭 → 서브시스템 상세 뷰, 사용자 행 클릭 → 활동 타임라인
- **시간 범위 필터** — 7/14/30일 드롭다운, 다수 백엔드 쿼리 `days` 파라미터 연동 필요
- **2-column 레이아웃** — 세로 스크롤 길이 단축, 반응형 재설계 리스크 큼
- **자동 refresh pause 토글** — 피드 검토 중 일시 정지
- **수동 새로고침 버튼** — pill 옆 🔄
- **접근성 감사** — 타일 `aria-describedby`, 이모지 `aria-hidden`, focus-trap, 키보드 네비 — 별도 감사 계획 권장
- **Translator 백그라운드 완료 이벤트** — 현재 `status='started'` 만, `services/translator_service.py` 완료 시점 emit 필요
- **`debug.demo_seed_enabled` 플래그** — 프로덕션 배포 시 데모 버튼 숨김

---

---

## DOCX 변환기 — 북마크 localStorage 마이그레이션 도구

> 출처: Plan-37 §6 범위 외

- 운영 개시 후 heading ID 체계가 바뀌면 기존 북마크가 끊어질 수 있음
- heading text 기반 유사도 매칭 등으로 자동 재연결 도구 필요
- 현 시점 플랫폼이 pre-launch 라 불필요, 운영 개시 후 재검토

## DOCX 변환기 — 섹션 래핑 정책 확장

> 출처: Plan-37 §6 범위 외

- `js/app.js:630` 섹션 래핑이 h1/h2 기준 → cascade 로 deeper heading 많아질 시 content-visibility 효과 저하 가능
- h1~h3 확장 vs 현행 유지 판단 — Compare 의존 조사 및 실데이터 기반 판단 후 결정

## DOCX 변환기 — LO 전처리 후 heading 매칭 손실 (swa_kor 류)

> 출처: Plan-37 Phase 3 Docker smoke 검증에서 발견 (2026-04-21)

- `SWA_Sample_KOR.docx` 류: 원본에 `toc 1/2/3` 스타일 복제 단락 41개 + Heading 58개
- LibreOffice 전처리 시 TOC 단락이 자동 삭제됨 (LO 특성)
- 남은 Heading 58개 중 converter 가 14개만 heading 으로 감지 (44개 손실)
- 골든(Word COM 전처리 없이): 53 heading / LO 경로: 14 heading
- 원인 후보:
  - Heading 스타일의 outlineLvl 정보 유실
  - style_id 가 `Heading3` 등으로 정확히 박혀있는데 `_check_style_id` 매칭 누락 여부
- 조사·수정 시점: Phase 4 (numbering.xml 파서) 구현 중 재조사 권장

## DOCX 변환기 — `v:shape` 이미지 추출 실패 (KI-002)

> 출처: Plan-37 Phase 0 시맨틱 게이트 발견 (2026-04-21)
> 상세: `tools/converter/tests/known_issues.md` KI-002

- `SWA_Sample_KOR.docx` 류: 이미지가 `pic:pic` 대신 `v:shape` (도형 객체) 로 감싸진 문서
- converter 가 raw 이미지 파일 추출은 성공 (`_images/` 에 10개 저장), HTML 삽입 실패
- 결과: HTML 에 `<img>` 0건, `<div class="shape-placeholder">` 9건 → 사용자 경험 크게 저하
- 대응:
  - `_has_unextractable_shapes()` 에서 도형 감지 후에도 해당 문단에 `pic:pic`/`inline drawing` 존재 시 정상 추출 경로 폴백
  - 추출된 raw 이미지가 HTML 에서 참조되지 않으면 경고 로그
- Plan-37 범위 외, 별도 플랜 승격 가능

---

## Notebook — 마인드맵 확장

> 출처: Plan-20 Phase 2

- **PNG 내보내기** — SVG→Canvas→PNG 변환, 현재 펼침/줌 상태 캡처, 다크/라이트 대응
- **노드 클릭 → 좌측 PDF 페이지 이동** — 헤딩별 페이지 번호를 백엔드에서 매핑, `goToPage()` 연동

## Notebook — 규격 번호 자동 링크

> 출처: Plan-20 Phase 3

- 웹뷰 렌더링 후 DOM 후처리로 규격 번호(`MIL-STD`, `MIL-DTL`, `AS`, `EN`, `KS` 등)를 클릭 가능한 링크로 래핑
- Notebook: 클릭 시 Explorer 검색 URL로 이동
- Explorer: 본문에서 동일 후처리
- 정규식 패턴을 `js/config.js`에 공통 정의
- precision 우선 (오탐 최소화)

## Notebook — 관련 문서 추천

> 출처: Plan-20 Phase 4

- 문서 열람 시 현재 문서 키워드 vs 다른 문서 키워드 비교 (자카드 유사도)
- 뷰어 사이드 또는 카드 목록에 "비슷한 내 문서" 위젯 (최대 3개)
- `GET /api/translator/document/{doc_id}/related`
- 문서가 충분히 쌓여야 의미 있음

## Notebook — 문서 분석 취소 강화

> 출처: Plan-20 세션 논의

- 분석 진행 중 취소 시 "현재 페이지 완료 후 중단" → 더 즉각적인 중단 방식 검토
- 취소 후 이미 추출 완료된 페이지 결과물 활용 전략

## 플랫폼 — 관리자 설정: 임베딩 백엔드/모델 필드 개선

> 출처: Plan-27 Phase 3, Plan-40 Phase 4 이관

- **Plan-40으로 백엔드는 용도별 분리됨** (`EMBEDDING_BACKEND_INDEX` / `_RUNTIME`) — 환경변수 수준에서만 조작 가능
- 개선 (미착수):
  1. 관리자 UI에 두 백엔드 선택 드롭다운 추가 (index/runtime 각각, 툴팁 포함)
  2. 로컬 모드일 때 `embedding_model` 필드: `bge-m3 (로컬 고정)` 표시 + 편집 비활성
  3. Ollama 모드일 때만 모델명 편집 가능
  4. 변경 시 "재시작 필요" 라벨 (용도별 변수는 재시작 필요)
- 관련 파일: `js/admin-settings.js`, `backend/services/settings_service.py`, `backend/services/embedding_client.py`

## 플랫폼 — Ollama 임베딩 장애 로깅 보강

> 출처: Plan-40 피드백 §10-2

- `_encode_ollama` 실패 시 `requests.RequestException`이 상위로 그대로 전파 — 관리자가 원인(URL·네트워크·모델 미설치) 식별 어려움
- 개선: WARN 레벨 로그 1줄 추가 `"Ollama 임베딩 실패: {url} model={model} {error}"`
- 관련 파일: `backend/services/embedding_client.py`

## 플랫폼 — 인덱싱 진행률 스트리밍

> 출처: Plan-40 피드백 §9.2

- 현재: "벡터 인덱스 재생성 중..." 정적 메시지
- 개선: 배치 `N/총 M` 형태 진행률 스트리밍 (SSE 또는 polling), 장문 문서(수천)에서도 사용자 대기 체감 완화
- 관련 파일: `backend/api/upload.py` (_run_vector_reindex), `tools/build-vector-index.py`, `js/admin-settings.js` (인덱스 재생성 모달)

## 플랫폼 — 관리자 설정 메뉴

> 출처: memory/admin-settings-plan.md

- Launcher 통합 A안 권장
- 현재 `admin-settings.js` 기반, 별도 진입점 필요

## Explorer — Compare 시스템 고도화

> 출처: Plan-13 (핵심 완료, 고도화 보류)

- 레이아웃 비교 롤백 이력
- 상세 비교 알고리즘 개선

## Explorer — 사내 LLM 엔드포인트 연동

> 출처: Plan-10 Phase 4 (사내 서버 확보 후 진행)

- 4-B: 관리자 설정 UI에 LLM 엔드포인트 설정 (URL, 모델명, API 키)
- 4-C: 연결 테스트 API (`POST /api/settings/test-llm`)
- 프로바이더 구현(4-A)은 Phase 1에서 완료됨, 설정 UI + 테스트만 잔여

## 플랫폼 — 개발 워크플로우 정립

> 출처: Plan-15 Phase 4 (실사용 경험 축적 후)

- 구현 전 워크플로우 정립 (codebase-researcher → Plan → 구현)
- 구현 후 워크플로우 정립 (code-reviewer → 수정 → 커밋)
- CLAUDE.md에 워크플로우 섹션 추가

## Explorer — 챗봇 고급 기능

> 출처: Plan-10 Phase 5

- **대화 세션 영속화 (5-A)** — 현재 인메모리 LRU, DB 또는 파일 저장으로 전환 시 세션 유지
- **표 데이터 정밀 QA (5-D)** — GFM 테이블 파싱 후 수치 연산 (최대값, 평균 등)

## Verify — TND(사내 용어 사전) + 캘리브레이션

> 출처: Plan-23 Phase 5j, 5k — **실사용 시작 후 진행**

- **TND 관리 (5j)** — 사내 기술 용어 등록 UI + API. 승인어 검사(STE-1.1) 도입 시 함께 구현.
  현재 승인어 검사 미구현이므로 당장 불필요. 약어 감지의 `common_abbrs`가 축소판 역할 중.
- **캘리브레이션 (5k)** — 실제 사내 기술스펙 문서로 오탐률 측정 + 임계값 튜닝.
  가상 데이터로 튜닝해봐야 실문서에서 틀어지므로, 실문서 투입 후 진행이 효과적.

## Verify — 프리셋 드롭다운 + suppress

> 출처: Plan-23 Phase 5i

- **프리셋 드롭다운** — MIL-STD-461 검증용 / 기술교범 작성용 / 일반 기술문서 / 커스텀. 소스 그룹 ON/OFF는 5i에서 구현 완료 후, 프리셋은 조합을 저장/복원하는 상위 기능
- **억제(suppress) 기능** — 개별 이슈를 "의도적"으로 무시. 실사용 피드백 후 판단

## Verify — 세션 영속화 + 참조 라이브러리

> 출처: Plan-23 Phase 4 Step 2~3

- **결과 재열람 (Step 2)** — `data/verify/{username}/{session_id}/` 저장, 이력 클릭 → 읽기 전용 재열람
- **참조 문서 라이브러리 (Step 3)** — 자주 쓰는 MIL-STD 등 서버 저장, "라이브러리에서 선택" 옵션
- Phase 5 규칙 확장 완료 후 진행 권장 (깊은 규칙 결과를 영속화해야 의미 있음)

## 디자인 시스템 — 추가 리파인먼트

> 출처: Plan-21 Phase 5 보류 항목

- **배경 팔레트 세분화** — `--bg-gray`, `--canvas-bg`, `--content-bg` 값 미세 조정 (전역 영향, 충분한 테스트 필요)
- **경계선 연하게** — `--border-color` 값 조정 (전역 영향)
- **호버 피드백 강화** — `--hover-bg` 톤 + 미세 translate/그림자 조합 (컴포넌트별 테스트 필요)
- **line-height 일괄 교체** — 50+곳, 1.4~1.8 의도적 차이 항목별 확인 필요
- **`--font-small: 12px` 참조 전환** — 토큰 정의 완료, 하드코딩 12px → `var(--font-small)` 점진적 교체
- **독자 버튼 리팩토링** — `.card-btn`, `.translate-page-btn` → `.btn` 시리즈 위임 또는 토큰 참조
- **`.spinner` rgba 토큰화** — 현재 의도적 차이 유지 중, 필요 시 `--spinner-track` 토큰 신설
