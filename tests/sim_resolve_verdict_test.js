// Plan-59 단위 테스트 — resolveVerdict + verdict_legacy 5단계→3단계 매핑
// 실행: node tests/sim_resolve_verdict_test.js
// compare.html 의 순수 함수를 본 파일에 인라인 복제하여 검증.

// ─── compare.html 에서 복제한 순수 함수 (compare.html:2417~, :2429~ 참조) ───
function matchVerdictBand(score, bands) {
    if (!Array.isArray(bands) || !bands.length) return null;
    if (score <= bands[0].range_min) return bands[0];
    for (var i = 1; i < bands.length; i++) {
        var next = bands[i + 1];
        if (!next || score < next.range_min) return bands[i];
    }
    return bands[bands.length - 1];
}

var BANDS = [
    { color: 'blue',   range_min: 0,  range_max: 0,   label: '매칭 없음',    meaning: '완전 독창' },
    { color: 'green',  range_min: 1,  range_max: 24,  label: '양호',         meaning: '정상' },
    { color: 'yellow', range_min: 25, range_max: 49,  label: '검토 필요',    meaning: '점검' },
    { color: 'orange', range_min: 50, range_max: 74,  label: '상당량 매칭',  meaning: '재작성 권고' },
    { color: 'red',    range_min: 75, range_max: 100, label: '위험',         meaning: '본격 검토' }
];

// resolveVerdict 의 simHelp 의존성을 인자로 단순화한 테스트 버전.
// (실제 compare.html 에서는 simHelp 전역 변수에서 verdict_bands 를 가져옴)
function resolveVerdictForTest(score, bands, verdictBoundLow, verdictBoundHigh) {
    var match = bands ? matchVerdictBand(score, bands) : null;
    if (match) {
        var classMap = { blue: 'sim-verdict-blue', green: 'sim-verdict-good', yellow: 'sim-verdict-yellow', orange: 'sim-verdict-orange', red: 'sim-verdict-warning' };
        return {
            label: match.label,
            cls:   classMap[match.color] || 'sim-verdict-moderate',
            tip:   '유사율 ' + match.range_min + (match.range_min === match.range_max ? '%' : '~' + match.range_max + '%') + ' — ' + (match.meaning || '')
        };
    }
    if (score >= verdictBoundHigh) return { label: '위험',      cls: 'sim-verdict-warning',  tip: '유사율 ' + verdictBoundHigh + '% 이상' };
    if (score >= verdictBoundLow)  return { label: '검토 필요', cls: 'sim-verdict-moderate', tip: '유사율 ' + verdictBoundLow + '~' + verdictBoundHigh + '% 구간' };
    return                                { label: '양호',      cls: 'sim-verdict-good',     tip: '유사율 ' + verdictBoundLow + '% 미만' };
}

// verdict_legacy 5단계→3단계 매핑 (compare.html:5328~ 참조)
function resolveVerdictLegacy(score, bands, verdictBoundLow, verdictBoundHigh) {
    var matchBand = bands ? matchVerdictBand(score, bands) : null;
    var legacyMap = { blue: '양호', green: '양호', yellow: '검토 필요', orange: '검토 필요', red: '위험' };
    return matchBand
        ? (legacyMap[matchBand.color] || '양호')
        : (score >= verdictBoundHigh ? '위험' : (score >= verdictBoundLow ? '검토 필요' : '양호'));
}

// ─── 테스트 유틸 ───
var out = process.stdout;
var pass = 0, fail = 0;

function assert(id, desc, actual, expected) {
    var ok = JSON.stringify(actual) === JSON.stringify(expected);
    if (ok) { pass++; out.write('  OK ' + id + ' ' + desc + '\n'); }
    else {
        fail++;
        out.write('  FAIL ' + id + ' ' + desc + '\n');
        out.write('    expected: ' + JSON.stringify(expected) + '\n');
        out.write('    actual:   ' + JSON.stringify(actual) + '\n');
    }
}

out.write('\n=== Plan-59 단위 테스트 — resolveVerdict + verdict_legacy ===\n\n');

// ─── R1~R6: resolveVerdict — SSOT 경로 (Plan-58 사각지대 검증 재확인) ───
out.write('[resolveVerdict — SSOT 경로]\n');
assert('R1', 'score=0   -> blue/매칭 없음',
    resolveVerdictForTest(0, BANDS, 25, 74).cls, 'sim-verdict-blue');
assert('R2', 'score=0.9 -> good/양호 (사각지대 정상화)',
    resolveVerdictForTest(0.9, BANDS, 25, 74).cls, 'sim-verdict-good');
