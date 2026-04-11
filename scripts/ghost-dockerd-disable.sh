#!/bin/bash
# ── 유령 dockerd 안전 중지 + 비활성화 스크립트 ──
# 용도: WSL2 네이티브 dockerd와 그 안의 유령 컨테이너들을 정지/비활성화
# 실행: sudo bash scripts/ghost-dockerd-disable.sh
# 전제: scripts/ghost-dockerd-snapshot.sh로 스냅샷 수집 완료
#
# 동작:
#   1. 정체 확인 (컨테이너 config 조회)
#   2. systemd docker.service / docker.socket 중지
#   3. 부팅 자동 시작 해제
#   4. 검증 (port 80 해제 확인, PID 사라짐 확인)
#
# 주의: Docker Desktop은 전혀 영향받지 않음

set +e  # 일부 실패해도 계속 진행

CONTAINERS_DIR=/var/lib/docker/containers

echo "=============================================="
echo "  유령 dockerd 중지 스크립트"
echo "=============================================="
echo ""

# ─────────────────────────────────────────────
# Step 1: 컨테이너 정체 확인
# ─────────────────────────────────────────────
echo "[Step 1] 정체 확인 — 컨테이너 3개의 이미지/상태"
echo ""

for CID in $(ls "$CONTAINERS_DIR" 2>/dev/null); do
    CFG="$CONTAINERS_DIR/$CID/config.v2.json"
    if [ -f "$CFG" ]; then
        SHORT_ID="${CID:0:12}"
        IMG=$(python3 -c "import json; d=json.load(open('$CFG')); print(d.get('Config',{}).get('Image','?'))" 2>/dev/null)
        NAME=$(python3 -c "import json; d=json.load(open('$CFG')); print(d.get('Name','?').lstrip('/'))" 2>/dev/null)
        STATE=$(python3 -c "import json; d=json.load(open('$CFG')); print(d.get('State',{}).get('Running','?'))" 2>/dev/null)
        echo "  [$SHORT_ID] name='$NAME' image='$IMG' running=$STATE"
    fi
done

echo ""
echo "[Step 1] 완료 — 위 컨테이너 전부가 중지됩니다."
echo ""

# ─────────────────────────────────────────────
# Step 2: systemd 중지
# ─────────────────────────────────────────────
echo "[Step 2] docker.service + docker.socket 중지"

systemctl stop docker.service docker.socket 2>&1
SLEEP_OK=0
for i in $(seq 1 10); do
    STATE=$(systemctl is-active docker.service 2>&1)
    if [ "$STATE" != "active" ]; then
        SLEEP_OK=1
        break
    fi
    sleep 1
done

if [ "$SLEEP_OK" -eq 1 ]; then
    echo "  ✓ docker.service 중지 확인 (상태: $(systemctl is-active docker.service 2>&1))"
else
    echo "  ✗ 중지 실패 — docker.service 상태: $(systemctl is-active docker.service 2>&1)"
fi
echo ""

# ─────────────────────────────────────────────
# Step 3: 부팅 자동 시작 해제
# ─────────────────────────────────────────────
echo "[Step 3] 부팅 자동 시작 해제 (disable)"

systemctl disable docker.service docker.socket 2>&1 | tail -5
echo "  ✓ disable 완료"
echo ""

# ─────────────────────────────────────────────
# Step 4: 검증
# ─────────────────────────────────────────────
echo "[Step 4] 검증"
echo ""

echo "  (a) docker.service 상태: $(systemctl is-active docker.service 2>&1)"
echo "  (b) docker.service enabled: $(systemctl is-enabled docker.service 2>&1)"
echo "  (c) docker.socket 상태: $(systemctl is-active docker.socket 2>&1)"
echo ""

echo "  (d) dockerd 프로세스 존재 여부:"
DOCKERD_COUNT=$(pgrep -c dockerd 2>&1)
if [ "$DOCKERD_COUNT" -gt 0 ]; then
    echo "      ⚠ dockerd 프로세스 $DOCKERD_COUNT개 남아있음:"
    pgrep -la dockerd 2>&1 | sed 's/^/        /'
else
    echo "      ✓ dockerd 프로세스 없음"
fi
echo ""

echo "  (e) 유령 nginx (PID 672) 존재 여부:"
if [ -d /proc/672 ]; then
    echo "      ⚠ PID 672 아직 존재: $(ps -p 672 -o cmd= 2>&1)"
else
    echo "      ✓ PID 672 사라짐 (유령 nginx 정지)"
fi
echo ""

echo "  (f) 모든 nginx 프로세스:"
NGINX_PROCS=$(ps aux 2>&1 | grep -E '[n]ginx: master' | wc -l)
echo "      nginx master 개수: $NGINX_PROCS"
ps aux 2>&1 | grep -E '[n]ginx: master' | sed 's/^/        /'
echo ""

echo "  (g) port 80 리스너:"
ss -tlnp 2>&1 | grep ":80 " | sed 's/^/      /' || echo "      (없음 — port 80 완전 해제됨)"
echo ""

echo "=============================================="
echo "  완료"
echo "=============================================="
echo ""
echo "다음 단계: 사용자 쉘에서 아래 명령 실행"
echo "  cd /mnt/c/AHS_Proj/smart-document-platform"
echo "  docker compose down && docker compose up -d"
echo ""
echo "이 명령으로 Docker Desktop의 sdp-nginx가 port 80을 새로 바인딩합니다."
