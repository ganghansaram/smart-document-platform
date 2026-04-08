#!/bin/bash
# ── Smart Document Platform: 리눅스 VM 배포 스크립트 ──
# 용도: 첫 설치 + 버전 업데이트 겸용
# 사용: ./deploy.sh [이미지 tar 경로]
#
# 예시:
#   첫 설치:  ./deploy.sh platform-v1.0.tar
#   업데이트: ./deploy.sh platform-v1.1.tar

set -e
cd "$(dirname "$0")"

TAR_FILE="${1:-platform-v1.0.tar}"

# ── 이미지 tar 확인 ──
if [ ! -f "$TAR_FILE" ]; then
    echo "ERROR: 이미지 파일 '$TAR_FILE'을 찾을 수 없습니다."
    echo "사용법: $0 <이미지.tar>"
    exit 1
fi

echo "=== Smart Document Platform 배포 ==="
echo "이미지: $TAR_FILE"
echo ""

# ── 1. Docker 이미지 로드 ──
echo "[1/4] Docker 이미지 로드 중..."
docker load -i "$TAR_FILE"
echo ""

# ── 2. .env 확인 ──
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[2/4] .env 생성됨 (.env.example에서 복사)"
        echo "  → OLLAMA_URL 등을 환경에 맞게 수정하세요."
    else
        echo "[2/4] WARNING: .env 파일 없음 — 기본값으로 실행됩니다."
    fi
else
    echo "[2/4] .env 확인 완료 (기존 설정 유지)"
fi
echo ""

# ── 3. 데이터 디렉토리 생성 ──
echo "[3/4] 데이터 디렉토리 확인..."
mkdir -p data contents models backups logs
echo "  data/ contents/ models/ backups/ logs/ — OK"
echo ""

# ── 4. 서비스 시작 ──
echo "[4/4] 서비스 시작..."
docker compose up -d
echo ""

# ── 5. 이전 이미지 정리 ──
echo "미사용 이미지 정리..."
docker image prune -f 2>/dev/null || true
echo ""

# ── 상태 확인 ──
echo "=== 배포 완료 ==="
docker compose ps
echo ""
PORT_VAL=$(grep '^PORT=' .env 2>/dev/null | cut -d'=' -f2)
echo "접속: http://$(hostname -I | awk '{print $1}'):${PORT_VAL:-80}"
