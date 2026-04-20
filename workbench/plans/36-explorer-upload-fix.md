# Plan-36: Explorer 업로드 엔드포인트 리네이밍 (Plan-35 본조치)

> **상태**: 실행 대기
> **목표**: `/api/upload` → `/api/document-submit` 리네이밍으로 회사 보안장비 URL 필터 회피
> **선행 플랜**: `done-35-explorer-upload-diagnosis.md` (원인 확정 완료)
> **생성**: 2026-04-20

---

## 0. 배경 요약

Plan-35 조사로 확정된 원인:
- 회사 보안장비(DLP/NGFW 계열)가 `/api/upload` URL 패턴을 inline inspection 후 19초 hold → drop
- 서버 내부 loopback curl은 5ms 내 정상 응답 → 서버·백엔드 무고
- 동일 FormData를 `/api/diag/upload-test` 경로로 보내면 7ms 200 OK → URL 문자열 매칭이 원인

해결책: 엔드포인트 URL에서 "upload" 문자열 제거. 가장 단순·확실.

---

## Phase 0. 범위 스캔 (롤백 전 필수)

**목적**: 리네이밍 대상이 `/api/upload` 1개인지, 다른 엔드포인트(Translator·Verify)도 같이 걸리는지 확정.
**중요**: v2.4의 진단 엔드포인트(`/api/diag/upload-test`)를 대조군으로 사용. Phase 1 롤백 전에 실행해야 대조군이 살아있음.

### 0-1. 원격 PC F12 Console 실행

```js
const paths = [
  '/api/upload',
  '/api/reindex',
  '/api/translator/upload',
  '/api/compare/upload',
  '/api/documents/upload',
  '/api/diag/upload-test',
];
for (const p of paths) {
  const t0 = performance.now();
  const ctrl = new AbortController();
  setTimeout(() => ctrl.abort(), 25000);
  try {
    const fd = new FormData();
    fd.append('file', new Blob(['x']), 't.docx');
    const r = await fetch(p, {method:'POST', body:fd, credentials:'include', signal:ctrl.signal});
    console.log('OK', p, r.status, Math.round(performance.now()-t0)+'ms');
  } catch (e) {
    console.log('FAIL', p, e.name, Math.round(performance.now()-t0)+'ms');
  }
}
```

### 0-2. 판정

| 결과 | 해석 | 조치 |
|------|------|------|
| `OK ... <1000ms` | 통과 | 리네이밍 불필요 |
| `FAIL ... ~19000ms` | **차단됨** | Phase 2 리네이밍 대상에 추가 |
| `FAIL ... <1000ms` | 경로 없음(404) 또는 다른 이유 | 스킵 |

### 0-3. 결과 기록

`§A. Phase 0 결과` (본 문서 하단)에 원격 PC에서 돌린 출력 요약 기록.

---

## Phase 1. 진단 코드 롤백 (Plan-35 §5 준수)

### 1-1. 파일 삭제

```bash
rm upload-diag.html
rm backend/api/upload_diag.py
rm -rf test-upload-standalone/
```

### 1-2. `backend/main.py` revert (2줄)

- Line 13: `upload_diag` import 제거
  ```python
  # 변경 전
  from api import search, chat, document, upload, auth, analytics, settings, menu, translator, compare, upload_diag
  # 변경 후
  from api import search, chat, document, upload, auth, analytics, settings, menu, translator, compare
  ```
- Line 161: 라우터 등록 삭제
  ```python
  # 삭제: app.include_router(upload_diag.router)  # 진단용 (임시, Plan-35)
  ```

### 1-3. 조사용 기타 산출물 확인 후 판단

- `add-firewall-rule.ps1` — 이번 조사용이면 삭제
- `workbench/upload-debug-guide.md` — done-35와 중복이면 삭제

### 1-4. 롤백 검증

```bash
docker compose build
docker compose up -d
curl -sI http://localhost/upload-diag.html | head -1   # expected: HTTP/1.1 404
curl -s http://localhost/api/diag/upload-test -X POST | head -c 200  # expected: 404 Not Found
```

---

## Phase 2. 엔드포인트 리네이밍

### 2-1. 이름 확정

기본: **`/api/document-submit`**

Phase 0 결과에 따라 다른 엔드포인트도 동일 원리로:
- `/api/translator/upload` → `/api/translator/document-submit`
- `/api/compare/upload` → `/api/compare/document-submit`

"upload" 문자열 완전 제거가 목적 — 장비 룰이 어떤 정확 문자열을 보는지 불명하므로 안전 마진 확보.

### 2-2. 변경 파일 (최소)

**`backend/api/upload.py:299`**:
```python
# 변경 전
@router.post("/upload")
# 변경 후
@router.post("/document-submit")
```

