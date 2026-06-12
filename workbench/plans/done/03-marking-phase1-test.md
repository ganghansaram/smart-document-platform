# 마킹 Phase 1 — 테스트 계획

## 구현 범위

| 항목 | 설명 |
|------|------|
| 백엔드 서비스 | `translator_service.py` — annotations CRUD 함수 6개 |
| 백엔드 API | `translator.py` — 엔드포인트 4개 (GET/POST/PUT/DELETE) |
| 우측 text-layer | 번역 PDF 위에 투명 텍스트 레이어 (텍스트 선택/복사) |
| 좌측 annotation-layer | 원문 PDF 위에 빈 마킹 오버레이 (Phase 2에서 내용 추가) |

---

## 1. 백엔드 API 테스트

### 1-1. GET `/translator/document/{doc_id}/annotations`

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 1 | 마킹 없는 문서 | `{"highlights":[]}` (200) |
| 2 | 마킹 있는 문서 | `{"highlights":[...]}` (200) |
| 3 | 존재하지 않는 doc_id | 404 "문서를 찾을 수 없습니다" |
| 4 | 비로그인 요청 | 401 "Not authenticated" |

### 1-2. POST `/translator/document/{doc_id}/annotations`

| # | 시나리오 | 요청 Body | 기대 결과 |
|---|----------|-----------|-----------|
| 1 | 정상 생성 | `{page:1, rects:[{x,y,w,h}], color:"yellow", text:"...", memo:"..."}` | 200 + `h_` prefix ID 포함 객체 |
| 2 | 필수값 누락 (page 없음) | `{rects:[...]}` | 400 "page, rects 필수" |
| 3 | 필수값 누락 (rects 없음) | `{page:1}` | 400 "page, rects 필수" |
| 4 | color 미지정 | `{page:1, rects:[...]}` | 200, color 기본값 "yellow" |
| 5 | memo/text 미지정 | `{page:1, rects:[...]}` | 200, memo="" / text="" |
| 6 | 존재하지 않는 doc_id | 유효 body | 404 |
| 7 | 다중 rects | `{page:1, rects:[{...},{...}]}` | 200, rects 배열 저장 |

### 1-3. PUT `/translator/document/{doc_id}/annotations/{ann_id}`

| # | 시나리오 | 요청 Body | 기대 결과 |
|---|----------|-----------|-----------|
| 1 | memo 수정 | `{memo:"new memo"}` | 200, memo 변경됨 |
| 2 | color 수정 | `{color:"green"}` | 200, color 변경됨 |
| 3 | memo + color 동시 수정 | `{memo:"x", color:"red"}` | 200, 둘 다 변경 |
| 4 | 존재하지 않는 ann_id | 유효 body | 404 "마킹을 찾을 수 없습니다" |
| 5 | 허용 외 필드 (page) | `{page:5}` | 200, page 값 **변경되지 않음** |

### 1-4. DELETE `/translator/document/{doc_id}/annotations/{ann_id}`

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 1 | 정상 삭제 | 200 `{"success":true}` |
| 2 | 삭제 후 GET 목록 | highlights 배열에서 해당 항목 제거됨 |
| 3 | 존재하지 않는 ann_id | 404 |
| 4 | 이미 삭제된 ann_id 재삭제 | 404 |

### 1-5. 데이터 영속성

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 1 | 서버 재시작 후 GET | 이전 생성 마킹 유지 |
| 2 | annotations.json 파일 | 문서 디렉토리에 정상 생성, JSON 형식 |
| 3 | annotations.json 없는 상태에서 GET | `{"highlights":[]}` (에러 아님) |

---

## 2. 프론트엔드 테스트 — 우측 text-layer

### 2-1. 텍스트 선택/복사

