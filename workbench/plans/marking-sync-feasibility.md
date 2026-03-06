# 마킹(형광펜/메모) 기능 — 설계 문서

## 1. 요구사항

- 좌측(원문) 패널에서 텍스트 드래그 → 형광펜 마킹
- 마킹에 메모/노트 기록 가능
- 마킹 목록에서 검색/탐색 → 해당 페이지 이동
- 번역 모드(PDF/텍스트)에 관계없이 동일하게 동작

## 2. 설계 원칙

### 좌측 원문 전용 액션 + 우측 동기화 표시

**마킹 생성/편집/삭제 액션은 좌측(원문) 패널에서만 수행한다.**
**생성된 형광펜은 우측(번역) 패널에도 동일 좌표로 동기화 표시된다.**

```
[좌측 원문]                          [우측 번역]
━━━━━━━━━━━━━━━━━━━━━━              ━━━━━━━━━━━━━━━━━━━━━━
 텍스트 드래그 → 형광펜 생성            → 동일 % 좌표로 형광펜 표시
 형광펜 클릭 → 메모 작성               (메모 popover는 좌측만)
 형광펜 삭제                          → 동기화 삭제
━━━━━━━━━━━━━━━━━━━━━━              ━━━━━━━━━━━━━━━━━━━━━━
 ● 능동: 생성/편집/삭제               ● 수동: 표시만 (동기화)
```

**동기화 원리**: % 좌표 기반이므로 원문/번역 PDF가 동일 레이아웃을
유지하는 한 양쪽에 동일 위치로 표시된다. pdf2zh(PDFMathTranslate)가
레이아웃을 보존하므로 PDF 모드/텍스트 모드 모두 동기화 가능.

### 블록 매핑 동기화 — 제외

**제외 대상**: 텍스트 클릭 시 반대편 문서의 해당 섹션이 하이라이트되는 기능.
이것은 형광펜 표시 동기화와 별개의 기능이며, 이번 범위에서 제외한다.

**제외 사유:**
1. 블록(섹션) 단위 매핑은 정밀도가 낮아 실용적 가치 부족
2. PDF 모드에서는 매핑 데이터 부재로 동기화 불가 → 모드 간 기능 차이 발생
3. 기존 스크롤 동기화로 양쪽 대조에 충분

> 추후 사용자 피드백으로 동기화 수요가 확인되면, 텍스트 모드 한정으로 추가 가능.
> (text_mapping.json 블록 매핑 데이터가 이미 존재하므로 확장 용이)

### 결과: 번역 모드 무관 동일 경험

| 기능 | PDF 모드 | 텍스트 모드 |
|------|---------|-----------|
| 좌측 형광펜 | ✅ | ✅ |
| 우측 동기화 표시 | ✅ | ✅ |
| 좌측 메모 | ✅ | ✅ |
| 마킹 목록 | ✅ | ✅ |
| 번역 텍스트 복사 | ✅ (text-layer) | ✅ (text-layer) |
| 블록 매핑 동기화 | — | — |

→ 사용자에게 모드 차이를 설명할 필요 없음.

---

## 3. 아키텍처

### 뷰어 레이어 구조 (변경 후)

```
좌측 패널 (원문)                    우측 패널 (번역)
├── canvas (PDF 렌더링)            ├── canvas (PDF 렌더링)
├── text-layer (투명 span) ✅       ├── text-layer ← 신규 추가
└── annotation-layer ← 신규 추가   └── annotation-layer ← 동기화 표시용
```

**변경 사항**:
- **우측 text-layer 추가** (PDF 모드 / 텍스트 모드 공통)
  - `page.getTextContent()` → `renderTextLayer()` 호출 추가
  - 부수 효과: 번역 텍스트 복사 가능 (기존에는 불가)
- **좌측 annotation-layer 추가** (형광펜 div overlay, 생성/편집/삭제 액션)
- **우측 annotation-layer 추가** (동기화 표시 전용, 동일 % 좌표)

### 하이라이트 구현 방식

**% 좌표 div overlay** (react-pdf-highlighter 패턴)
- 페이지 크기 대비 % 좌표로 div 배치
- 줌 변경 시 자동 대응, 재계산 불필요
- Vanilla JS로 구현 가능

```
1. 좌측 text-layer에서 mouseup 이벤트 캡처
2. window.getSelection() → Range 객체
3. range.getClientRects() → 선택 영역 좌표
4. 좌표를 페이지 크기 대비 %로 변환
5. annotation-layer에 하이라이트 div 렌더링
6. annotations.json에 저장 (백엔드 API)
```

---

## 4. UI 설계

