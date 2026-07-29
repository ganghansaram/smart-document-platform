# 배포 원장 (Deploy Queue)

> **운영 축 SSOT** — "무엇이 로컬 완료됐지만 회사 미반영인가 / 다음 배포에 뭐가 나가나 / 회사에서만 확인 가능한 게 뭔가"의 단일 출처.
> 계획서(개발 축)와 **분리**: plan 은 **코드 완성 + 로컬 Docker 검증**으로 닫는다. **회사 배포·회사테스트는 완료 조건이 아니라 이 큐로 흐른다.**
> plan 을 닫을 때, 배포 필요분·회사전용 확인은 계획서 꼬리에 남기지 말고 여기에 1줄 append(예측 아님, 누적).
> 배포 방법: `docs/01-DEPLOYMENT-GUIDE.md` · 검증 기준: `memory/feedback_docker_verification.md`(HTTP 200만으론 부족) · 배포유형 판단: `memory/feedback_docker_deploy.md`
> 최종 갱신: 2026-07-24 (환경 C 톰캣 강등 → deprecated, `/data/` 하드닝 차단 해소·icebox 이관)

---

## 🔜 미배포 (로컬 완료 · 회사 미반영)

> **v2.12 컷(`d01ce46`, 2026-07-01) 이후** 로컬에 쌓인 배포 대상. 각 줄 = `[plan/커밋] 요약 · 배포유형`.
> (문서·계획서·MCP설정 등 비배포 커밋 `f0c6314`·`80dbaaf`·`a9ab780` 등은 제외)

- **[plan/68]** Explorer 안정화·성능복원·관리자 올클린 — **전체 이미지 필요**(nginx 500m·청크 업로드 + backend 인덱싱 관측·올클린·빈폴더정리). 커밋 `f1e1ada`·`2910c02`·`abd0e57`·`6379d0c`·`5fb8bed`
- **[plan/69]** 관리자 빠른설정 드로어 — **프론트 패치**(`js/admin-settings.js`·`js/platform-header.js`·`css/settings-drawer.css`·`css/admin-settings.css`). 커밋 `1ae1966`
- **[plan/70]** '새 문서' 저작 편집기 Explorer→Author 교정 이전 — **프론트 패치**(`author.html`·`css/author.css`·`js/app.js`·`js/author.js`·`js/md-editor.js`). Explorer '새 문서' 메뉴 사라지고 Author 홈에서 저작. RBAC 게이팅 포함. 배포 후 교차검증 시 Explorer '새 문서' 부재 + Author 저작·저장 + 뷰어 게이팅 확인
- **[plan/71]** Author 저작 편집기 화면 트렌디 리디자인 — **프론트 패치**(`css/md-editor.css`·`js/md-editor.js`). 위지윅 단일 컬럼·밝은 상단 바·히어로 제목·접힘 표지 정보·정직 dirty·반응형. 저장 모델 불변. 배포 후 교차검증 시 '빈 문서 작성'→새 화면 + 저장/DOCX + 라이트/다크 확인 (커밋 대기)
- **[plan/72 P3·P4]** Author 셸 통합 + 저작 문서 소유권 — **전체 이미지 필요**(backend `api/document.py` 변경: `/api/save-markdown` name 계약·소유권 캡처·`/api/authored` 인증·소유자필터·신규 `/api/authored/content`). 프론트: 편집기 오버레이→Author 셸 스플릿(`md-editor.js`·`md-editor.css`·`author.html`·`author.css`·`author.js`), Explorer `.md` 잔존 정리(`editor.js`·`tree-menu.js`). **저장 위치 `contents/authored/`→`data/authored/` 이전**(정적 누수 차단). 배포 후 교차검증: 저작 문서 생성/편집/저장, 좌측 패널 문서 전환, 헤더 유지, **하위권한 계정으로 소유권 격리**(타인 문서 목록·읽기·덮어쓰기 차단) (커밋 대기)

