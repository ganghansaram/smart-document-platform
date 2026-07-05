# 배포 원장 (Deploy Queue)

> **운영 축 SSOT** — "무엇이 로컬 완료됐지만 회사 미반영인가 / 다음 배포에 뭐가 나가나 / 회사에서만 확인 가능한 게 뭔가"의 단일 출처.
> 계획서(개발 축)와 **분리**: plan 은 **코드 완성 + 로컬 Docker 검증**으로 닫는다. **회사 배포·회사테스트는 완료 조건이 아니라 이 큐로 흐른다.**
> plan 을 닫을 때, 배포 필요분·회사전용 확인은 계획서 꼬리에 남기지 말고 여기에 1줄 append(예측 아님, 누적).
> 배포 방법: `docs/01-DEPLOYMENT-GUIDE.md` · 검증 기준: `memory/feedback_docker_verification.md`(HTTP 200만으론 부족) · 배포유형 판단: `memory/feedback_docker_deploy.md`
> 최종 갱신: 2026-07-05

---

## 🔜 미배포 (로컬 완료 · 회사 미반영)

> v2.12(2026-07-01 패키징) **이후** 로컬에 쌓인 변경. 각 줄 = `[plan/커밋] 요약 · 배포유형`.

- **[plan/69]** 관리자 빠른설정 드로어 — 프론트 패치(`js/admin-settings.js`·`js/platform-header.js`·`css/*`). 커밋 `1ae1966`·`b243068` (2026-07-05)
- **[plan/68]** Explorer 안정화·성능복원·관리자 올클린 — **전체 이미지 필요**(nginx 500m·청크 업로드 + backend 인덱싱 관측·올클린·빈폴더정리). 커밋 `2910c02`·`abd0e57`·`6379d0c`·`5fb8bed`·`f1e1ada` 등

> ⚠️ **확인 필요**: v2.12(`release-v2.12/platform-v2.12.tar`, 2026-07-01)가 **회사에 이미 반영됐는지**. 미반영이면 v2.10 이후 누적분(Plan-60~67·Author 61~64·Notebook 63/66 등) 전체가 이 큐 대상이 됨 → 사용자 확인 후 채움.

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
| v2.12 | 2026-07-01 | 패키징(`platform-v2.12.tar`). **회사 반영 여부 확인 필요** |
| v2.10 | 2026-06-16 | 회사 배포 baseline. tag `v2.10`(=1a8ad24), `memory/release-v2.10.md` |
