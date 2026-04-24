// Plan-45 Phase 2 단위 테스트 — resolveCategory + computeScore
// 실행: node tests/sim_phase2_test.js
// compare.html 의 순수 함수를 본 파일에 인라인 복제하여 검증.
// 함수 시그니처·로직이 compare.html 과 동일해야 한다.

// ─── compare.html 에서 복제한 순수 함수 (compare.html:1391~ 및 2374~ 참조) ───
var SIM_EXCL_TO_KEY = {
    boilerplate:         'exclude_boilerplate',
    boilerplate_pattern: 'exclude_boilerplate',
    short_match:         'exclude_short_match',
    toc_heading:         'exclude_toc',
    caption:             'exclude_caption',
    cited_quote:         'exclude_cited_quote'
};
var SIM_AUTO_EXCLUDED = ['references_section', 'spec_number_only'];

function simIsActiveExclusion(reason, settings) {
    if (!reason) return false;
    if (SIM_AUTO_EXCLUDED.indexOf(reason) >= 0) return true;
    var key = SIM_EXCL_TO_KEY[reason];
    return key && settings[key] === true;
}

var SIM_TYPE_TO_CATEGORY = {
    identical:   'identical',
    near_copy:   'near_copy',
    paraphrase:  'paraphrased',
    translation: 'paraphrased',
    low_sim:     'low_similarity'
};

function resolveCategory(match, settings) {
    if (!match) return null;
    if (match.user_excluded) return 'excluded_manual';
    if (match.type === 'boilerplate') return 'excluded_auto';
    if (simIsActiveExclusion(match.exclusion_reason, settings)) return 'excluded_auto';
    return SIM_TYPE_TO_CATEGORY[match.type] || 'low_similarity';
}