### 4.1 형광펜 색상

**4색 팔레트**: 노랑(기본), 초록, 빨강, 파랑

- 마킹 생성 시 기본 노랑 적용
- 생성 후 색상 변경 가능 (popover 내)
- 색상에 라벨(중요/동의 등)은 부여하지 않음 — 사용자마다 용도가 다름

### 4.2 메모 UI — 인라인 popover

형광펜 클릭 → 마킹 위에 popover 등장:
- 메모 입력/편집 (textarea)
- 색상 변경 (4색 팔레트)
- 삭제 버튼
- popover 외부 클릭 시 자동 닫힘 + 저장

```
┌─────────────────────────┐
│ ■ ■ ■ ■  (색상 팔레트)   │
│                         │
│ 핵심 결론 부분            │
│ (textarea)              │
│                         │
│              [삭제]      │
└─────────────────────────┘
```

### 4.3 마킹 목록 — 오버레이 팝업

웹북(Explorer)의 **북마크 UI 패턴을 재사용**한다.

- 뷰어 툴바에 "마킹" 버튼 추가
- 클릭 → 중앙 오버레이 팝업 등장 (bookmarks-overlay 패턴)
- ESC / 배경 클릭으로 닫기

**목록 구성**:
- 페이지별 그룹핑 (Page 1, Page 2, ...)
- 각 항목: 색상 뱃지 + 선택 텍스트 미리보기 + 메모 미리보기
- 항목 클릭 → 팝업 닫힘 → 해당 페이지 이동 + 마킹 강조
- 항목별 삭제(×) 버튼, 상단 전체 삭제(Clear All)

```
┌──────────────────────────────────────────┐
│  Markings                    Clear All ✕ │
├──────────────────────────────────────────┤
│  PAGE 2                                  │
│  ──────────────────────────────────────  │
│  🟡 "The proposed method achieves..."  ✕ │
│     └ 핵심 결론 부분                      │
│  🔴 "experimental results show..."     ✕ │
│                                          │
│  PAGE 5                                  │
│  ──────────────────────────────────────  │
│  🟢 "In conclusion, the framework..."  ✕ │
│     └ 최종 요약 - 보고서에 인용           │
└──────────────────────────────────────────┘
```

**재사용 요소** (웹북 bookmarks):
- `bookmarks-overlay` CSS 구조 (오버레이 + 컨테이너 + blur 배경)
- 그룹 헤더 + 항목 리스트 레이아웃
- 항목 hover → 삭제 버튼 표시 패턴
- 다크 모드 대응

---

## 5. 데이터 구조

### 저장 위치

```
data/translator/{username}/{doc_id}/
  ├── original.pdf
  ├── meta.json
  ├── annotations.json       ← 마킹/메모 (문서 단위)
  └── pages/
      └── {N}/
          ├── translated.pdf
          └── text_translated.pdf
```

### annotations.json 스키마

```json
{
  "highlights": [
    {
      "id": "h_20260306_abc123",
      "page": 2,
      "rects": [
        { "x": 10.2, "y": 30.5, "w": 80.1, "h": 2.3 }
      ],
      "color": "#ffff00",
      "text": "selected text snippet",
      "memo": "핵심 결론 부분",
      "created_at": "2026-03-06T14:30:00"
    }
  ]
}
```

- `rects`: 페이지 크기 대비 % 좌표 (다중 라인 선택 시 rect 여러 개)
- `text`: 선택한 텍스트 (목록 미리보기 + 앵커링 검증용)
- `memo`: 사용자 메모 (빈 문자열이면 메모 없음)
- `color`: 형광펜 색상 (`#ffff00`, `#90ee90`, `#ffb3b3`, `#add8e6`)

---