| # | 시나리오 | 확인 방법 | 기대 결과 |
|---|----------|-----------|-----------|
| 1 | PDF 모드 번역 완료 페이지 | 우측 번역 텍스트 드래그 | 텍스트 선택 가능 (파란 하이라이트) |
| 2 | 선택한 텍스트 복사 | Ctrl+C → 메모장 붙여넣기 | 번역 텍스트 정상 복사 |
| 3 | 텍스트 모드 번역 완료 페이지 | 우측 텍스트 드래그 | 텍스트 선택/복사 가능 |
| 4 | 미번역 페이지 | 우측 placeholder 상태 | text-layer 비어있음 (에러 없음) |

### 2-2. 레이어 정렬

| # | 시나리오 | 확인 방법 | 기대 결과 |
|---|----------|-----------|-----------|
| 1 | 번역 PDF 로드 | DevTools → `#right-text-layer` 크기 | canvas와 동일 크기 |
| 2 | 줌 인 (150%) | 줌 후 text-layer 크기 | canvas에 맞게 리사이즈 |
| 3 | 줌 아웃 (70%) | 줌 후 text-layer 크기 | canvas에 맞게 리사이즈 |
| 4 | 페이지 이동 | 다른 페이지 이동 후 | text-layer innerHTML 초기화 + 새 텍스트 |

---

## 3. 프론트엔드 테스트 — 좌측 annotation-layer

### 3-1. DOM 구조

| # | 확인 항목 | 확인 방법 | 기대 결과 |
|---|-----------|-----------|-----------|
| 1 | 요소 존재 | `document.getElementById('left-annotation-layer')` | not null |
| 2 | 부모 컨테이너 | `.parentElement.id` | `left-page-container` |
| 3 | z-index | computed style | `4` (text-layer 위) |
| 4 | pointer-events | computed style | `none` (이벤트 통과) |

### 3-2. 크기 동기화

| # | 시나리오 | 기대 결과 |
|---|----------|-----------|
| 1 | 초기 렌더 | annotation-layer 크기 = canvas 크기 |
| 2 | 줌 변경 | 크기가 canvas와 함께 변경 |
| 3 | 페이지 이동 | 크기 재설정 |

---

## 4. 기존 기능 회귀 테스트

| # | 기능 | 확인 항목 |
|---|------|-----------|
| 1 | 좌측 텍스트 선택 | 원문 텍스트 드래그 선택 여전히 가능 (annotation-layer가 가리지 않음) |
| 2 | 페이지 이동 | 이전/다음 버튼 정상 동작 |
| 3 | 줌 인/아웃 | 양쪽 패널 동시 줌 |
| 4 | 스크롤 동기화 | 좌측 스크롤 시 우측 따라감 |
| 5 | PDF 번역 | 번역 요청 → 폴링 → 결과 표시 |
| 6 | 텍스트 번역 | 텍스트 모드 번역 정상 동작 |
| 7 | 엔진 전환 | PDF↔텍스트 라디오 버튼 전환 |
| 8 | 문서 목록 | 카드 그리드 표시, 열기/삭제 |
| 9 | 트리 패널 | 폴더 탐색, 문서 이동 |

---

## 5. 실행 절차

### 사전 조건
- 백엔드 서버 구동 (port 8000)
- 프론트엔드 서버 구동 (port 8080)
- 테스트용 PDF 문서 1개 이상 업로드 (1페이지 이상 번역 완료)

### 테스트 순서

```
1단계: 백엔드 API (curl/Playwright)
  └─ 1-1 ~ 1-5 항목 순차 실행

2단계: 우측 text-layer (브라우저)
  └─ 번역 완료 페이지에서 2-1, 2-2 확인

3단계: 좌측 annotation-layer (DevTools)
  └─ 3-1, 3-2 확인

4단계: 회귀 테스트 (브라우저)
  └─ 4번 항목 전체 확인
```

### 합격 기준
- 백엔드 API: 전체 시나리오 통과
- 우측 text-layer: 번역 텍스트 선택/복사 가능
- 좌측 annotation-layer: DOM 존재 + 크기 동기화 + 기존 텍스트 선택 미방해
- 회귀: 기존 기능 전부 정상
