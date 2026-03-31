# 백로그 — 미착수 / 보류 항목

> 각 계획서에서 이관된 잔여 항목을 모아둔 파일.
> 필요 시 우선순위를 매겨 별도 계획서로 승격하여 진행.
> 최종 수정: 2026-03-30

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

## 디자인 시스템 — 추가 리파인먼트

> 출처: Plan-21 Phase 5 보류 항목

- **배경 팔레트 세분화** — `--bg-gray`, `--canvas-bg`, `--content-bg` 값 미세 조정 (전역 영향, 충분한 테스트 필요)
- **경계선 연하게** — `--border-color` 값 조정 (전역 영향)
- **호버 피드백 강화** — `--hover-bg` 톤 + 미세 translate/그림자 조합 (컴포넌트별 테스트 필요)
- **line-height 일괄 교체** — 50+곳, 1.4~1.8 의도적 차이 항목별 확인 필요
- **`--font-small: 12px` 참조 전환** — 토큰 정의 완료, 하드코딩 12px → `var(--font-small)` 점진적 교체
- **독자 버튼 리팩토링** — `.card-btn`, `.translate-page-btn` → `.btn` 시리즈 위임 또는 토큰 참조
- **`.spinner` rgba 토큰화** — 현재 의도적 차이 유지 중, 필요 시 `--spinner-track` 토큰 신설
