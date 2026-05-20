#!/bin/bash
# Plan-45 Phase 7 — 유사도 라벨·공식 일관성 자동 검증
#
# 검증 대상:
#   E1: 카테고리 라벨 SSOT 외 하드코딩 0건 (동일/거의 동일/의역/약한 유사)
#   E3: 축약어 금지 ("유사", "참고", "공통" 단독 사용)
#   Plan-38 옛 어휘 (4그룹/표절 의심/참고 가능/제외 영역) 잔존 0건
#   옛 가중치 공식 (실질 매칭 + 의역·번역 × 0.5) 잔존 0건
#
# 예외 (검사 대상 제외):
#   - data/help/similarity-help.json (SSOT 본체)
#   - contents/guide/verify-guide.html (사용자 가이드, "동일/거의 동일/..." 본문 필요)
#   - workbench/** (계획서·보고서·스크린샷)
#   - tests/sim_phase2_test.js (테스트는 라벨 검증 자체)
#   - .claude/**, node_modules/** (외부)
#
# 사용:
#   bash tests/sim_label_consistency.sh
#
# CI/pre-commit 등록 권장 (CI: yaml step / hook: .git/hooks/pre-commit)

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# 검사 대상 — 유사도 분류 체계가 정의되는 코드 경로만
# js/ 디렉토리는 Translator·Explorer 무관 시스템이라 검사 제외 (false positive 방지)
TARGET_PATHS=(
    "compare.html"
    "css/compare.css"
    "backend/services"
    "backend/api"
)

# 예외 파일 (SSOT·가이드·테스트·문서)
EXCLUDE_PATHS=(
    "data/help/similarity-help.json"
    "contents/guide/verify-guide.html"
    "workbench"
    "tests/sim_label_consistency.sh"
    "tests/sim_phase2_test.js"
    "tests/sim_verdict_band_test.js"
    ".claude"
    "node_modules"
)

EXCLUDE_GREP=""
for p in "${EXCLUDE_PATHS[@]}"; do
    EXCLUDE_GREP+=" --exclude-dir=$(basename "$p") "
done

FAIL=0

# ─────────────────────────────────────────────────────────────
# E3 — Plan-38 옛 유사도 카드 라벨 단독 리터럴 ("일치"·"번역") 금지
# (다른 도메인의 "참고"·"공통"·"유사" 단어는 false positive 다수라 제외 —
#  AI 분류 태그·Translator 시스템 등 무관 영역에서 사용됨)
# 유사도 카드 라벨은 SIM_TYPE_MAP 의 label 필드에서만 SSOT 경유로 설정.
# ─────────────────────────────────────────────────────────────
echo "[E3] 옛 카드 라벨 단독 리터럴 ('일치'·'번역') 검사..."
# 검사는 다음 단계 [E2-legacy] 에서 'label: \'일치\'' 등 정확 패턴으로 수행
echo "  (E2-legacy 단계로 통합 — 'label: ...' 패턴만 정확 검사)"

# ─────────────────────────────────────────────────────────────
# Plan-38 옛 그룹 어휘 — 카드/필터/통계 라벨 잔존 검사
# (계획서·가이드·보고서는 예외)
# ─────────────────────────────────────────────────────────────
echo "[E1-legacy] Plan-38 옛 그룹 어휘 잔존 검사 (4그룹 어휘는 SSOT 외 사용 금지)..."
# "표절 의심" "참고 가능" "제외 영역" — 한 단어로는 false positive 가능 (e.g. "참고문헌").
# 따라서 "참고 가능" 처럼 그룹명 정확 형태만 검사.
for label in "표절 의심" "참고 가능" "제외 영역"; do
    cnt=0
    for tp in "${TARGET_PATHS[@]}"; do
        if [ -e "$tp" ]; then
            c=$(grep -rn --include="*.html" --include="*.js" --include="*.py" \
                $EXCLUDE_GREP \
                -F "$label" "$tp" 2>/dev/null | wc -l || true)
            cnt=$((cnt + c))
        fi
    done
    if [ "$cnt" -gt 0 ]; then
        echo "  FAIL E1-legacy: \"$label\" ${cnt}건 발견 (SSOT 경유 필요)"
        FAIL=1
    fi
done

# ─────────────────────────────────────────────────────────────
# 옛 가중치 공식 잔존 검사 (Plan-38 0.5 가중치)
# ─────────────────────────────────────────────────────────────
echo "[C1-legacy] 옛 가중치 공식 잔존 검사..."
patterns=(
    "실질 매칭 + 의역·번역 × 0.5"
    "× 0.5) / (전체"
    "가중치 ×0.5"
    "가중치 × 0.5"
)
for p in "${patterns[@]}"; do
    cnt=0
    for tp in "${TARGET_PATHS[@]}"; do
        if [ -e "$tp" ]; then
            c=$(grep -rn --include="*.html" --include="*.js" --include="*.py" \
                $EXCLUDE_GREP \
                -F "$p" "$tp" 2>/dev/null | wc -l || true)
            cnt=$((cnt + c))
        fi
    done
    if [ "$cnt" -gt 0 ]; then
        echo "  FAIL C1-legacy: \"$p\" ${cnt}건 발견 (Plan-45 v3 공식만 사용)"
        FAIL=1
    fi
done