function computeScore(matches, totalSentences, settings) {
    var counts = { identical: 0, near_copy: 0, paraphrased: 0, low_similarity: 0 };
    var excluded = 0;
    for (var i = 0; i < matches.length; i++) {
        var m = matches[i];
        var cat = resolveCategory(m, settings);
        var span = (m.target_idx_end !== undefined ? m.target_idx_end : m.target_idx) - m.target_idx + 1;
        if (cat === 'excluded_auto' || cat === 'excluded_manual') {
            excluded += span;
        } else if (counts[cat] !== undefined) {
            counts[cat] += span;
        }
    }
    var scored = counts.identical + counts.near_copy + counts.paraphrased;
    var denominator = Math.max(totalSentences - excluded, 1);
    var score = Math.min(100, Math.round(scored / denominator * 1000) / 10);
    return { score: score, counts: counts, excluded: excluded, totalSentences: totalSentences };
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

var DEFAULT_SETTINGS = {
    exclude_boilerplate: true,
    exclude_short_match: true,
    exclude_toc: true,
    exclude_caption: true,
    exclude_cited_quote: false
};

function m(type, opts) {
    opts = opts || {};
    return {
        type: type,
        target_idx: opts.target_idx !== undefined ? opts.target_idx : 0,
        target_idx_end: opts.target_idx_end,
        exclusion_reason: opts.exclusion_reason || null,
        user_excluded: !!opts.user_excluded
    };
}

out.write('\n=== Plan-45 Phase 2 단위 테스트 (U1~U10) ===\n\n');

// ─── U1~U6: resolveCategory 기본 유형 → 카테고리 매핑 ───
out.write('[resolveCategory 기본 유형 매핑]\n');
assert('U1', 'type=identical  -> identical',
    resolveCategory(m('identical'), DEFAULT_SETTINGS), 'identical');
assert('U2', 'type=near_copy  -> near_copy',
    resolveCategory(m('near_copy'), DEFAULT_SETTINGS), 'near_copy');
assert('U3', 'type=paraphrase -> paraphrased',
    resolveCategory(m('paraphrase'), DEFAULT_SETTINGS), 'paraphrased');
assert('U4', 'type=translation -> paraphrased (통합)',
    resolveCategory(m('translation'), DEFAULT_SETTINGS), 'paraphrased');
assert('U5', 'type=low_sim    -> low_similarity',
    resolveCategory(m('low_sim'), DEFAULT_SETTINGS), 'low_similarity');
assert('U6', 'type=boilerplate -> excluded_auto (항상)',
    resolveCategory(m('boilerplate'), DEFAULT_SETTINGS), 'excluded_auto');

// ─── U7~U9: 자동/수동 제외 로직 ───
out.write('\n[자동 제외 + 수동 제외 우선순위]\n');
assert('U7', 'exclusion_reason=toc_heading + exclude_toc=true  -> excluded_auto',
    resolveCategory(m('near_copy', { exclusion_reason: 'toc_heading' }), DEFAULT_SETTINGS), 'excluded_auto');
assert('U8', 'exclusion_reason=toc_heading + exclude_toc=false -> near_copy (원래 카테고리)',
    resolveCategory(m('near_copy', { exclusion_reason: 'toc_heading' }),
        Object.assign({}, DEFAULT_SETTINGS, { exclude_toc: false })), 'near_copy');
assert('U9', 'user_excluded=true + type=identical -> excluded_manual (최우선)',
    resolveCategory(m('identical', { user_excluded: true }), DEFAULT_SETTINGS), 'excluded_manual');

// ─── U10: computeScore — Copyleaks 공식 검증 (가중치 없음) ───
out.write('\n[computeScore — Copyleaks aggregatedScore 공식]\n');

// 시나리오 1: Copyleaks 샘플 값과 구조 동일
// 동일 76 + 거의 동일 50 + 의역 89, 전체 597, 자동 제외 105 → 43.7%
var matches1 = [];
for (var i = 0; i < 76;  i++) matches1.push(m('identical',   { target_idx: i }));
for (var i = 0; i < 50;  i++) matches1.push(m('near_copy',   { target_idx: 100 + i }));
for (var i = 0; i < 89;  i++) matches1.push(m('paraphrase',  { target_idx: 200 + i }));
for (var i = 0; i < 105; i++) matches1.push(m('identical',   { target_idx: 400 + i, exclusion_reason: 'references_section' }));

var r1 = computeScore(matches1, 597, DEFAULT_SETTINGS);
assert('U10-a', 'Copyleaks 샘플: (76+50+89)/(597-105) = 43.7%', r1.score, 43.7);
assert('U10-b', '  counts.identical = 76', r1.counts.identical, 76);
assert('U10-c', '  counts.near_copy = 50', r1.counts.near_copy, 50);
assert('U10-d', '  counts.paraphrased = 89', r1.counts.paraphrased, 89);
assert('U10-e', '  excluded = 105', r1.excluded, 105);

// 시나리오 2: low_sim 점수 제외 검증 (C3 불변)
var matches2 = [m('identical', {target_idx:0}), m('low_sim', {target_idx:1}), m('low_sim', {target_idx:2})];
var r2 = computeScore(matches2, 10, DEFAULT_SETTINGS);
assert('U10-f', 'low_sim 점수 제외: 1/(10-0)=10.0%', r2.score, 10.0);
assert('U10-g', '  low_sim 카운트는 유지 (통계용)', r2.counts.low_similarity, 2);

// 시나리오 3: 가중치 없음 (Plan-38 구공식 대비 검증)
var matches3 = [
    m('identical',  {target_idx:0}), m('identical',  {target_idx:1}),
    m('paraphrase', {target_idx:2}), m('paraphrase', {target_idx:3})
];
var r3 = computeScore(matches3, 10, DEFAULT_SETTINGS);
assert('U10-h', '가중치 없음: (2 identical + 2 paraphrased) / 10 = 40.0% (구공식은 30%)', r3.score, 40.0);

// 시나리오 4: 수동 제외가 분모에서 차감되는지 (C4)
var matches4 = [
    m('identical', {target_idx:0}),
    m('identical', {target_idx:1, user_excluded: true}),
    m('identical', {target_idx:2, user_excluded: true})
];
var r4 = computeScore(matches4, 10, DEFAULT_SETTINGS);
assert('U10-i', '수동 제외 분모 차감: 1/(10-2)=12.5%', r4.score, 12.5);
assert('U10-j', '  excluded = 2 (수동 2건)', r4.excluded, 2);

// 시나리오 5: 빈 매칭
var r5 = computeScore([], 100, DEFAULT_SETTINGS);
assert('U10-k', '빈 매칭: score=0, excluded=0',
    { score: r5.score, excluded: r5.excluded }, { score: 0, excluded: 0 });

// 시나리오 6: denominator 0 방지
var matches6 = [m('boilerplate', {target_idx:0})];
var r6 = computeScore(matches6, 1, DEFAULT_SETTINGS);
assert('U10-l', 'denominator 0 방지: totalSentences=1, excluded=1 -> 0%', r6.score, 0);

out.write('\n---------------------------------\n');
out.write('PASS: ' + pass + ' · FAIL: ' + fail + '\n');
out.write('---------------------------------\n');
process.exit(fail > 0 ? 1 : 0);
