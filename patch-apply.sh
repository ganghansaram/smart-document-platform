#!/bin/bash
# ── Smart Document Platform: 코드 패치 적용 스크립트 ──
# 용도: 전체 이미지 교체 없이 변경된 코드만 컨테이너에 적용
# 사용: ./patch-apply.sh patch-v1.0.1.tar.gz
#
# 전제: deploy.sh로 최초 설치가 완료된 환경

set -e
cd "$(dirname "$0")"

PATCH_FILE="${1}"

if [ -z "$PATCH_FILE" ] || [ ! -f "$PATCH_FILE" ]; then
    echo "ERROR: 패치 파일을 지정하세요."
    echo "사용법: $0 <patch-vX.X.X.tar.gz>"
    exit 1
fi

echo "=== Smart Document Platform 패치 적용 ==="
echo "패치: $PATCH_FILE"
echo ""

# ── 1. 패치 압축 해제 ──
PATCH_DIR=$(mktemp -d)
echo "[1/4] 패치 압축 해제..."
tar -xzf "$PATCH_FILE" -C "$PATCH_DIR"
echo ""

# ── 2. 매니페스트 확인 ──
if [ ! -f "$PATCH_DIR/MANIFEST" ]; then
    echo "ERROR: MANIFEST 파일이 없습니다. 유효한 패치 파일인지 확인하세요."
    rm -rf "$PATCH_DIR"
    exit 1
fi

echo "[2/4] 패치 내용:"
cat "$PATCH_DIR/MANIFEST"
echo ""

# ── 3. 컨테이너에 파일 복사 ──
echo "[3/4] 컨테이너에 패치 적용..."

# 백엔드 파일
if [ -d "$PATCH_DIR/backend" ]; then
    echo "  → sdp-backend: backend/ 코드 업데이트"
    docker cp "$PATCH_DIR/backend/." sdp-backend:/app/backend/
fi

# 프론트엔드 파일 (nginx 컨테이너)
if [ -d "$PATCH_DIR/frontend" ]; then
    echo "  → sdp-nginx: 프론트엔드 코드 업데이트"
    # nginx 컨테이너의 프론트엔드 경로에 복사
    for item in "$PATCH_DIR/frontend/"*; do
        name=$(basename "$item")
        docker cp "$item" "sdp-nginx:/app/frontend/$name"
    done
fi

# tools 파일 (백엔드 컨테이너)
if [ -d "$PATCH_DIR/tools" ]; then
    echo "  → sdp-backend: tools/ 업데이트"
    docker cp "$PATCH_DIR/tools/." sdp-backend:/app/tools/
fi

# Docker 설정 파일 (nginx.conf 등)
if [ -f "$PATCH_DIR/docker/nginx.conf" ]; then
    echo "  → sdp-nginx: nginx.conf 업데이트"
    docker cp "$PATCH_DIR/docker/nginx.conf" sdp-nginx:/etc/nginx/nginx.conf
fi
if [ -f "$PATCH_DIR/docker/config.docker.js" ]; then
    echo "  → sdp-nginx: config.docker.js 업데이트"
    docker cp "$PATCH_DIR/docker/config.docker.js" sdp-nginx:/app/frontend/js/config.js
fi

echo ""

# ── 4. 컨테이너 재시작 ──
echo "[4/4] 컨테이너 재시작..."
docker restart sdp-backend sdp-nginx
echo ""

# ── 정리 + 상태 확인 ──
rm -rf "$PATCH_DIR"

# 헬스체크 대기
echo "헬스체크 대기 중..."
for i in $(seq 1 15); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' sdp-backend 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "healthy" ]; then
        break
    fi
    sleep 2
done

echo ""
echo "=== 패치 적용 완료 ==="
docker compose ps
echo ""

# 이전 이미지 정리
echo "미사용 이미지 정리..."
docker image prune -f 2>/dev/null || true
echo ""

PORT_VAL=$(grep '^PORT=' .env 2>/dev/null | cut -d'=' -f2)
echo "접속: http://$(hostname -I | awk '{print $1}'):${PORT_VAL:-80}"
