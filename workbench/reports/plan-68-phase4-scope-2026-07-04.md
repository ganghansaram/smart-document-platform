# Plan-68 Phase 4 — 올클린 보존/삭제 경계 판별 (2026-07-04)

> Explorer "올클린 초기화"가 지울 대상 = **사용자가 업로드/작성으로 추가한 문서만**.
> 시스템 baseline(페이지·가이드·화면 데코)과 계정·통계·설정은 보존.
> 판별은 추측이 아니라 **사실 근거**(git 추적·변환기 provenance·프론트 참조)로 수행.

## 판별 신호
- **변환기 provenance 주석**(`converter:`/`adapter:`/`_images/image_<hash>`) = 업로드→docx/pdf 변환 문서의 증거
- **프론트 코드 참조**(html/js/css가 해당 경로를 부름) = 시스템 화면 부품(데코레이션)
- git 추적 여부는 **판별 불가**(개발자가 콘텐츠도 커밋해와서 전부 tracked)

## 최종 분류 (contents/ 최상위)
| 항목 | 근거 | 판정 |
|------|------|------|
| `home.html` | 변환기 흔적 0 = 수기 시스템 페이지 | 🟢 보존 |
| `about.html` | 변환기 흔적 0 · 헤더 "About" 메뉴가 로드(`js/app.js:36`) · editor 시스템페이지(`editor.js:150`) | 🟢 보존(크롬) |
| `guide/` | 시스템 사용 가이드(수기, 32파일) | 🟢 보존 |
| `banner_images/` | `translator.html`·`author.css`·`compare.css` 가 참조 = 화면 데코레이션 | 🟢 보존(데코) |
| `authored/` | `.gitkeep` 뿐(빈 폴더, Plan-60 작성문서 저장소) | 🟢 보존(빈 시스템 폴더) |
| `KF-21-개발백서` | 이미지가 `_images/image_<hash>.png` = 변환기 추출 문서 이미지, 메뉴 노출 | 🔴 삭제(업로드 문서) |
| `설계-기준` | HTML 3/3 변환기 흔적, 메뉴 노출 | 🔴 삭제(업로드 문서) |
| `samples` | 데모/샘플, 메뉴 노출 | 🔴 삭제(테스트 콘텐츠) |
| `dev-overview` | `introduction.html` 1장, 메뉴 노출 (사용자 확인으로 포함) | 🔴 삭제(문서) |

## 구현 방식 = allowlist
`_ALLCLEAN_PRESERVE = {home.html, about.html, guide, banner_images, authored}` 만 남기고
그 외 최상위 항목 전부 휴지통 이동. denylist(알려진 것만 삭제)보다 안전 — **미래 업로드도 자동 포함**.

## 사용자 결정 (2026-07-04)
- 범위 = Explorer 한정, 삭제 = 사용자 업로드/작성 문서만
- 계정(`auth.db`)·통계(`analytics.db`)·설정 = 보존(무접촉)
- `backups/` = 이번엔 무접촉(보존)
- 삭제분 = `data/trash/` 이동(복구 가능)