- **[plan/73]** 캡션 감지 2계층 분리 — **프론트 패치**(`css/content.css` 만). Explorer 는 캡션 위 간격 **무변화**, 그림 아래 캡션 16px→4px(의도된 개선). 배포 후 교차검증: 캡션 있는 문서(`설계-기준/구조-설계` 등)에서 표 위·그림 아래 캡션이 대상에 붙는지 확인
- **[plan/73 · 업체]** DOCX 변환기 v1.6.0 exe **업체(웹북) 전달** — 배포 축이 아닌 **외부 전달 건**. 패키지 `tools/docx2html-standalone/2026-07-29-webbook-exe-v1.6.0/`(gitignore, exe+README+메일). 업체는 exe 교체만 하면 됨(CLI 인자·호출 방식 불변). 전달 후 확인: 변환 HTML 첫 줄 provenance 가 `1.6.0` 인지
- **[admin/`8754a4e`]** 관리자 설정 결함 3종 — **프론트 패치**(`js/admin-settings.js`·`js/analytics.js`·`css/admin-settings.css`). ① 대시보드 자동갱신 타이머가 해제되지 않아 **다른 섹션(계정관리·각 설정탭)을 30초마다 덮어쓰며 입력값을 날리던 버그** 수정 ② 메뉴관리 '+' 후 취소해도 '새 항목' 이 남던 부작용 제거 ③ 모달 4종 오류를 모달 안에 표시 + Escape 닫기. **UI 변화 有** — 계정 '사용자 추가' 가 인라인 폼→**모달**, 목록 헤더에 `+ 사용자 추가` 버튼, 사용자 표 헤더 sticky. 배포 후 교차검증: 대시보드 방문→계정관리 이동→40초 대기 시 화면·입력 유지 / 대시보드 자체 30초 갱신은 지속 / 메뉴관리 '+'→취소 후 잔존 노드 없음 / '+ 사용자 추가' 모달 생성·Escape 닫기

> ✅ **[보안 하드닝 — 환경 C 강등으로 배포 차단 해소]** (2026-07-24) 이 하드닝은 **환경 C(Tomcat·`http.server`)가 배포 대상일 때만** 유효한 선결 조건이었다. **환경 C는 deprecated(폐지·보류)로 강등** → 표준 배포(Docker/nginx)는 `location /data/ {return 403}`로 이미 차단(로컬 검증 완료)되어 **현행 배포에는 차단 요소 없음**. 하드닝 과제(`data/` 무인증 노출: `auth.db`·`settings.json`·`verify/*`·`authored/*`·`_owners.json`)는 **환경 C를 되살릴 경우의 선결 조건으로 icebox 보존** → `plans/backlog.md` #30(상태: 🧊 icebox — 환경 C 부활 시 승격).

## 📦 다음 배포 대상 (이번 회사 방문분)

- **대상 버전**: v2.13 후보 (또는 v2.12 미반영 시 v2.12 먼저 반영 확인)
- **배포유형**: **전체 이미지** (Plan-68 backend 변경 有 → nginx+backend 재빌드)
- **체크리스트**:
  - [ ] `.env` `OLLAMA_URL=host.docker.internal:11434` 확인
  - [ ] tar 빌드 (`docker-release` 스킬 / `deploy.sh`)
  - [ ] VM 적용 (`deploy.sh` — `COMPOSE_FILE` 고정 방어선 임의수정 금지)
  - [ ] **교차 검증** — `Last-Modified` · nginx 액세스 로그 · 컨테이너 내부 `curl` (HTTP 200만으론 불충분, 유령 컨테이너 교훈)

## 🧪 회사 환경 전용 (로컬 재현 불가)

- **[plan/68 F3]** 세션 만료 추정 이슈 — 회사 환경에서만 재현. 배포 후 콘솔/네트워크 **401 캡처**하여 원인(세션TTL·쿠키·프록시) 확정. 확정되면 별도 fix plan 또는 backlog 로.

## ✅ 배포 이력

| 버전 | 날짜 | 비고 |
|------|------|------|
| v2.12 | 2026-07-01 | ✅ **회사 반영 완료**. 컷=`d01ce46`, `platform-v2.12.tar`. Plan-60~67·Author 61~64·Notebook 63/66 등 포함 |
| v2.10 | 2026-06-16 | 회사 배포 baseline. tag `v2.10`(=1a8ad24), `memory/release-v2.10.md` |
