// Plan-58 단위 테스트 — matchVerdictBand (verdict 5단계 신호등 매칭)
// 실행: node tests/sim_verdict_band_test.js
// compare.html 의 순수 함수를 본 파일에 인라인 복제하여 검증.
// 함수 시그니처·로직이 compare.html 과 동일해야 한다.
// 검증 항목: 정수 경계의 소수점 점수 사각지대 (0.x / 24.x / 49.x / 74.x) + 정상 경계값 + 회귀 영역.

// ─── compare.html 에서 복제한 순수 함수 (compare.html:2417~ 참조) ───
function matchVerdictBand(score, bands) {
    if (!Array.isArray(bands) || !bands.length) return null;
    if (score <= bands[0].range_min) return bands[0];
    for (var i = 1; i < bands.length; i++) {
        var next = bands[i + 1];
        if (!next || score < next.range_min) return bands[i];
    }
    return bands[bands.length - 1];
}

// ─── SSOT data/help/similarity-help.json 의 verdict_bands ───
var BANDS = [
    { color: 'blue',   range_min: 0,  range_max: 0,   label: '매칭 없음' },
    { color: 'green',  range_min: 1,  range_max: 24,  label: '양호' },
    { color: 'yellow', range_min: 25, range_max: 49,  label: '검토 필요' },
    { color: 'orange', range_min: 50, range_max: 74,  label: '상당량 매칭' },
    { color: 'red',    range_min: 75, range_max: 100, label: '위험' }
];

// ─── 백엔드 _compute_verdict_band() 와 동일 로직 (정합성 검증용) ───
// backend/services/similarity_engine.py:_compute_verdict_band 참조.
function backendCompute(score) {
    var th = [0, 25, 50, 75];
    if (score <= th[0]) return 'blue';
    if (score < th[1]) return 'green';
    if (score < th[2]) return 'yellow';
    if (score < th[3]) return 'orange';
    return 'red';
}

// ─── 테스트 유틸 (process.stdout.write 사용 — hook 규칙 준수) ───
var out = process.stdout;
var pass = 0, fail = 0, failures = [];

function assert(id, desc, actual, expected) {
    var ok = JSON.stringify(actual) === JSON.stringify(expected);
    if (ok) {
        pass++;
        out.write('  OK ' + id + ' ' + desc + '\n');
    } else {
        fail++;
        failures.push({ id: id, desc: desc, expected: expected, actual: actual });
        out.write('  FAIL ' + id + ' ' + desc + '\n');
        out.write('    expected: ' + JSON.stringify(expected) + '\n');
        out.write('    actual:   ' + JSON.stringify(actual) + '\n');
    }
}

out.write('\n=== Plan-58 단위 테스트 — matchVerdictBand ===\n\n');

// ─── V1~V4: 사각지대 점수 (이전에 모두 red 폴백되던 케이스) ───
out.write('[사각지대 점수 — 정수 경계 사이의 소수점]\n');
assert('V1', 'score=0.4  -> green (이전: red 폴백)',
    matchVerdictBand(0.4, BANDS).color, 'green');
assert('V2', 'score=0.9  -> green (사용자 보고 케이스)',
    matchVerdictBand(0.9, BANDS).color, 'green');
assert('V3', 'score=24.5 -> green (24<s<25 구간)',
    matchVerdictBand(24.5, BANDS).color, 'green');
assert('V4', 'score=24.9 -> green',
    matchVerdictBand(24.9, BANDS).color, 'green');
assert('V5', 'score=49.9 -> yellow (49<s<50 구간)',
    matchVerdictBand(49.9, BANDS).color, 'yellow');
assert('V6', 'score=74.9 -> orange (74<s<75 구간)',
    matchVerdictBand(74.9, BANDS).color, 'orange');

// ─── V7~V12: 정수 경계값 (회귀 영역, 이전에도 정상이던 케이스) ───
out.write('\n[정수 경계값 — 회귀 영역]\n');
assert('V7',  'score=0    -> blue  (매칭 없음)',
    matchVerdictBand(0, BANDS).color, 'blue');
assert('V8',  'score=1    -> green',
    matchVerdictBand(1, BANDS).color, 'green');
assert('V9',  'score=24   -> green',
    matchVerdictBand(24, BANDS).color, 'green');
assert('V10', 'score=25   -> yellow',
    matchVerdictBand(25, BANDS).color, 'yellow');
assert('V11', 'score=50   -> orange',
    matchVerdictBand(50, BANDS).color, 'orange');
assert('V12', 'score=75   -> red',
    matchVerdictBand(75, BANDS).color, 'red');

// ─── V13~V15: 정상 점수 (전형적 사용자 시나리오) ───
out.write('\n[정상 점수 시나리오]\n');
assert('V13', 'score=1.7  -> green',
    matchVerdictBand(1.7, BANDS).color, 'green');
assert('V14', 'score=12.5 -> green',
    matchVerdictBand(12.5, BANDS).color, 'green');
assert('V15', 'score=99.9 -> red',
    matchVerdictBand(99.9, BANDS).color, 'red');

// ─── V16~V18: 극단값 + 빈 입력 ───
out.write('\n[극단값·방어 로직]\n');
assert('V16', 'score=100 -> red (상한)',
    matchVerdictBand(100, BANDS).color, 'red');
assert('V17', 'bands=[] -> null (빈 입력 방어)',
    matchVerdictBand(50, []), null);
assert('V18', 'bands=null -> null (방어)',
    matchVerdictBand(50, null), null);

// ─── V19~V36: 백엔드 _compute_verdict_band() 와 전수 정합 검증 ───
out.write('\n[백엔드 _compute_verdict_band() 정합 검증]\n');
var crossCases = [0, 0.1, 0.4, 0.9, 1, 1.0, 12.5, 24, 24.1, 24.5, 24.9, 25, 49, 49.9, 50, 74, 74.9, 75, 100];
for (var i = 0; i < crossCases.length; i++) {
    var s = crossCases[i];
    var fe = matchVerdictBand(s, BANDS).color;
    var be = backendCompute(s);
    assert('V19+' + i, 'score=' + s + ' frontend=' + fe + ' backend=' + be, fe, be);
}

// ─── 결과 출력 ───
out.write('\n=== 결과: ' + pass + ' pass, ' + fail + ' fail ===\n\n');
if (fail > 0) {
    out.write('실패 상세:\n');
    failures.forEach(function(f) {
        out.write('  ' + f.id + ' ' + f.desc + '\n');
        out.write('    expected=' + JSON.stringify(f.expected) + ' actual=' + JSON.stringify(f.actual) + '\n');
    });
    process.exit(1);
} else {
    process.exit(0);
}