assert('R3', 'score=12.5 -> good/양호',
    resolveVerdictForTest(12.5, BANDS, 25, 74).cls, 'sim-verdict-good');
assert('R4', 'score=49.9 -> yellow/검토 필요 (사각지대)',
    resolveVerdictForTest(49.9, BANDS, 25, 74).cls, 'sim-verdict-yellow');
assert('R5', 'score=74.5 -> orange/상당량 매칭 (백엔드 75 미만)',
    resolveVerdictForTest(74.5, BANDS, 25, 74).cls, 'sim-verdict-orange');
assert('R6', 'score=75 -> warning/위험',
    resolveVerdictForTest(75, BANDS, 25, 74).cls, 'sim-verdict-warning');

// ─── R7~R9: resolveVerdict — fallback 경로 (simHelp 미로드) ───
out.write('\n[resolveVerdict — fallback 경로 (simHelp 미로드, 25/74)]\n');
assert('R7', 'fallback score=10 -> good/양호',
    resolveVerdictForTest(10, null, 25, 74).label, '양호');
assert('R8', 'fallback score=50 -> moderate/검토 필요',
    resolveVerdictForTest(50, null, 25, 74).label, '검토 필요');
assert('R9', 'fallback score=80 -> warning/위험',
    resolveVerdictForTest(80, null, 25, 74).label, '위험');

// ─── R10~R15: 라벨 + 색 + 툴팁 통합 검증 ───
out.write('\n[라벨 + 색 + 툴팁 통합 검증]\n');
var v1 = resolveVerdictForTest(0.9, BANDS, 25, 74);
assert('R10', 'score=0.9 label=양호 (사용자 보고 케이스)', v1.label, '양호');
assert('R11', 'score=0.9 cls=sim-verdict-good', v1.cls, 'sim-verdict-good');
assert('R12', 'score=0.9 tip 시작이 "유사율 1~24%"', v1.tip.startsWith('유사율 1~24%'), true);
var v2 = resolveVerdictForTest(75, BANDS, 25, 74);
assert('R13', 'score=75 label=위험', v2.label, '위험');
assert('R14', 'score=75 cls=sim-verdict-warning', v2.cls, 'sim-verdict-warning');
assert('R15', 'score=75 tip 시작이 "유사율 75~100%"', v2.tip.startsWith('유사율 75~100%'), true);

// ─── L1~L7: verdict_legacy 5단계→3단계 매핑 (F-58-1) ───
out.write('\n[verdict_legacy 5→3 매핑 (F-58-1: 백엔드 75 정합)]\n');
assert('L1', 'score=0 -> 양호 (blue→양호)',
    resolveVerdictLegacy(0, BANDS, 25, 74), '양호');
assert('L2', 'score=0.9 -> 양호 (green→양호)',
    resolveVerdictLegacy(0.9, BANDS, 25, 74), '양호');
assert('L3', 'score=25 -> 검토 필요 (yellow→검토 필요)',
    resolveVerdictLegacy(25, BANDS, 25, 74), '검토 필요');
assert('L4', 'score=49.9 -> 검토 필요 (yellow→검토 필요)',
    resolveVerdictLegacy(49.9, BANDS, 25, 74), '검토 필요');
assert('L5', 'score=50 -> 검토 필요 (orange→검토 필요)',
    resolveVerdictLegacy(50, BANDS, 25, 74), '검토 필요');
assert('L6', 'score=74.5 -> 검토 필요 (orange→검토 필요) ★ 옛 코드는 "위험"으로 1 off',
    resolveVerdictLegacy(74.5, BANDS, 25, 74), '검토 필요');
assert('L7', 'score=75 -> 위험 (red→위험)',
    resolveVerdictLegacy(75, BANDS, 25, 74), '위험');

// ─── L8~L10: verdict_legacy fallback 경로 (simHelp 미로드) ───
out.write('\n[verdict_legacy fallback 경로]\n');
assert('L8', 'fallback score=10 -> 양호',
    resolveVerdictLegacy(10, null, 25, 74), '양호');
assert('L9', 'fallback score=50 -> 검토 필요',
    resolveVerdictLegacy(50, null, 25, 74), '검토 필요');
assert('L10', 'fallback score=80 -> 위험',
    resolveVerdictLegacy(80, null, 25, 74), '위험');

// ─── 결과 ───
out.write('\n=== 결과: ' + pass + ' pass, ' + fail + ' fail ===\n\n');
process.exit(fail > 0 ? 1 : 0);