# ─────────────────────────────────────────────────────────────
# 옛 카드 라벨 — "일치"·"번역" 단독 라벨 리터럴 잔존 검사
# (compare.html SIM_TYPE_MAP·Modal A SVG는 v3 동기 완료된 상태)
# 카드 렌더에서 'label: \'일치\'' 또는 'label: \'번역\'' 잔존 차단
# ─────────────────────────────────────────────────────────────
echo "[E2-legacy] 옛 카드 라벨 ('일치'/'번역') 리터럴 패턴 검사..."
old_label_patterns=(
    "label: '일치'"
    "label: '번역'"
    "label: \"일치\""
    "label: \"번역\""
)
for p in "${old_label_patterns[@]}"; do
    cnt=0
    for tp in "${TARGET_PATHS[@]}"; do
        if [ -e "$tp" ]; then
            c=$(grep -rn --include="*.html" --include="*.js" --include="*.py" \
                $EXCLUDE_GREP \
                -F "$p" "$tp" 2>/dev/null | wc -l || true)
            cnt=$((cnt + c))
        fi
    done
    if [ "$cnt" -gt 0 ]; then
        echo "  FAIL E2-legacy: $p ${cnt}건 발견 (v3: '동일'/'의역')"
        FAIL=1
    fi
done

# ─────────────────────────────────────────────────────────────
# C2-legacy — Plan-50: 백엔드 옛 가중치 공식 (× 0.5) 잔존 검사
# adjusted_pct = (substantive + derived * 0.5) / effective_total 같은 패턴.
# Plan-45 v3 통일 후 의역 가중치 0.5 는 백엔드에서도 사용 금지.
# ─────────────────────────────────────────────────────────────
echo "[C2-legacy] 백엔드 옛 가중치 공식 잔존 검사..."
backend_old_patterns=(
    "derived * 0.5"
    "+ derived * 0.5"
    "substantive + derived * 0.5"
    "(substantive + derived * 0.5)"
)
for p in "${backend_old_patterns[@]}"; do
    cnt=0
    for tp in "${TARGET_PATHS[@]}"; do
        if [ -e "$tp" ]; then
            c=$(grep -rn --include="*.py" \
                $EXCLUDE_GREP \
                -F "$p" "$tp" 2>/dev/null | wc -l || true)
            cnt=$((cnt + c))
        fi
    done
    if [ "$cnt" -gt 0 ]; then
        echo "  FAIL C2-legacy: \"$p\" ${cnt}건 발견 (Plan-45 v3: 가중치 없음, 의역도 1.0)"
        FAIL=1
    fi
done

# ─────────────────────────────────────────────────────────────
# T1-legacy — Plan-50: 옛 3단계 임계값 (30/60, 40/70) 잔존 검사
# Plan-45 v3 5단계 신호등 (25/49/74) 으로 통일됨.
# verdictBoundLow/High (compare.html), 이력 색상 임계 (40/70) 등이 대상.
# ─────────────────────────────────────────────────────────────
echo "[T1-legacy] 옛 3단계 임계값 잔존 검사..."
threshold_patterns=(
    "verdictBoundLow = 30"
    "verdictBoundHigh = 60"
    "similarity_score >= 70"
    "similarity_score >= 40"
)
for p in "${threshold_patterns[@]}"; do
    cnt=0
    for tp in "${TARGET_PATHS[@]}"; do
        if [ -e "$tp" ]; then
            c=$(grep -rn --include="*.html" --include="*.js" --include="*.py" \
                $EXCLUDE_GREP \
                -F "$p" "$tp" 2>/dev/null | wc -l || true)
            cnt=$((cnt + c))
        fi
    done
    if [ "$cnt" -gt 0 ]; then
        echo "  FAIL T1-legacy: \"$p\" ${cnt}건 발견 (Plan-45 v3 5단계: 25/49/74)"
        FAIL=1
    fi
done

# ─────────────────────────────────────────────────────────────
# T2-band-deadzone — Plan-58: verdict_bands 양방향 비교 안티패턴 금지
# 정수 경계 사이의 소수점 점수 (0.x / 24.x / 49.x / 74.x) 가 red 폴백되는
# 결함이 발생. matchVerdictBand() 헬퍼 사용 필수 (compare.html:2417~).
# ─────────────────────────────────────────────────────────────
echo "[T2-band-deadzone] verdict_bands 양방향 비교 안티패턴 검사..."
# rg-like grep — '>= b.range_min' 와 '<= b.range_max' 가 같은 줄에 공존하면 안티패턴
band_antipatterns=(
    ">= .*\.range_min.*<= .*\.range_max"
    "bands\.find.*range_min.*range_max"
)
for p in "${band_antipatterns[@]}"; do
    cnt=0
    for tp in "${TARGET_PATHS[@]}"; do
        if [ -e "$tp" ]; then
            c=$(grep -rnE --include="*.html" --include="*.js" --include="*.py" \
                $EXCLUDE_GREP \
                "$p" "$tp" 2>/dev/null | wc -l || true)
            cnt=$((cnt + c))
        fi
    done
    if [ "$cnt" -gt 0 ]; then
        echo "  FAIL T2-band-deadzone: \"$p\" ${cnt}건 발견 (Plan-58: matchVerdictBand() 헬퍼 사용)"
        FAIL=1
    fi
done

echo ""
if [ "$FAIL" -eq 0 ]; then
    echo "================================="
    echo "PASS: 모든 라벨·공식 일관성 검증 통과"
    echo "================================="
    exit 0
else
    echo "================================="
    echo "FAIL: 일관성 위반 발견 — 위 항목 수정 필요"
    echo "================================="
    exit 1
fi
