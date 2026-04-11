#!/bin/bash
# ── 유령 dockerd 스냅샷 수집 스크립트 ──
# 용도: WSL2 네이티브 dockerd를 중지하기 전에 현재 상태를 기록
# 실행: sudo bash scripts/ghost-dockerd-snapshot.sh
# 출력: /tmp/ghost-dockerd-snapshot/snapshot.txt

set +e  # 일부 명령 실패해도 계속 진행
OUT_DIR=/tmp/ghost-dockerd-snapshot
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/snapshot.txt"

{
    echo "=== 수집 시각 ==="
    date

    echo ""
    echo "=== 1. systemd docker.service MainPID ==="
    systemctl show docker.service -p MainPID -p ActiveState -p SubState

    echo ""
    echo "=== 2. dockerd process info ==="
    MAIN_PID=$(systemctl show docker.service -p MainPID --value)
    if [ -n "$MAIN_PID" ] && [ "$MAIN_PID" != "0" ]; then
        ps -p "$MAIN_PID" -o pid,ppid,user,cmd
    else
        echo "MainPID not found"
    fi

    echo ""
    echo "=== 3. nginx master (PID 672) cgroup & process ==="
    if [ -d /proc/672 ]; then
        cat /proc/672/cgroup
        ps -p 672 -o pid,ppid,user,cmd
    else
        echo "PID 672 not found"
    fi

    echo ""
    echo "=== 4. docker sockets ==="
    ls -la /run/docker.sock /var/run/docker.sock 2>&1

    echo ""
    echo "=== 5. port 80 listener (ss -tlnp) ==="
    ss -tlnp 2>&1 | grep ":80 "

    echo ""
    echo "=== 6. current default docker (via /var/run/docker.sock) ==="
    docker ps -a 2>&1

    echo ""
    echo "=== 7. docker containers on disk (/var/lib/docker/containers) ==="
    ls -la /var/lib/docker/containers/ 2>&1 | head -30

    echo ""
    echo "=== 8. docker images on disk (/var/lib/docker/image/overlay2/repositories.json) ==="
    cat /var/lib/docker/image/overlay2/repositories.json 2>&1 | head -30

    echo ""
    echo "=== 9. containerd containers (if accessible) ==="
    ctr -n moby containers list 2>&1 || echo "ctr not available or no permission"

    echo ""
    echo "=== 10. All nginx processes on host ==="
    ps aux 2>&1 | grep -E '[n]ginx' | head -10

    echo ""
    echo "=== 11. dockerd command line ==="
    if [ -n "$MAIN_PID" ] && [ "$MAIN_PID" != "0" ] && [ -f "/proc/$MAIN_PID/cmdline" ]; then
        tr '\0' ' ' < "/proc/$MAIN_PID/cmdline"
        echo ""
    fi

    echo ""
    echo "=== 수집 완료 ==="
} > "$OUT" 2>&1

chmod 644 "$OUT"
echo "스냅샷 저장: $OUT"
echo ""
cat "$OUT"