## 6. API 설계

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/document/{doc_id}/annotations` | GET | 마킹/메모 목록 |
| `/document/{doc_id}/annotations` | POST | 마킹 생성 |
| `/document/{doc_id}/annotations/{id}` | PUT | 메모 수정 / 색상 변경 |
| `/document/{doc_id}/annotations/{id}` | DELETE | 마킹 삭제 |

---

## 7. 외부 사례 참고

| 제품 | 방식 | 참고점 |
|------|------|--------|
| **react-pdf-highlighter** | PDF.js 위 % 좌표 div overlay | Vanilla JS 동일 구현 가능, 줌 자동 대응 |
| **Hypothes.is** | TextQuoteSelector (텍스트+전후 문맥으로 앵커링) | 문서 변경에도 하이라이트 유지 |
| **pdf-annotate.js** | SVG overlay + StoreAdapter 패턴 | 백엔드 추상화 참고 |
| **Explorer 웹북 Bookmarks** | 오버레이 팝업 + 그룹 목록 + 클릭 이동 | 마킹 목록 UI 기반 |

---

## 8. 구현 난이도 평가

| 기능 | 난이도 | 상태 |
|------|--------|------|
| 우측 text-layer 추가 | 하 | ✅ Phase 1 |
| 좌측/우측 annotation-layer | 하 | ✅ Phase 1, 2 |
| annotations.json CRUD API | 하 | ✅ Phase 1 |
| 형광펜 생성 (getSelection → % 좌표) | 중 | ✅ Phase 2 |
| 좌우 동기화 표시 | 하 | ✅ Phase 2 |
| 페이지 이동 시 마킹 복원 | 하~중 | ✅ Phase 2 |
| 커스텀 selection overlay | 하 | 대기 (Phase 2.5) |
| 메모 popover UI | 하 | 대기 (Phase 3) |
| 형광펜 4색 팔레트 | 하 | 대기 (Phase 3) |
| 마킹 목록 오버레이 | 하~중 | 대기 (Phase 4) |

---

## 9. 구현 단계별 계획

### Phase 1: 기반 인프라 — ✅ 완료 (`c94cea1`)

우측 text-layer 추가 + 좌측 annotation-layer 추가 + 백엔드 API.

**백엔드:**
1. `backend/api/translator.py` — annotations CRUD 엔드포인트 4개
2. `backend/services/translator_service.py` — annotations.json CRUD 함수 6개

**프론트엔드:**
3. `translator.html` — 우측 `#right-text-layer`, 좌측 `#left-annotation-layer` div
4. `renderRightPage()` — text-layer 렌더링 (번역 텍스트 복사 가능)
5. annotation-layer CSS (z-index 4, pointer-events: none)

---

### Phase 2: 형광펜 마킹 + 좌우 동기화 — ✅ 완료 (`c3ff589`)

텍스트 선택 → 하이라이트 생성/저장/복원 + 우측 동기화 표시.

**구현된 기능:**
1. `mouseup` 핸들러 — `getSelection()` → % 좌표 변환 → API 저장 → div 렌더
2. `createHighlightDiv()` — % 좌표 기반 하이라이트 div 생성
3. `renderAnnotations()` / `renderAnnotationsRight()` — 좌/우 페이지별 렌더
4. `loadAnnotations()` — 서버에서 마킹 로드, `annotationsCache` 캐시
5. `selectionToPercentRects()` + `mergeAdjacentRects()` — 좌표 변환 + 병합
6. 더블클릭 삭제 (Phase 3 popover 전 임시)
7. 우측 annotation-layer 동기화 — 생성/삭제/페이지 이동 시 양쪽 동시 반영

---

### Phase 2.5: 커스텀 selection overlay

PDF.js text-layer의 네이티브 `::selection`은 span별로 끊겨 시각적으로 어색함.
Zotero, Hypothesis 등 논문 리더와 동일하게 커스텀 selection overlay로 교체.

**배경:**
- PDF.js text-layer는 각 텍스트 조각을 `position: absolute` + `transform: scaleX()`로 배치
- 브라우저의 `::selection`은 inline flow에 최적화 → absolute span에서는 조각조각 끊김
- 업계 표준: 네이티브 selection을 숨기고 커스텀 div로 깔끔한 선택 영역 표시

**구현:**
1. CSS: `#left-text-layer ::selection { background: transparent; }` — 네이티브 선택 배경 숨기기
2. `mousedown` — 드래그 시작 플래그
3. `mousemove` — 드래그 중 실시간으로 `getSelection()` → % 좌표 → 임시 div 렌더
4. `mouseup` — 확정 → 기존 저장 플로우 (Phase 2 로직 재사용)

**기존 인프라 활용:**
- `selectionToPercentRects()` — 이미 구현됨
- `mergeAdjacentRects()` — 이미 구현됨
- `createHighlightDiv()` — 임시 선택용 변형 사용

---

### Phase 3: 메모 + 색상

popover UI 추가. 이 단계 완료 시: 메모 작성, 색상 변경, 삭제 가능.

**프론트엔드:**
1. popover 컴포넌트
   - 하이라이트 클릭 → 해당 div 위에 popover 표시
   - 구성: 색상 팔레트(4색) + 메모 textarea + 삭제 버튼
   - popover 외부 클릭 → 자동 닫힘 + 변경사항 저장 (PUT `/annotations/{id}`)
2. 4색 팔레트
   - 노랑 `#ffff00`, 초록 `#90ee90`, 빨강 `#ffb3b3`, 파랑 `#add8e6`
   - 각 색상을 작은 원형 버튼으로 표시, 선택 시 체크 표시
   - 클릭 즉시 하이라이트 색상 반영 + 서버 저장
