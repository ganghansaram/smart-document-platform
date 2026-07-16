# plan 71 실행 피드백 — Author 저작 편집기(MdEditor) 화면 트렌디 리디자인
> 실행일 2026-07-16 · 실행자 Claude(/run-plan) · 대상 `workbench/plans/71-author-editor-trendy-redesign.md`

## 요약
- **완료 Task**: 0(이음새/영향성) · A(CSS) · B(JS) · C(검증) — 4/4
- **변경 파일**: 2 (`js/md-editor.js` +92/−? , `css/md-editor.css` +182/−71 · 합 +203/−71)
- **리뷰**: Critical 0 / Warning 2 (1 반영·1 범위외) / Suggestion 5 (1 반영·4 기록)
- **성격**: 표현(presentation) 개편 — 저장 모델·데이터 경로 불변. 실브라우저 end-to-end 검증 통과.

## 구현 결과 (영역별)

| 영역 | 상태 | 변경 | 메모 |
|------|:----:|------|------|
| B. 마크업 재구성 | ✅ | `md-editor.js buildDom()` | 네이비 바→밝은 topbar / 히어로 제목(input→auto-grow **textarea**) 중앙 시트로 이전 / 표지 정보 `<details>` 접힘 / dom 참조 **7키 + 신규 3키**(crumb·status·summary) 보존 |
| B. 편집 엔진 | ✅ | `mountEditor()` | `initialEditType` markdown→**wysiwyg**, `previewStyle` vertical→**tab**, `editor.on('change', refreshStatus)` |
| B. 배선 | ✅ | dirty·요약·브레드크럼 | `refreshStatus`(전 입력원)·`onTitleInput`/`onMetaInput` 분리·Enter preventDefault·저장/열기 시 브레드크럼 상태전환(새 문서/문서 편집) |
| A. CSS 전면 | ✅ | `md-editor.css` | 밝은 topbar / 중앙 시트(패널 토큰, `.entry-card` **미재사용**) / 히어로 제목 / details 알약 / 공통 `.btn`·`.form-*` 재사용 / 다크 편집영역 배경 보정 / **반응형 2 breakpoint** |
| C. 검증 | ✅ | — | 아래 검증 결과 |

## 검증 결과

### 게이트 (프로젝트 자체 탐지)
- **빌드/번들러 없음**(Vanilla, 무빌드) → lint/build/test/typecheck 게이트 부재. 대체로 `node --check js/md-editor.js` **통과**.
- 이 프로젝트의 검증 수단 = 실브라우저(Docker :80, `js`·`css` bind-mount로 수정 즉시 반영).

### 실브라우저 end-to-end (Docker localhost:80)
| 시나리오 | 결과 | 증거 |
|----------|:----:|------|
| 신규 저작(openNew) — 밝은 바·중앙 시트·히어로 제목·위지윅 단일 컬럼 | ✅ | `screenshots/verify-new-light2.png` |
| dirty 토글 — `● 저장되지 않은 변경사항`(앰버)↔`저장됨` + 표지 펼침·요약 | ✅ | `screenshots/verify-expanded-dirty.png` |
| 다크 모드(재오픈) — 편집영역 배경 보정 후 정상 | ✅ | `screenshots/verify-new-dark2.png` |
| 기존 열기(openExisting) — 브레드크럼 "문서 편집"·제목 readOnly·front matter 파싱 | ✅ | crumb=문서 편집·readonly=true·author/docNumber/classification 채워짐 |
| 저장 e2e(로그인 testbot) — 파일 생성·목록 등록·상태 리셋 | ✅ | `/api/authored` 등록·status→저장됨·crumb→문서 편집 |
| **모델 회귀 0** — front matter(title·author·date, 빈 필드 생략) 규칙 동등 | ✅ | 저장 파일 원문 대조 |
| **본문 known-delta** — 골격 무편집 저장이 원본 SKELETON과 **바이트 동일** | ✅ | 드리프트 0 (헤딩 골격은 wysiwyg 재직렬화가 정확 복원) |
| 반응형(440px) — 상단 바 넘침 0, 크럼/상태 숨김, 시트 여백 축소 | ✅ | `screenshots/verify-narrow.png` |
| ESC 닫기(document 디스패치) | ✅ | open→closed (핸들러 불변) |
| 콘솔 에러 0 | ✅ | 잔여 3건은 세션 초반 테스트 흔적(무관) |

> 테스트로 생성한 `Plan71 검증용 문서.md` 는 삭제 → `/api/authored` 0건 청정 복원.

