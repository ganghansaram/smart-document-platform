# 계획서 인덱스 (Plans Index)

> 전 계획의 **상태 단일 출처(SSOT)**. 파일을 뒤지지 말고 여기서 위치·상태를 확인한다.
> 최종 갱신: 2026-07-05

## 디렉토리 규약

| 위치 | 의미 | 파일명 규칙 |
|------|------|------------|
| `plans/*.md` (루트) | **활성** — 진행 중이거나 곧 착수 | `NN-제목.md` |
| `plans/done/` | **완료** — 구현·검증 반영됨 | `NN-제목.md` (옛 `done-` 접두어 제거) |
| `plans/icebox/` | **보류** — 설계·로드맵, 현재 미스케줄 (상세 보존) | `NN-제목.md` |
| `plans/backlog.md` | 잔여 항목 상시 목록 (계획서 미승격 단위) | — |

### 완료 처리 절차 (계획 종료 시 항상 수행)
1. 계획서 헤더 `상태:` → `✅ 완료 (요약)` 로 갱신
2. `git mv NN-제목.md done/NN-제목.md` (루트 → `done/`)
3. **본 README 의 해당 행을 활성 → 완료 섹션으로 이동**
4. 외부 문서(`docs/`, 타 계획서)가 옛 경로를 참조하면 `plans/done/NN-…` 로 수정

> 이 절차는 `CLAUDE.md` 작업 원칙 및 `/plan-execute` 스킬 마지막 단계에 규칙으로 명시되어 있다.
> 보류 전환은 동일하게 `git mv NN-….md icebox/` + README 이동.

---

## 🟢 활성 (Active)

| # | 제목 | 상태 | 비고 |
|---|------|------|------|
| 49 | Verify 가이드 튜토리얼화 | 🟡 Phase 1 완료 / Phase 2 진행 | 유사도 모드 완료, 비교 모드 진행 중 |
| 57 | Verify 비교/검증 모드 뷰 통일 | ⬜ 미착수 (대작 ~11.75일) | 4차 design-review 통과, 착수 결정 대기 |
| 60 | 통일 양식 기반 문서 저작·내보내기 플랫폼 (저작+DOCX 내보내기 통합) | 🟡 Phase 2·3·4 진행 중 | 2a 저작 풀사이클 ✅ + 에디터 디자인 토큰·다크 브리지 ✅(2026-06-18) + 3a/3c DOCX 내보내기 ✅ + 4 "작성 문서" 자동 메뉴 편입 ✅(방법 가). 남음: 2b 소유권·3b 표지·하드닝·검색연동·admin 큐레이션/관리·회귀. 최근 커밋 `cddc377`·`d44e7c1`(push됨) |
| 68 | Explorer 안정화·성능복원·관리자 올클린 | 🟡 Phase 3 D4·Phase 5 부분 완료 | Phase 3 D4(삭제 후 빈 폴더 정리) 완료·UI E2E·푸시(`5fb8bed`). Phase 5 F1·F2·F4 완료·푸시(`f1e1ada`), F3 미해결. Phase 1·2·4 코드완료·배포대기. Phase 6·F3 은 회사 VM 필요. [plans/68-*.md](68-explorer-stabilization-perf-adminreset.md) |

## ❄️ 보류 (Icebox — 설계·로드맵·트리거 대기)

| # | 제목 | 사유 |
|---|------|------|
| 44 | Ollama 동시성·안정성 강화 | **🔫 트리거 대기 (shelved 아님)**. L1 ✅ 완료·가동 중, L2(Gateway) armed·꺼짐. 대시보드 "피크 동시 LLM 4~5" 도달 시 → 선행조건 3종(계획서 상단 ⚠️) 묶음으로 활성 복귀 |
| 08 | PPT → HTML 변환기 | 장기 미착수 (2026-03), 실수요 대기 |
| 09 | 지식 그래프 | 장기 미착수 (2026-03) |
| 24 | Author 시스템 (문서 합성 워크벤치) | Plan-23 후속 선행 대기 |
| 25 | 플랫폼 데이터 아키텍처 로드맵 | 전략 문서, Plan-26 선행 |
| 26 | Notebook 뷰어 + 추출 파이프라인 | Plan-25 선행 작업 |
| 34 | Verify 현업 품질 확보 | 핵심부 Plan-50대 흡수, 잔여(실문서 캘리브레이션)는 실사용 후 — `backlog.md` "Verify 캘리브레이션" 과 중복 |

> 보류 항목 착수 시 루트로 `git mv` + 본 표를 활성 섹션으로 이동.

## ✅ 완료 (Done — `done/`)