3. 메모 입력
   - textarea (2~3줄 높이, 자동 확장 없음)
   - placeholder: "메모 추가..."
   - 입력 후 popover 닫힘 시 자동 저장
4. 삭제 버튼
   - popover 하단 "삭제" 텍스트 버튼 (빨간색)
   - 클릭 → DELETE `/annotations/{id}` → 하이라이트 div 제거

**스타일 가이드라인:**
- popover 배경: `var(--white)`, 테두리: `1px solid var(--border-color)`
- border-radius: `8px`, box-shadow: `0 4px 16px rgba(0, 0, 0, 0.15)`
- padding: `12px`
- 색상 팔레트 원형: 20px × 20px, border-radius: `50%`, gap: `8px`
- textarea: font-size `13px`, border `1px solid var(--border-color)`, border-radius `6px`
- 삭제 버튼: font-size `13px`, color `var(--medium-gray)`, hover `#e74c3c`
- 다크 모드: `var()` 변수로 자동 대응
- popover 등장 transition: `opacity 0.15s ease, transform 0.15s ease`
- transform: 살짝 위로 (`translateY(-4px)`) → 등장 시 자연스러운 느낌

```
┌─────────────────────────────┐
│  ● ● ● ●  (노/초/빨/파)     │
│  ─────────────────────────  │
│  메모 추가...                │
│  (textarea)                 │
│                             │
│                      삭제   │
└─────────────────────────────┘
```

---

### Phase 4: 마킹 목록

오버레이 팝업으로 전체 마킹 탐색. 이 단계 완료 시: 전체 기능 완성.

**프론트엔드:**
1. 뷰어 툴바에 마킹 목록 버튼 추가
   - 툴바 우측에 아이콘 버튼 (형광펜 또는 목록 아이콘)
   - 마킹이 있으면 뱃지 카운트 표시 (선택사항)
2. 오버레이 팝업 — bookmarks UI 패턴 재사용
   - `markings-overlay` (bookmarks-overlay 구조 동일)
   - 중앙 모달, max-width `600px`, backdrop blur
   - 헤더: "Markings" + Clear All + 닫기(×)
   - 본문: 스크롤 가능 목록
3. 목록 항목 구성
   - 페이지별 그룹 헤더 (`Page 1`, `Page 2`, ...)
   - 각 항목:
     ```
     ● "selected text preview..."              ✕
       └ 메모 미리보기 (있을 경우)
     ```
   - 색상 뱃지: `8px` 원형, 해당 하이라이트 색상
   - 텍스트 미리보기: 최대 50자 말줄임 (`text-overflow: ellipsis`)
   - 메모 미리보기: font-size `12px`, color `var(--medium-gray)`, 최대 1줄
   - 삭제(×): hover 시 표시 (bookmarks 패턴)
4. 항목 클릭 동작
   - 팝업 닫힘
   - 해당 페이지로 이동 (`goToPage()`)
   - 해당 하이라이트에 포커스 효과 (일시적 강조 → 2초 후 복귀)

**스타일 가이드라인:**
- bookmarks.css 구조 재사용 (overlay, container, header, list, item, empty)
- 그룹 헤더: font-size `12px`, weight `600`, uppercase, letter-spacing `0.5px`
- 항목: padding `8px 12px`, hover background `var(--hover-bg)`
- 색상 뱃지: `display: inline-block`, `width: 8px`, `height: 8px`, `border-radius: 50%`
- 메모 서브텍스트: `margin-left: 16px` (뱃지 아래 들여쓰기)
- 빈 상태: "저장된 마킹이 없습니다." + 안내 텍스트
- 다크 모드: bookmarks.css의 다크 오버라이드 패턴 동일 적용
- 포커스 효과: `box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.4)` → transition out `2s`

---

### Phase 요약

| Phase | 기능 | 상태 | 커밋 |
|-------|------|------|------|
| 1 | 기반 인프라 (text-layer, annotation-layer, API) | ✅ 완료 | `c94cea1` |
| 2 | 형광펜 마킹 + 좌우 동기화 | ✅ 완료 | `c3ff589` |
| 2.5 | 커스텀 selection overlay (드래그 시각 개선) | 대기 | — |
| 3 | 메모 + 색상 (popover UI, 4색 팔레트) | 대기 | — |
| 4 | 마킹 목록 (오버레이 팝업, 페이지 이동) | 대기 | — |

> 순차 진행. Phase 2.5와 3은 독립적이므로 순서 교환 가능.