**`js/tree-menu.js:669`**:
```js
// 변경 전
var response = await fetch(backendUrl + '/api/upload', {
// 변경 후
var response = await fetch(backendUrl + '/api/document-submit', {
```

### 2-3. 잔존 참조 확인

```bash
grep -rn '/api/upload\b' backend/ js/ docs/ contents/guide/ css/ data/
```

결과에 따라 추가 수정. 특히:
- `docs/` 가이드 문서 내 업로드 안내
- `data/settings.json` API 경로 참조 (있으면)
- 테스트·샘플 파일

### 2-4. 리네이밍하지 **않을** 것

- `backend/api/upload.py`의 다른 엔드포인트 `/reindex`, `/index-status` (upload 문자열 없음, Phase 0에서 통과 확인 시)
- `upload.py` 파일명·모듈명 자체 (내부 코드만 영향, 외부 URL 아님)
- 변수명 `UPLOAD_CONFIG`, `UPLOAD_TEMP_DIR` 등 (URL 아님)

---

## Phase 3. 로컬 검증 (집 개발 PC)

### 3-1. Docker 재빌드 + 기동

```bash
docker compose build
docker compose up -d
docker compose ps  # healthy 확인
```

### 3-2. 기능 테스트

- http://localhost/ Explorer 접속
- 트리 노드 업로드 버튼 → 소형 DOCX 업로드 시도
- F12 Network: 요청 URL이 `/api/document-submit`으로 나가는지 확인
- 변환 완료 → 페이지 로드
- 검색 인덱스 / 벡터 인덱스 갱신 확인

### 3-3. 엣지 케이스

- [ ] 한글 파일명 (`테스트문서.docx`)
- [ ] 한글 target_path (`contents/설계-기준/…`)
- [ ] 이미 존재하는 경로 → 자동 백업 정상 동작
- [ ] 대용량 파일 (10MB 이상) — 진행 표시 정상

---

## Phase 4. v2.5 빌드 & 배포

### 4-1. 이미지 export

```bash
docker save -o platform-v2.5.tar smart-document-platform-backend smart-document-platform-nginx
ls -lh platform-v2.5.tar  # 약 4.0GB
```

### 4-2. 반출 파일

| 파일 | 크기 | 비고 |
|------|------|------|
| platform-v2.5.tar | ~4.0GB | 필수 |
| docker-compose.yml | 작음 | 변경 없음 → 재전송 불필요 |
| deploy.sh | 작음 | 변경 없음 → 재전송 불필요 |

### 4-3. 회사 리눅스 VM 배포

```bash
./deploy.sh platform-v2.5.tar
docker compose ps  # healthy 확인
```

### 4-4. 원격 PC 최종 검증

- 원격 PC 브라우저에서 Explorer 접속
- 업로드 성공 확인
- F12 Network: `POST /api/document-submit` 200 OK
- 처리 시간 정상 (소형 파일 몇 초 내)
- 변환 결과 페이지 로드 + 검색 인덱스 갱신 확인

**성공 기준**: 원격 PC에서 5초 내(변환 시간 제외) 업로드 응답 + 변환 결과 페이지 표시.

---

## Phase 5. 후속 작업

### 5-1. git commit 3분할

```bash
# (a) 계획서 정리 — Plan-35 완료 처리 + Plan-36 최종판
git add workbench/plans/done-35-explorer-upload-diagnosis.md \
        workbench/plans/done-36-explorer-upload-fix.md
git commit -m "정리 [Plan-35/36] 완료 처리 — 원인 확정 + 본조치 기록"

# (b) 진단 도구 철거
git rm upload-diag.html backend/api/upload_diag.py
git rm -r test-upload-standalone/
git add backend/main.py  # revert 2줄 반영
git commit -m "정리 [Plan-35] 진단 도구 철거"

# (c) 엔드포인트 리네이밍 본조치
git add backend/api/upload.py js/tree-menu.js
# Phase 0 결과에 따라 추가 파일
git commit -m "수정 [Explorer] 업로드 엔드포인트 리네이밍 (/api/upload → /api/document-submit, 보안장비 회피)"
```

### 5-2. Plan-36 완료 처리

```bash
mv workbench/plans/36-explorer-upload-fix.md workbench/plans/done-36-explorer-upload-fix.md
```

### 5-3. 사내 IT 문의 (병행)

`done-35-…md`의 §7-4 템플릿 활용:
- 제목, 현상, 관측된 사실, 요청 사항 포함
- 보안팀에 URL 필터링 정책 변경 이력 확인 요청
- 장기 해결책: 화이트리스트 예외 등록 가능 여부

### 5-4. MEMORY.md 업데이트

- "진행 중 계획" 목록에서 Plan-35/36 제거
- "완료된 계획" 목록에 추가

---

## Phase 6. 완료 처리

