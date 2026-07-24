# 쓰레기 데이터 정리 가이드 — 휴지통 · 백업 (회사 리눅스 VM)

대상: `data/trash/` (삭제된 문서 보관), `backups/*.bak` (업로드·편집 시 자동 백업).
둘 다 무기한 누적됨. v2.12부터 **재시작 시 자동정리**(30일 초과 휴지통 + 파일당 5개 초과 백업).
아래는 **누적분을 지금 즉시 비우는** 수동 절차.

> 경로 전제: 모든 명령은 **배포 디렉토리**에서 실행. `data/`·`backups/`는 호스트 bind mount(기본 `./data`, `./backups`).

---

## STEP 0. 배포 디렉토리로 이동
```bash
cd ~/smart-document-platform          # 실제 배포 경로로 교체
```
확인:
```bash
ls docker-compose.yml deploy.sh       # 이 파일들이 보이면 올바른 위치
```

> ⚠️ `.env`에 `DATA_DIR`·`BACKUPS_DIR`를 커스텀 지정했다면 그 경로 사용. 확인:
> `grep -E 'DATA_DIR|BACKUPS_DIR' .env` — 출력 없으면 기본 `./data`, `./backups`.

---

## STEP 1. 현재 용량·개수 확인 (지우기 전)
```bash
du -sh data/trash backups 2>/dev/null
echo "휴지통 폴더: $(ls -1 data/trash 2>/dev/null | wc -l) / 백업 파일: $(ls -1 backups 2>/dev/null | wc -l)"
```
→ 숫자와 용량을 눈으로 확인.

---

## STEP 2. (선택) 지우기 전 안전 백업
```bash
tar -czf ~/trash-backup-$(date +%Y%m%d).tar.gz data/trash backups 2>/dev/null
ls -lh ~/trash-backup-*.tar.gz        # 생성 확인
```
> 완전히 확신하면 이 단계는 건너뛰어도 됨 (휴지통·백업 자체가 이미 복구본).

---

## STEP 3. 비우기
```bash
rm -rf data/trash/* backups/*
```

---

## STEP 4. 확인 (둘 다 0 이어야 함)
```bash
echo "휴지통: $(ls -1 data/trash 2>/dev/null | wc -l) / 백업: $(ls -1 backups 2>/dev/null | wc -l)"
```
→ `휴지통: 0 / 백업: 0` 나오면 완료.

---

## (대안) data/가 호스트에 안 보일 때 — 컨테이너 내부에서
STEP 1~4가 "No such file"이면 볼륨이 호스트 bind가 아닌 경우. 컨테이너 안에서 실행:
```bash
# 확인
docker compose exec backend sh -c 'du -sh data/trash backups 2>/dev/null'
# 비우기
docker compose exec backend sh -c 'rm -rf data/trash/* backups/* && echo done'
```

---

## (선택) STEP 5. 구버전 삭제 잔재로 검색에 유령 문서가 있으면
휴지통 정리와 무관하게, 옛 버전에서 삭제된 문서가 검색에 남아 있으면 인덱스 재정합:
1. 브라우저로 접속 → **admin 계정 로그인**
2. 관리자 설정 → **재인덱스**(reindex) 1회 실행
3. Explorer 검색에서 삭제된 문서가 더 이상 안 뜨는지 확인

---

## 이후 자동화 (v2.12부터)
- 이번 정리 후에는 **재시작할 때마다** 자동으로:
  - 휴지통 = 30일 지난 것 삭제
  - 백업 = 문서당 최근 5개만 유지
- 즉 STEP 1~4는 **지금 한 번만** 하면 되고, 앞으로는 알아서 한도가 잡힘.
- 자동정리 동작 확인:
  ```bash
  docker compose logs backend | grep 보존정리
  ```