| # | 제목 |
|---|------|
| 01 | Fallback 번역기 |
| 02 | Translator OCR 테스트 |
| 03 | 마킹 Phase1 테스트 |
| 04 | 마킹 동기화 타당성 |
| 05 | AI 선택 메뉴 |
| 06 | 플랫폼 리뷰 (8단계 리팩토링) |
| 07 | Translator UX |
| 10 | RAG 챗봇 고도화 |
| 11 | 챗봇 피드백 루프 |
| 12 | RAG 품질 개선 |
| 13 | 문서 비교 리서치 |
| 14 | 디자인 시스템 |
| 15 | 개발 워크플로우 자동화 |
| 16 | Translator 품질 강화 |
| 17 | 지식 Markdown 파이프라인 |
| 18 | Notebook 뷰어 재설계 |
| 19 | Notebook 플랫폼 완성 |
| 20 | 문서 인텔리전스 |
| 21 | 디자인 시스템 리파인먼트 |
| 22 | 운영 안정성 |
| 23 | Compare(Verify) 고도화 |
| 27 | Docker 마이그레이션 |
| 28 | 가이드·기술 문서 |
| 29 | Notebook 페이지 넘김 롤백 |
| 30 | Docker 설정 정비 |
| 31 | Docker Parity |
| 32 | 관리자 설정 재구성 |
| 33 | Verify 출시 전 리뷰 |
| 35 | Explorer 업로드 진단 |
| 36 | Explorer 업로드 수정 |
| 37 | Converter 통합 |
| 38 | 유사도 표절 등급 |
| 39 | DOCX 캡션 하이픈 손실 |
| 40 | 임베딩 백엔드 분리 |
| 41 | 대시보드 플랫폼 전역 |
| 42 | 사용자 프로필 확장 |
| 43 | 대시보드 UX 폴리시 |
| 45 | 유사도 라벨 통일 (v3 체계) |
| 47 | 모달 A/B 리파인먼트 |
| 48 | 유사도 미니맵 개선 |
| 50 | 유사도 점수 공식 통일 (v3) |
| 51 | 유사도 매칭 병합 ri 방향 수정 |
| 52 | 유사도 표 처리 |
| 53 | DOCX 블록 순서 |
| 54 | 제외 마킹 시각 |
| 55 | 표 행 sentence 가드 |
| 56 | 헤딩 Markdown 인식 |
| 58 | verdict 밴드 사각지대 수정 |
| 59 | verdict 라벨 재갱신 + legacy 정합 |
| 61 | Author 셸("빈 방") 구축 — 4번째 시스템 진입 셸·생산 허브 홈 (Claude Design 시안 v2 기반, 바닐라 이식·검증 통과). 후속: 저작 이관(Plan-60)·합성(Plan-24) |
| 62 | 공통 진입 카드(`.entry-card`) 추출 + Verify 허브 현대화 — components.css 공통 스킨 추출, Verify 허브 평상시 elevation 통일(모드 3색·레이아웃 유지), Author 회귀 0 |
| 63 | Notebook 문서 카드를 Author 카드 언어로 정합 — `.content-card`(entry-card 경량 자매) 추출, Notebook `.doc-card` 현대화(호버 들림·다크 솔리드), Author `.au-card` 베이스 전환(회귀 0), 인터랙션 보존 |
| 64 | Verify 허브 모드 색 모노크롬화 — 3색(주황/파랑/초록)="AI생성 느낌" → 단일 악센트 통일(허브 아이콘+최근작업 배지). 유사도 분류색(`sim-*`) 무손상. Plan-62 "색코딩 유지" 번복 |
| 65 | 홈 하단 "목록/이력" 영역 표현 정합 — B축 3시스템 섹션 헤더 규격 통일(B2: 13.5px·600·진한색) + A축 Verify 이력 리스트 A1 패널 감쌈(평평·hairline). 시안 선행→확정→이식→검증(testbot 실데이터·라이트/다크). 배지·점수색 불가침. 기능(저장/재실행)은 OUT. 커밋 `2523f3a` 외 |
| 66 | Notebook 트리 패널 도킹(밀어내기) 모드 — 동료 요구(두 문서+트리 동시 표시) ② 도킹-듀얼 구현. 새 토글 `tp-docked`(핀 보존, B안)·A2 push(`--tp-width`)·트리 리사이즈 핸들(듀얼 로직 재사용)·전역 폭+복원 클램프·`rerenderBothPanels` 재사용. 시안 선행→design-review→구현→code-review(Critical 1+안전 3 수정)→검증. 오버레이 디폴트 유지. ③ 단일폴백·아이콘레일은 OUT |
| 67 | Explorer 트리·문서 생애주기 관리 — 문서 삭제 cascade(파일 휴지통 이동 + 검색·벡터 인덱스 제거 + menu.json 노드 처리) + detach(문서만 제거) + admin 영향 미리보기 모달·dirty-guard + authored 통합 삭제. 벡터=`IndexFlatL2.remove_ids`(순서보존 실측) + `INDEX_WRITE_LOCK`. 재시작 audit=배너 7항목만(이미 표준). 단위 6/6 + 실서버 HTTP e2e + 실브라우저 UI 검증 통과. 커밋 `fba7df6` |
| 69 | Gmail식 하이브리드 관리자 빠른설정 드로어 — 각 시스템(Explorer/Notebook/Verify)에서 페이지 전환 없이 우측 드로어로 그 시스템 설정 조정. `renderAdminSettings(container,opts)` 파라미터화 + 공통 헤더 admin 톱니 1개(lazy-load) + 빈 탭 필터·Explorer 무거운 확장 게이팅. 무거운 관리는 admin.html 존치(Gmail 하이브리드). 실측: 저장 왕복 디스크 영속·no-wipe, admin.html 회귀 0, 콘솔 0. 커밋 `1ae1966` |
| — | (설계) Phase4 AI 요약 설계서 → `phase4-ai-summary-design.md` |

> 결번 46: 미생성. 08·09·24·25·26·34 는 icebox.
