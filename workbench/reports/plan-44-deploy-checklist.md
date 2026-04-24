# 월요일 배포 가이드 (2026-04-27 月)

**기계적으로 따라하세요. 각 단계 순서대로.**

---

## 준비

- 회사 Linux VM 에 SSH 접속 가능한 상태
- testbot 계정 비밀번호 알고 있음 (`test1234`)
- 브라우저 1개 열어놓기

---

## Step 1 — 코드 받기 (터미널)

### 1-1. VM 에 SSH 로 접속한다.

### 1-2. 아래 명령을 복사해서 붙여넣고 Enter.

```bash
cd /opt/smart-document-platform
```

> 경로가 다르면 실제 배포 위치로 바꿔서 `cd`.

### 1-3. 아래 명령을 복사해서 붙여넣고 Enter.

```bash
git status
```

**결과가 `nothing to commit, working tree clean` 이어야 함.**
아니면 아래 명령으로 로컬 변경 제거:

```bash
git stash
```

### 1-4. 아래 명령을 복사해서 붙여넣고 Enter.

```bash
git pull origin main
```

**"Updating ... Fast-forward" 메시지가 나오면 성공.**

---

## Step 2 — 백엔드 재시작 (터미널)

### 2-1. 아래 명령을 복사해서 붙여넣고 Enter.

```bash
docker compose restart backend
```

### 2-2. 15초 기다린 뒤 아래 명령을 복사해서 붙여넣고 Enter.

```bash
sleep 15 && curl -s http://localhost:8000/api/health | head -c 200
```

**결과에 `"status":"ok"` 또는 `"status":"degraded"` 가 보이면 기동 성공.**

---

## Step 3 — 코드 반영 확인 (터미널)

### 3-1. 아래 명령을 복사해서 붙여넣고 Enter.

```bash
curl -s http://localhost:8000/api/health | grep -o '"ollama_latency_ms":[0-9.]*'
```

**`"ollama_latency_ms":숫자` 가 보이면 Plan-44 반영 OK.**
안 보이면 Step 2 다시.

---

## Step 4 — 브라우저 확인

### 4-1. 브라우저 주소창에 입력 후 Enter.

```
http://회사-VM-주소/admin.html
```

> `회사-VM-주소` 는 실제 VM IP 또는 도메인.

### 4-2. 로그인 화면이 나오면:

- Username: `testbot`
- Password: `test1234`
- **"로그인" 버튼 클릭**

### 4-3. 좌측 메뉴에서 **"대시보드"** 클릭.

### 4-4. 화면을 아래로 스크롤하며 확인:

- **"시스템 건강"** 섹션 — 뱃지 4개 (백엔드 DB / Ollama / FAISS / 디스크) 보여야 함
- **"AI 동시성 상태"** 섹션 — 4개 카드 (p95 응답 지연 / 503 오류 / 피크 동접 / 활성 스트림) 보여야 함
- **"서브시스템 현황"** 섹션 — 타일 4개 (Explorer / Translator / Verify / Notebook)

**위 3개 섹션이 다 보이면 L1 반영 OK.**

### 4-5. 좌측 메뉴에서 **"공통"** 클릭.

### 4-6. 화면을 스크롤하며 확인:

- **"AI 연결"** 섹션 보임
- **"AI 동시성 제어 (LLM Gateway)"** 섹션 보임 ← 새로 추가된 것
  - Gateway 활성화: **토글이 OFF(회색)** 여야 함
  - 동시 LLM 호출 최대: **8**
  - 스트림 전용 슬롯: **3**
  - 대기열 최대 요청 수: **32**
- **"보안"** 섹션 보임

**"AI 동시성 제어" 섹션이 보이고 토글이 OFF 면 L2 반영 OK.**

> ⚠ **토글 건들지 마세요.** 지금은 그냥 확인만. 활성화는 부하 테스트 후에.

---

## Step 5 — 기존 기능 동작 확인 (브라우저)

Plan-44 가 기존 기능을 깨뜨리지 않았는지 확인.

### 5-1. 주소창에 입력:

```
http://회사-VM-주소/index.html
```

### 5-2. 우측 하단 **챗봇 버튼 클릭** → 아무 질문 입력 → **전송**.

**30초 이내에 답변 스트리밍 나오면 OK.**

### 5-3. 주소창에 입력:

```
http://회사-VM-주소/translator.html
```

### 5-4. 문서 목록 로딩되는지 확인.

### 5-5. 주소창에 입력:

```
http://회사-VM-주소/compare.html
```

### 5-6. 화면 로딩되는지 확인 (실제 비교까진 안 해도 됨).

**3개 페이지 모두 정상 로딩되면 기존 기능 회귀 없음 확인.**

---

## Step 6 — 여기까지 문제 없으면 완료

**Flag OFF 상태로 배포 완료.** 이 상태에서 2~3일 사용자 관찰.
사용자 민원 없으면 다음 주에 Phase 2c (부하 테스트) 진행.

---

## 🚨 문제 생기면 롤백 (터미널)

### A. 백엔드가 안 뜬다면

로그 확인:
```bash
docker compose logs backend --tail 50
```

오류 메시지 복사해서 claude 에게 전달.

### B. 사용자가 "갑자기 AI 안 된다" 하면

**즉시 아래 명령 복사 붙여넣기:**

```bash
cd /opt/smart-document-platform && git log --oneline -5
```

복구할 커밋(plan-44 반영 전) 찾아서:

```bash
git reset --hard cf1ffce
docker compose restart backend
```

> `cf1ffce` 는 Plan-44 시작 직전 커밋. 현재 상태에서 이 지점으로 되돌아가면 모든 Plan-44 변경 제거.

### C. 대시보드 "AI 동시성 상태" 가 안 보이면

브라우저 캐시 문제일 수 있음:
- **Ctrl + Shift + R** 눌러서 강제 새로고침
- 안 되면 시크릿 창에서 다시 접속

---

## 체크리스트 (다 했으면 ✓)

- [ ] Step 1: git pull 성공
- [ ] Step 2: `docker compose restart backend` 성공
- [ ] Step 3: `ollama_latency_ms` 필드 확인
- [ ] Step 4: 대시보드에 "AI 동시성 상태" 섹션 + 공통 탭에 "AI 동시성 제어" 섹션 보임, 토글 OFF
- [ ] Step 5: Explorer·Translator·Compare 페이지 정상 로딩
- [ ] 2~3일 사용자 관찰 시작

---

## 그 다음엔?

2~3일 뒤 (D-17 ~ D-14, 수요일~목요일)에:
- **Phase 2c 부하 테스트** 진행
- Agent 에게: "Plan-44 Phase 2c 진행해줘" 라고 말하면 됨

오픈(5월 15일) 1주일 전에:
- **Gateway 토글 ON 전환** + 재시작
- 관리자 대시보드로 모니터링

---

## 참고

- 계획서: `workbench/plans/44-ollama-concurrency-hardening.md`
- 재검토 보고서: `workbench/reports/plan-44-p2b-regression-review-2026-04-24.md`
- Ollama 서버 튜닝 (선택): `docs/03-DOCKER-OPERATIONS.md §2-2-A`
