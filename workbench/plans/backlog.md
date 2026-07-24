# 백로그 — 미착수 / 보류 항목

> 각 계획서에서 이관된 잔여 항목을 모아둔 파일. 필요 시 우선순위를 매겨 별도 계획서로 승격하여 진행.
> 최종 수정: 2026-07-17

## 🧭 현황 한눈에 (Backlog Dashboard)
> 상태: ⬜ 대기 · 🔄 진행 중 · ✅ 조치(→ 하단 [조치 이력](#-조치-이력)). 상세는 아래 각 섹션.
> **등록일**: 이 표 도입(2026-07-05) 이후 신규 항목만 정확. 기존 항목은 출처 계획 기준 **추정(≈)**.

| # | 항목 | 영역 | 출처 | 등록 | 상태 |
|:--:|------|------|------|------|------|
| 1 | 대시보드 Phase 3 확장 (드릴다운·필터·접근성) | 대시보드 | Plan-41/43 | ≈2026-05 | ⬜ 운영데이터 후 |
| 2 | DOCX 북마크 localStorage 마이그레이션 도구 | 변환기 | Plan-37 | ≈2026-04 | ⬜ 운영개시 후 |
| 3 | DOCX 섹션 래핑 정책 확장 (h1~h3) | 변환기 | Plan-37 | ≈2026-04 | ⬜ 대기 |
| 4 | DOCX LO 전처리 heading 매칭 손실 (swa_kor) | 변환기 | Plan-37 | 2026-04-21 | ⬜ 대기 |
| 5 | DOCX `v:shape` 이미지 추출 실패 (KI-002) | 변환기 | Plan-37 | 2026-04-21 | ⬜ 대기 |
| 6 | Notebook 마인드맵 확장 (PNG·페이지 이동) | Notebook | Plan-20 | ≈2026-03 | ⬜ 대기 |
| 7 | Notebook 규격 번호 자동 링크 | Notebook | Plan-20 | ≈2026-03 | ⬜ 대기 |
| 8 | Notebook 관련 문서 추천 | Notebook | Plan-20 | ≈2026-03 | ⬜ 문서 축적 후 |
| 9 | Notebook 문서 분석 취소 강화 | Notebook | Plan-20 | ≈2026-03 | ⬜ 대기 |
| 10 | 관리자 설정: 임베딩 백엔드/모델 필드 개선 | 플랫폼 | Plan-27/40 | ≈2026-05 | ⬜ 대기 |
| 11 | Ollama 임베딩 장애 로깅 보강 | 플랫폼 | Plan-40 | ≈2026-05 | ⬜ 대기 |
| 12 | 인덱싱 진행률 스트리밍 | 플랫폼 | Plan-40 | ≈2026-05 | ⬜ 대기 |
| 13 | Explorer 인덱스 관측 경량화 (D2·D3, 선택) | Explorer | Plan-68 | 2026-07-05 | ⬜ 대기 |
| 14 | Explorer 인덱싱 업계표준 비교 문서 (Phase 6) | Explorer | Plan-68 | 2026-07-05 | ⬜ 회사데이터 |
| 15 | Explorer Compare 시스템 고도화 | Explorer | Plan-13 | ≈2026-03 | ⬜ 대기 |
| 16 | Explorer 사내 LLM 엔드포인트 연동 (설정·테스트) | Explorer | Plan-10 | ≈2026-03 | ⬜ 사내서버 후 |
| 17 | 개발 워크플로우 정립 | 플랫폼 | Plan-15 | ≈2026-03 | ⬜ 대기 |
| 18 | Explorer 챗봇 고급 (세션영속·표 QA) | Explorer | Plan-10 | ≈2026-03 | ⬜ 대기 |
| 19 | 가이드 튜토리얼 확장 (규칙모드·타 시스템) | Verify/플랫폼 | Plan-49 | 2026-07-05 | ⬜ 대기 |
| 20 | Verify TND(용어사전) + 캘리브레이션 | Verify | Plan-23 | ≈2026-04 | ⬜ 실사용 후 |
| 21 | Verify 프리셋 드롭다운 + suppress | Verify | Plan-23 | ≈2026-04 | ⬜ 대기 |
| 22 | Verify 세션 영속화 + 참조 라이브러리 | Verify | Plan-23 | ≈2026-04 | ⬜ 대기 |
| 23 | 디자인 시스템 추가 리파인먼트 | 디자인 | Plan-21 | ≈2026-04 | ⬜ 대기 |
| 24 | Author 저작 문서 소유권 (소유자·편집권·위임·관리자 재지정) | Author | Plan-60→70 | 2026-07-16 | ⬜ 대기 |
| 25 | Author 저장 충돌 하드닝 (ETag 낙관적 검사·충돌 UI) | Author | Plan-60→70 | 2026-07-16 | ⬜ 대기 |
| 26 | Author DOCX 표지 정책 (3b) | Author | Plan-60→70 | 2026-07-16 | ⬜ 대기 |
| 27 | 작성 문서 admin 큐레이션 (삭제/개명/관리) — 위치 협의 | Author | Plan-60→70 | 2026-07-16 | ⬜ 대기 |
| 28 | 작성 문서 Explorer 검색연동 — 소속 협의(읽기측=Explorer 가능) | Explorer/Author | Plan-60→70 | 2026-07-16 | ⬜ 대기 |
| 29 | Author 편집기 번들 lazy-load | Author | Plan-70 S1 | 2026-07-16 | ⬜ 대기 |
| 30 | 회사 Tomcat·http.server `/data/` 정적 노출 차단 (auth.db 포함) | 플랫폼/보안 | Plan-72 | 2026-07-17 | 🧊 icebox — 환경 C 부활 시 |

> **관리 규칙**: 새 항목 추가 시 이 표에 1행(등록일=오늘) + 아래 상세 섹션. 조치 완료 시 → 상태 ✅ + [조치 이력](#-조치-이력)에 옮기고 상세 섹션 제거.

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

## Explorer — 인덱스 관측 경량화 (Plan-68 D2·D3, 선택)

> 출처: Plan-68 done 이관 잔여 (계획서상 "선택" 명시 — 정리는 전체 재빌드로 자가치유)

- D2: `vector-index_meta` 잔재 점검 — 증분만 돈 벡터 메타와 `contents/` 대조해 고아 유무 리포트
- D3: `index_status` 에 파일 존재/고아 수 반영 (mtime 비교 → 정합 상태 노출) — 관측 개선
- 관련 파일: `backend/api/upload.py`, 인덱스 빌더

## Explorer — 인덱싱 업계표준 비교 문서 (Plan-68 Phase 6)

> 출처: Plan-68 done 이관 잔여 — **회사 VM 데이터 필요**(업로드 로그·Ollama GPU)

- Explorer 인덱싱·정합·관측을 업계 표준과 비교한 개선안 문서 + 추가 식별 이슈 정리
- 산출물: `reports/plan-68-industry-standard-compare-YYYY-MM-DD.md`

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

## Verify/플랫폼 — 가이드 튜토리얼 확장 (Plan-49 잔여)

> 출처: Plan-49 done 이관 — 유사도·비교 모드 튜토리얼화 완료, 아래는 후속

- Verify 규칙 모드(Phase 3) 튜토리얼화 — 21종 규칙 카탈로그, 별도 패턴 필요할 수 있음
- notebook/explorer/admin 가이드에 동일 `po-*` 튜토리얼 패턴 확장 (Phase 1 시범 성공 기반)
- 관련 파일: `contents/guide/*.html`

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

---

## Author — Plan-60 인계 (저작 후속 기능)

> 출처: Plan-60(저작·내보내기) 미완분. Plan-70(저작 기능 Author 교정 이전, 2026-07-16 완료)이 저작의 집을 Author로 옮기면서, 아래는 "현재 없이도 동작 중 = 교정의 선행조건 아님"으로 판단해 Author 인계 백로그로 이관. 필요 시 별도 계획 승격.

- **소유권 (24)** — 소유자 1인 + 편집권 + 위임 + 관리자 재지정. Plan-60 확정 "Soft Lock + 담당자 소유권" 계승. `/api/authored` 소유권 필드 + soft lock(동시 편집 잠금)은 소유권과 강결합이라 함께 검토.
- **저장 하드닝 (25)** — 낙관적 저장 검사(ETag) + 충돌 처리(비교·사본·덮어쓰기) + 오류 토스트. 현재 신규는 409(동명) 보호만 있음(`md-editor.js doSave`).
- **표지 정책 (26)** — DOCX 내보내기 표지 페이지 정책(Plan-60 3b). 내보내기 엔진(3a/3c)은 완료됨.
- **admin 큐레이션 (27)** — 작성 문서 삭제/개명/관리 UI. **위치 협의**: Author 홈 자체 UI vs admin.html/Plan-69 드로어 재사용. 삭제는 Explorer 인덱스(Plan-67 생애주기)와 맞물림 주의.
- **검색연동 (28)** — 작성 문서를 Explorer 검색에 노출. **소속 협의**: 읽기(소비)측 일이라 Explorer 몫일 수 있음(Author 아님).
- **번들 lazy-load (29)** — 편집기 번들(TUI ~수백KB)을 "새 문서" 클릭 시점에 동적 로드. 현재 Author 홈 진입 시 즉시 로드(Plan-70 Acceptance "선호/후속").

---

## 플랫폼/보안 — 회사 Tomcat·http.server `/data/` 정적 노출 차단 (30) — 🧊 icebox

> **상태 (2026-07-24)**: 🧊 **icebox**. 환경 C(Tomcat·http.server)가 **deprecated로 강등**되어 현행 배포(Docker/nginx, `/data/` 403 차단됨)에는 노출 위험 없음 → 배포 차단 요소 아님. 이 항목은 **환경 C를 되살릴 경우에만** 선결 조건으로 승격한다.
> 출처: Plan-72 P4 code-review Critical #1 (2026-07-17). Docker/nginx 는 `docker/nginx.conf:52` `location /data/ {return 403}` 로 차단됨(로컬 검증 완료).

**문제**: `docs/01-DEPLOYMENT-GUIDE.md §5-2`가 회사 Windows(Tomcat 7)에 `data/`를 `webapps/ROOT/`로 통째 복사하도록 지시 → Tomcat:8080·(repo root에서의) `python -m http.server`는 `data/` 전체를 **무인증 정적 서빙**한다. 이는 P72 이전부터 존재하던 플랫폼 노출:
- `data/auth.db`(계정 DB)·`data/settings.json`·`data/verify/<user>/_history.json`가 이미 노출 대상
- Plan-72가 `data/authored/*.md`·`_owners.json`(저작 문서 본문·소유자 인덱스)를 그 집합에 추가 → **회사 Tomcat 환경에서만** 저작 문서 소유권 게이팅이 무력화(집 Docker는 안전)

**조치안** (택1 또는 병행):
- Tomcat: `webapps/ROOT/WEB-INF/web.xml`에 `<security-constraint>`로 `/data/*` 전면 거부(빈 `<auth-constraint/>`), **또는** 배포 시 `webapps/ROOT/` 복사 대상에서 `data/` 하위 제외(백엔드는 파일시스템 직접 접근이라 무영향)
- http.server(디버깅): repo root 대신 프론트 정적 자원만 서빙하도록 안내
- **nginx 403과 동등한 `/data/` 차단이 3환경 모두에서 성립**함을 배포 체크리스트 검증 항목으로 못박기

**우선순위**: 🧊 icebox. 환경 C가 부활하지 않는 한 착수 불필요. 부활 시에는 auth.db 노출을 포함하므로 실사용 전 **선재**(별도 계획 승격).
관련: `workbench/DEPLOY-QUEUE.md`(운영 축 기록), `docs/01-DEPLOYMENT-GUIDE.md §5-2`, `docker/nginx.conf:52`.

---

## ✅ 조치 이력

> 백로그에서 해결·실현되어 제거된 항목의 기록 (언제·어떻게).

| 항목 | 출처 | 조치일 | 조치 내용 |
|------|------|--------|-----------|
| 플랫폼 — 관리자 설정 메뉴 (별도 진입점 필요) | memory/admin-settings-plan | 2026-07-05 | ✅ **Plan-69로 실현** — 공통 헤더 admin 톱니 → 우측 빠른설정 드로어(Gmail식 하이브리드). 커밋 `1ae1966` |
