# 플랫폼 가이드 페이지 작성 기준

`contents/guide/` 하위 HTML 페이지 작성 시 따르는 기준.
Verify 사용법 페이지를 레퍼런스로 확정함.

---

## 1. 페이지 구조

```
page-header (h1 + subtitle)
  └ po-hero (시스템 요약, 배지)
  └ 개요 문단 + 메인 스크린샷
  └ h2.po-section-title — 기능 섹션 A
      └ po-system-card (설명, feat-list, 스크린샷)
  └ h2.po-section-title — 기능 섹션 B
      └ ...
  └ h2.po-section-title — 상세/배경 섹션
      └ h3 — 하위 주제 1
      └ h3 — 하위 주제 2
  └ po-callout (마무리)
```

- **h2**: 기능별 독립 섹션. 반드시 `<h2 class="po-section-title" id="...">` 사용
- **h3**: 상세 하위 주제. `id` 필수
- `<div class="po-section-title">`는 사용 금지 — "On this page" 사이드바에 표시되지 않음

## 2. 이모지

사용하지 않는다. 텍스트와 HTML 구조만으로 시각 구분.

## 3. 레이아웃 제약

Explorer 콘텐츠 영역 실질 너비: **400~500px** (좌측 트리 + 우측 OTP 사이)

| 클래스 | 주의사항 |
|--------|---------|
| `po-value-grid` (3컬럼) | 사용 자제. 텍스트가 2~3단어씩 끊김 → **테이블로 대체** |
| `po-feat-list` (2컬럼) | `style="grid-template-columns: 1fr;"` 로 1컬럼 전환 |
| `po-screenshot-grid` (2컬럼) | 가급적 1장씩 세로 배치 |
| `po-spec-table` | 4컬럼 이하 권장. 컬럼 너비 `style="width:..."` 지정 |

## 4. 말투

- 담백한 사내 소개체 ("~합니다", "~입니다")
- 홍보/마케팅 표현 사용하지 않음 ("혁신적인", "극대화", "즉각적인" 등)
- 기능은 사실 위주로 간결하게 설명

## 5. 사용 가능 CSS 클래스

| 용도 | 클래스 |
|------|--------|
| Hero 배너 | `po-hero`, `po-hero-label`, `po-badge-row`, `po-badge` |
| 섹션 제목 | `po-section-title` (h2 태그), `po-section-subtitle` |
| 시스템 카드 | `po-system-card`, `po-system-card-header`, `po-system-name`, `po-system-en`, `po-system-desc` |
| 기능 목록 | `po-feat-list` (1컬럼 권장) |
| 스크린샷 | `po-screenshot`, `po-screenshot-caption` |
| 테이블 | `po-spec-table` |
| 규칙 예시 | `po-rule-example`, `po-rule-example-header`, `po-rule-example-id`, `po-rule-example-name` |
| 강조 박스 | `po-callout` |
| 상태 태그 | `po-system-tag`, `po-tag-stable`, `po-tag-plan` |

## 6. 스크린샷 캡션

- `▲` 기호 사용하지 않음
- 설명체 (예: "유사도 검사 결과 — 유사 구간 하이라이트 및 수치 표시")
- 이미지 파일: `contents/guide/images/` 에 저장

## 7. 레퍼런스 파일

- 기준 페이지: `contents/guide/verify-guide.html`
- CSS 정의: `css/content.css` (`.po-*` 클래스 섹션)
