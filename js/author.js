/* ===================================================================
   Author 셸 로직 — Plan-61
   - 공통 헤더(currentSystem:'author') · 테마 · 푸터 · 애널리틱스
   - 최근 문서 = GET /api/authored 실연동 (카드/리스트 토글)
   - 진입 타일·새 문서 = "곧 제공" 자리표시 (실연결은 후속 Phase)
   - 합성 = empty-state (백엔드 미구현)
   =================================================================== */
(function () {
    'use strict';

    var API = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG)
        ? AUTH_CONFIG.backendUrl : '';

    var FILE_SVG = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
    var FILE_SVG_LG = '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';

    var docs = [];
    var view = localStorage.getItem('author-view') === 'list' ? 'list' : 'cards';

    // ── 테마 (app.js initTheme 와 동일 메커니즘: localStorage 'theme' + body.dataset.theme) ──
    function initTheme() {
        if (localStorage.getItem('theme') === 'dark') {
            document.body.dataset.theme = 'dark';
        }
        var btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', function () {
                var isDark = document.body.dataset.theme === 'dark';
                document.body.dataset.theme = isDark ? '' : 'dark';
                localStorage.setItem('theme', isDark ? 'light' : 'dark');
            });
        }
    }

    // ── RBAC 바디 클래스 (auth.js updateAuthUI 와 동일 규칙) ──
    function applyRbac(user) {
        var role = user && user.role;
        document.body.classList.toggle('auth-logged-in', !!user);
        document.body.classList.toggle('auth-editor', role === 'editor' || role === 'admin');
        document.body.classList.toggle('auth-admin', role === 'admin');
    }

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = (s == null) ? '' : String(s);
        return d.innerHTML;
    }

    function fmtDate(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        if (isNaN(d.getTime())) return '';
        return (d.getMonth() + 1) + '/' + d.getDate();
    }

    function comingSoon() {
        if (typeof showToast === 'function') {
            showToast('곧 제공됩니다 — 현재 준비 중인 기능입니다.');
        }
    }

    function openDoc(url) {
        // 읽기는 Explorer 잔류: index.html?page= 딥링크 (app.js loadPageFromUrl)
        // 방어: 서버 생성 contents/ 경로만 허용 (javascript: 등 차단)
        if (!url || url.indexOf('contents/') !== 0) return;
        window.location.href = 'index.html?page=' + encodeURIComponent(url);
    }

    // ── 최근 문서 렌더 ──
    function renderRecent() {
        var host = document.getElementById('recent-host');
        if (!host) return;

        if (!docs.length) {
            host.innerHTML =
                '<div class="au-empty">' + FILE_SVG_LG +
                '<h4>아직 작성한 문서가 없습니다</h4>' +
                '<p>통일 양식으로 새 기술 문서를 작성해 보세요.</p></div>';
            return;
        }

        if (view === 'list') {
            var rows = docs.map(function (d) {
                return '<button type="button" class="au-row" data-url="' + esc(d.url) + '">' +
                    '<span class="au-row-name">' + FILE_SVG + '<span>' + esc(d.label) + '</span></span>' +
                    '<span class="au-row-owner col-owner">' + esc(d.author || '—') + '</span>' +
                    '<span class="au-row-date">' + esc(fmtDate(d.modified)) + '</span>' +
                    '</button>';
            }).join('');
            host.innerHTML =
                '<div class="au-list"><div class="au-list-head">' +
                '<span>문서명</span><span class="col-owner">작성자</span><span class="ra">수정일</span></div>' +
                rows + '</div>';
        } else {
            var cards = docs.map(function (d) {
                return '<button type="button" class="au-card" data-url="' + esc(d.url) + '">' +
                    '<span class="au-card-top">' + FILE_SVG +
                    '<span class="au-card-name">' + esc(d.label) + '</span></span>' +
                    '<span class="au-card-meta"><span>' + esc(d.author || '—') + '</span>' +
                    '<span class="au-dot"></span><span>' + esc(fmtDate(d.modified)) + '</span></span>' +
                    '</button>';
            }).join('');
            // editor+ 만 보이는 "빈 문서 작성" 점선 타일
            cards += '<button type="button" class="au-card new auth-editor-only" data-act="new-doc">＋ 빈 문서 작성</button>';
            host.innerHTML = '<div class="au-grid">' + cards + '</div>';
        }

        host.querySelectorAll('[data-url]').forEach(function (el) {
            el.addEventListener('click', function () { openDoc(el.getAttribute('data-url')); });
        });
        host.querySelectorAll('[data-act="new-doc"]').forEach(function (el) {
            el.addEventListener('click', comingSoon);
        });
    }

    function setView(v) {
        view = v;
        localStorage.setItem('author-view', v);
        var c = document.getElementById('seg-cards');
        var l = document.getElementById('seg-list');
        if (c) c.setAttribute('aria-pressed', String(v === 'cards'));
        if (l) l.setAttribute('aria-pressed', String(v === 'list'));
        renderRecent();
    }

    function loadRecent() {
        // credentials: 플랫폼 fetch 관례 정합(교차출처 직접실행 대비) — /api/authored 자체는 공개
        fetch(API + '/api/authored', { credentials: 'include' })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function (d) { docs = (d && d.documents) || []; renderRecent(); })
            .catch(function () { docs = []; renderRecent(); });
    }

    function wireActions() {
        ['tile-new-doc', 'tile-new-synth', 'act-new-doc'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.addEventListener('click', comingSoon);
        });
        var c = document.getElementById('seg-cards');
        var l = document.getElementById('seg-list');
        if (c) c.addEventListener('click', function () { setView('cards'); });
        if (l) l.addEventListener('click', function () { setView('list'); });
    }

    function init() {
        if (typeof initPlatformHeader === 'function') {
            initPlatformHeader({
                title: 'Author',
                currentSystem: 'author',
                showThemeToggle: true,
                authRequired: true,      // 미로그인 → login.html (헤더 onUnauth 기본)
                onAuth: function (user) {
                    document.body.style.visibility = 'visible';
                    document.body.classList.add('fade-in');
                    applyRbac(user);
                    if (typeof initAnalytics === 'function') initAnalytics('author');
                    loadRecent();
                }
            });
        }

        initTheme();
        if (typeof initPlatformFooter === 'function') initPlatformFooter('author-footer');

        // 초기 세그먼트 상태 동기화
        var c = document.getElementById('seg-cards');
        var l = document.getElementById('seg-list');
        if (c) c.setAttribute('aria-pressed', String(view === 'cards'));
        if (l) l.setAttribute('aria-pressed', String(view === 'list'));

        wireActions();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
