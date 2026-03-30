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