### /code-review 요지 (교차 검토)
- **Critical 0**. 회귀 위험(dom 참조 보존·이벤트 배선·토큰 준수·`.entry-card` 미재사용·미리보기 버튼 클린 제거) 견고 확인.
- **Warning 1 (반응형 미구현)** → **반영**: `@media (max-width:720px/480px)` 추가(상단 바 넘침 방지·시트 여백·제목 축소).
- **Warning 2 (`#7db8f0` 하드코딩, css:214)** → **범위 외**: Plan-60 유산 다크 h2 헤딩 블록으로 이번 diff 밖. 후속 정리 대상(↓).
- **Suggestion 1 (autoGrowTitle 낭비)** → **반영**: `onTitleInput`/`onMetaInput` 분리로 메타 입력 시 title 리플로우 제거.
- Suggestion 2~5(refreshStatus 중복 metaFromFields·badge 미재사용·label for/id·readonly 시각 힌트) → 경미, 기록만(↓ 후속).

## 5관점 피드백
- **개발책임자**: 공유 편집기(Author openNew + Explorer openExisting)라 회귀면이 2 경로였으나, 데이터 경로 불변·dom 참조 보존으로 위험을 CSS/마크업에 국한. 두 경로 다 실측 통과.
- **코드전문가**: private 함수 추가는 최소, 공개 API(openNew/openExisting) 시그니처 불변 → 외부 호출자(author.js:64·editor.js:82) 무영향. 핸들러 분리로 불필요 리플로우 제거.
- **UI/UX**: 브레드크럼 상태전환이 "창작 vs 편집" 맥락을 정직 반영. 접힘 표지 정보로 집필 뷰 정리. 정직한 dirty로 저장 오해 방지.
- **웹디자인**: 신규 영역 색 전부 `var(--token)`(하드코딩 0), 네이비 악센트 통일. `.entry-card` hover-lift 배제로 정적 집필면 적합.
- **사용자**: '빈 문서 작성' → 노션식 깨끗한 단일 캔버스. 좁은 창에서도 넘침 없이 사용 가능.

## 업계표준 재검토 (조사→비교→판단)
- **채택**: 캔버스 히어로 제목·중앙 문서 컬럼·조용한 chrome·접힘 속성(Notion/Docs/Paper/Typora 공통) → 우리 테마로 번역 완료.
- **수용한 한계**: (1) Toast UI 엔진 제약으로 "진짜 단일 캔버스" 불가 → wysiwyg 기본 + 마크다운 하단 세그먼트 잔류가 "가능한 수준". (2) 라이트 기준 toastui CSS만 번들 → 다크 편집영역 배경을 우리 토큰으로 직접 덮음(브리지 확장). (3) 자동저장 미구현 → Google Docs식 "저장됨" 대신 정직한 dirty(가짜 신호 회피).

## 잔여·후속 제안
1. **`#7db8f0` 하드코딩(css:214)** — Plan-60 유산 다크 h2 색. tokens 정합 정리(별도, 이번 범위 밖). 값이 `--active-color`(#63a0e0)와 달라 단순 치환 시 색 변동 → 전용 토큰 검토 필요.
2. **표지 필드 label 연관(a11y)** — `for`/`id` 또는 label 래핑(Suggestion 4). 경미.
3. **readonly 제목 시각 힌트** — 기존 문서 편집 시 잠금 인지 강화(옅은 배경 등, Suggestion 5). 선택.
4. **Plan-72 연동** — Author 문서 워크스페이스(소유자 한정·좌측 패널·Explorer 분리) 착수 시, 이 편집기가 그 패널에서 열리는 동선과 정합 확인.

## 커밋 제안 (요청 시)
```
수정 [plan/71]: Author 저작 편집기 화면 트렌디 리디자인

네이비 바에 제목이 박힌 구식 레이아웃을 업계표준 문서 에디터 패턴으로 개편.
- 밝은 얇은 상단 바(네이비는 저장 버튼·제목 밑줄·활성색 악센트로만)
- 히어로 제목을 중앙 문서 시트 최상단으로 이전(auto-grow textarea)
- 표지 정보(작성자·문서번호·보안등급) 접힘 <details> 로 정리
- Toast UI wysiwyg 단일 컬럼(previewStyle:tab, 마크다운 세그먼트 잔류)
- 정직한 dirty 표시(전 입력원)·브레드크럼 상태전환(새 문서/문서 편집)
- 반응형 2 breakpoint·다크 편집영역 배경 보정

저장 모델 불변(front matter·슬러그·409·훅·readOnly 잠금) — dom 참조 보존.
실브라우저 e2e: 신규·기존·저장(모델 바이트 동등)·다크·반응형·콘솔 0 검증.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```
```
파일: css/md-editor.css, js/md-editor.js
```
```
검증 산출물: workbench/screenshots/verify-{new-light2,expanded-dirty,new-dark2,narrow}.png
```