- [ ] Plan-36 → `done-36-...md` 이름 변경
- [ ] MEMORY.md 갱신
- [ ] 기존 tar 파일 정리 판단 (v2.3, v2.4 삭제 여부 사용자 결정)

---

## 리스크 & 대응

| # | 리스크 | 대응 |
|---|--------|------|
| 1 | 리네이밍 후에도 차단 | Phase 0 스캔으로 사전 감지. 차단 지속 시 보안장비가 URL 패턴 아닌 다른 요소(Content-Type, body 크기 등)를 볼 가능성 → 별도 조사 |
| 2 | Translator·Verify 업로드도 걸림 | Phase 0에서 확인 → Phase 2에서 일괄 처리 |
| 3 | v2.5 배포 후 기존 세션 무효화 | 세션 DB는 `data/` 볼륨이라 이미지 재배포와 무관, 쿠키 유지 |
| 4 | 회사 VM 배포 중 서비스 중단 | deploy.sh는 기존 컨테이너 정리 후 재기동 → 수 초~수십 초 중단. 사용자 공지 필요 |
| 5 | 잔존 `/api/upload` 참조 누락 | Phase 2-3 grep + Phase 3 브라우저 F12 Network 확인으로 이중 체크 |

---

## 체크리스트 (실행 중 업데이트)

### Phase 0 범위 스캔
- [ ] 원격 PC에서 스캔 스크립트 실행
- [ ] 결과를 §A에 기록

### Phase 1 롤백
- [ ] `upload-diag.html` 삭제
- [ ] `backend/api/upload_diag.py` 삭제
- [ ] `test-upload-standalone/` 삭제
- [ ] 기타 조사 산출물 판단 완료
- [ ] `backend/main.py` 2줄 revert
- [ ] 롤백 후 재빌드 + 404 검증

### Phase 2 리네이밍
- [ ] `backend/api/upload.py` 수정
- [ ] `js/tree-menu.js` 수정
- [ ] Phase 0 기반 추가 파일 수정
- [ ] grep 잔존 참조 검증

### Phase 3 로컬 검증
- [ ] 로컬 Docker 업로드 성공
- [ ] 한글 파일명/경로 성공
- [ ] 기존 파일 백업 동작
- [ ] 검색·벡터 인덱스 갱신

### Phase 4 빌드·배포
- [ ] v2.5 tar 빌드
- [ ] 회사 VM 배포
- [ ] 원격 PC 업로드 성공 확인

### Phase 5·6 마무리
- [ ] 커밋 3분할
- [ ] IT 문의 전달
- [ ] MEMORY.md 갱신
- [ ] Plan-36 → done-36 이름 변경
- [ ] tar 정리 판단

---

## §A. Phase 0 결과 (2026-04-20)

### A-1. 1회차 — 배치 스캔 (큐 간섭 의심)

원격 PC에서 6개 경로 연속 실행:

| 경로 | 1회 | 2회 | 비고 |
|------|------|------|------|
| `/api/upload` | ERR_CONNECTION_RESET 18908ms | ERR_CONNECTION_TIMED_OUT 21005ms | 타임아웃 |
| `/api/reindex` | ERR_CONNECTION_TIMED_OUT 21012ms | ERR_CONNECTION_TIMED_OUT 21005ms | 타임아웃 |
| `/api/translator/upload` | ERR_CONNECTION_TIMED_OUT 21005ms | 400 7794ms | **불일치** |
| `/api/compare/upload` | 422 빠름 | 422 빠름 | 통과 |
| `/api/documents/upload` | 404 빠름 | 404 빠름 | 통과 |

모순: `/api/compare/upload`에도 "upload" 포함됐는데 통과. URL 단순 문자열 매칭 룰이 아님. 사용자 가설 = **앞선 차단 요청의 큐 간섭이 후속까지 번짐**.

### A-2. 2회차 — 개별 테스트 (각 경로 30초 간격)

개별 실행 결과:

- `/api/upload` — **프리징(타임아웃)** ← 차단 확정
- `/api/reindex` — 빠른 4xx 응답 (통과)
- `/api/translator/upload` — 빠른 4xx 응답 (통과)
- `/api/compare/upload` — 빠른 4xx 응답 (통과)
- `/api/documents/upload` — 빠른 404 (통과)
- `/api/diag/upload-test` — 200 (대조군, 통과)

→ **차단 대상: `/api/upload` 1개 확정**. 1회차의 다른 경로 타임아웃은 큐 간섭으로 판명.

### A-3. Phase 2 리네이밍 대상

- `/api/upload` → `/api/document-submit` (단일)
- 다른 엔드포인트 변경 불필요

---

## §B. Phase 2 변경 파일 최종 목록 (실행 후 기록)

(Phase 0 결과 + Phase 2-3 grep 결과 반영)

(대기 중)
