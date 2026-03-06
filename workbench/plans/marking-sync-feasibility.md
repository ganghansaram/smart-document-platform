# 마킹(형광펜) 동기화 기능 — 타당성 분석

## 1. 요구사항

- 한쪽 패널에 형광펜 마킹 → 반대쪽 동일 영역 자동 동기화
- 마킹에 메모/노트 기록 가능
- 섹션 클릭 시 반대쪽 동일 섹션 하이라이트 + 스크롤 이동
- Explorer 웹 에디터의 하이라이트 방식과 유사한 UX

## 2. 결론: 현재 아키텍처 변경 없이 구현 가능

### PDF.js 레이어 구조

```
[3] annotation-layer (HTML div overlay)  ← 하이라이트/메모 렌더링
[2] text-layer (투명 span)               ← 클릭/선택 이벤트 캡처
[1] canvas (PDF 렌더링)                   ← 변경 불필요
```

하이라이트/메모는 HTML overlay div로 구현 → PDF 파일 수정 불필요.
기존 PDF.js 뷰어 위에 얹는 방식.

### 양쪽 동기화 핵심: 블록 매핑 데이터

번역 시 사이드카 매핑 파일 생성:
```json
{
  "blocks": [
    {
      "id": 1,
      "source_rect": [57, 207, 300, 489],
      "target_rect": [57, 207, 300, 489],
      "source_text": "The proposed method...",
      "target_text": "제안된 방법은..."
    }
  ]
}
```

- **pdf2zh 모드**: 후처리로 블록 좌표 매핑 추출 가능
- **텍스트 번역 모드**: YOLO bbox → 번역 파이프라인에서 매핑 자연 생성
- 텍스트 번역 모드가 매핑 기능에 더 유리함

### 하이라이트 구현 방식

두 가지 접근법 존재:

| 방식 | 설명 | 장단점 |
|------|------|--------|
| **% 좌표 div** | 페이지 크기 대비 % 좌표로 div 배치 | 줌 변경 시 자동 대응, 재계산 불필요 |
| **SVG overlay** | SVG 요소로 하이라이트 렌더링 | 자유형 드로잉에 유리, 하이라이트엔 과도 |

권장: **% 좌표 div** (react-pdf-highlighter 패턴, Vanilla JS 구현 가능)

### 메모/노트 저장

```
data/translator/{username}/{doc_id}/pages/{N}/
  ├── translated.pdf
  ├── text_translated.pdf
  ├── text_mapping.json      ← 블록 매핑 (번역 시 자동 생성)
  └── annotations.json       ← 사용자 마킹/메모 (UI에서 생성)
```

```json
// annotations.json 예시
{
  "highlights": [
    {
      "id": "h1",
      "block_id": 3,
      "side": "source",
      "color": "#ffff00",
      "memo": "핵심 결론 부분",
      "created_at": "2026-03-06T..."
    }
  ]
}
```

---

## 3. 외부 사례 조사

| 제품 | 방식 | 참고점 |
|------|------|--------|
| **PDFRead (hourread.ai)** | 좌=원문 우=번역, 문장 hover 시 반대쪽 하이라이트 | 우리와 거의 동일한 UX 목표 |
| **Overleaf SyncTeX** | 소스↔PDF 양방향 클릭 이동, `.synctex.gz` 매핑 | 사이드카 매핑 파일 패턴 |
| **Hypothes.is** | TextQuoteSelector (텍스트+전후 문맥으로 앵커링) | 문서 변경에도 하이라이트 유지 |
| **react-pdf-highlighter** | PDF.js 위 % 좌표 div overlay | Vanilla JS 동일 구현 가능, 줌 자동 대응 |
| **Bilingual Reader (확장)** | 단락 선택 시 반대쪽 단락 하이라이트 | 단락 단위 동기화 UX |
| **pdf-annotate.js** | SVG overlay + StoreAdapter 패턴 | 백엔드 추상화 참고 |
| **MateCat/Memsource** | 세그먼트 그리드 (원문+번역 테이블) | 세그먼트 인덱스 매핑 |

### PDF.js 하이라이트 구현 핵심

```
1. text-layer에서 mouseup 이벤트 캡처
2. window.getSelection() → Range 객체
3. range.getClientRects() → 선택 영역 좌표
4. 좌표를 페이지 크기 대비 %로 변환
5. annotation-layer에 하이라이트 div 렌더링
6. 블록 매핑으로 반대쪽 대응 영역 조회
7. 반대쪽 annotation-layer에도 하이라이트 렌더링
```

---

## 4. 폴백 번역 작업과의 관계

**독립적으로 진행 가능.** 사전 준비 사항:

- `text_translated.pdf` 생성 시 `text_mapping.json` 함께 저장
- 각 블록에 `source_rect`, `target_rect`, `source_text`, `target_text` 기록
- 이 매핑 데이터가 마킹 동기화의 기반이 됨

→ 폴백 번역 엔진 구현 시 매핑 저장만 추가하면 충분.

---

## 5. 구현 난이도 평가

| 기능 | 난이도 | 비고 |
|------|--------|------|
| 섹션 클릭 → 반대쪽 하이라이트 | 중 | 블록 매핑만 있으면 직관적 |
| 사용자 형광펜 마킹 | 중 | text-layer 선택 → overlay div |
| 양쪽 마킹 동기화 | 중~상 | 블록 매핑 + 부분 텍스트 대응 필요 |
| 마킹에 메모 첨부 | 하 | tooltip/popover UI |
| pdf2zh 모드 매핑 추출 | 상 | pdf2zh 출력에서 역으로 매핑 재구성 필요 |
| 텍스트 모드 매핑 | 하 | 파이프라인에서 자연 생성 |
