/* ===================================================================
   Author 셸 로직 — Plan-61
   - 공통 헤더(currentSystem:'author') · 테마 · 푸터 · 애널리틱스
   - 최근 문서 = GET /api/authored 실연동 (카드/리스트 토글)
   - 저작 진입점(빈 문서·+새 문서·동적 카드) = MdEditor 실연결 (Plan-70 교정 이전, editor 권한)
   - 합성 타일 = "곧 제공" 자리표시 (Plan-24) · 합성 섹션 = empty-state (백엔드 미구현)
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

    // ── 저작 워크스페이스 (Plan-72 P3): 인셸 편집(좌측 패널 + 우측 편집면), 헤더 유지 ──
    function enterWorkspace() { document.body.classList.add('au-editing'); }
    function exitWorkspace() {
        document.body.classList.remove('au-editing');
        loadRecent();   // 홈 최근 문서 목록 최신화
    }

    // 편집 중 미저장 변경 보호 (새 문서·문서 전환 공통)
    function confirmDiscardIfDirty(msg) {
        if (window.MdEditor && MdEditor.isOpen() && MdEditor.isModified()) {
            return window.confirm(msg);
        }
        return true;
    }

    // 좌측 '내 문서' 패널 렌더 (activeName 강조)
    function renderPanel(activeName) {
        var host = document.getElementById('ws-doc-list');
        if (!host) return;
        if (!docs.length) {
            host.innerHTML = '<div class="au-ws-empty">아직 작성한 문서가 없습니다.</div>';
            return;
        }
        host.innerHTML = docs.map(function (d) {
            var active = (d.name === activeName) ? ' active' : '';
            return '<button type="button" class="au-ws-item' + active + '" data-name="' + esc(d.name) + '">' +
                FILE_SVG + '<span class="au-ws-item-name">' + esc(d.label) + '</span></button>';
        }).join('');
        host.querySelectorAll('[data-name]').forEach(function (el) {
            el.addEventListener('click', function () { openDoc(el.getAttribute('data-name')); });
        });
    }

    // 빈 문서 작성 = 저작 편집기(창작은 Author). 셸 안에서 헤더 유지된 채 편집.
    function openNewDoc() {
        if (!window.MdEditor) { if (typeof showToast === 'function') showToast('편집기를 불러오지 못했습니다', 'error'); return; }
        if (!confirmDiscardIfDirty('저장하지 않은 변경사항이 있습니다. 새 문서를 여시겠습니까?')) return;
        enterWorkspace();
        renderPanel(null);
        MdEditor.openNew();
    }

    // 기존 문서 편집 진입 (Plan-72 P3: Explorer 리다이렉트 폐기 → 인증 content API 경유 인셸 편집)
    function openDoc(name) {
        if (!name || !window.MdEditor) return;
        if (!confirmDiscardIfDirty('저장하지 않은 변경사항이 있습니다. 다른 문서를 여시겠습니까?')) return;
        fetch(API + '/api/authored/content?name=' + encodeURIComponent(name), { credentials: 'include' })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
            .then(function (text) {
                enterWorkspace();
                renderPanel(name);
                MdEditor.openExisting(name, text);
            })
            .catch(function () {
                if (typeof showToast === 'function') showToast('문서를 불러오지 못했습니다', 'error');
            });
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
                return '<button type="button" class="au-row" data-name="' + esc(d.name) + '">' +
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
                return '<button type="button" class="au-card content-card" data-name="' + esc(d.name) + '">' +
                    '<span class="au-card-top">' + FILE_SVG +
                    '<span class="au-card-name">' + esc(d.label) + '</span></span>' +
                    '<span class="au-card-meta"><span>' + esc(d.author || '—') + '</span>' +
                    '<span class="au-dot"></span><span>' + esc(fmtDate(d.modified)) + '</span></span>' +
                    '</button>';
            }).join('');
            // editor+ 만 보이는 "빈 문서 작성" 점선 타일
            cards += '<button type="button" class="au-card new content-card auth-editor-only" data-act="new-doc">＋ 빈 문서 작성</button>';
            host.innerHTML = '<div class="au-grid">' + cards + '</div>';
        }

        host.querySelectorAll('[data-name]').forEach(function (el) {
            el.addEventListener('click', function () { openDoc(el.getAttribute('data-name')); });
        });
        host.querySelectorAll('[data-act="new-doc"]').forEach(function (el) {
            el.addEventListener('click', openNewDoc);
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

    // 소유자 문서 목록 조회 (Plan-72 P4: 인증 필수·소유자 한정 — 비소유/미인증 시 빈 목록)
    function fetchDocs() {
        return fetch(API + '/api/authored', { credentials: 'include' })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function (d) { docs = (d && d.documents) || []; })
            .catch(function () { docs = []; });
    }

    function loadRecent() { fetchDocs().then(renderRecent); }

    function wireActions() {
        // 저작 진입점(빈 문서 작성·+새 문서·워크스페이스 패널 새 문서) → 편집기 / 합성 타일은 준비 중(Plan-24)
        ['tile-new-doc', 'act-new-doc', 'ws-new-doc'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.addEventListener('click', openNewDoc);
        });
        var synth = document.getElementById('tile-new-synth');
        if (synth) synth.addEventListener('click', comingSoon);
        var c = document.getElementById('seg-cards');
        var l = document.getElementById('seg-list');
        if (c) c.addEventListener('click', function () { setView('cards'); });
        if (l) l.addEventListener('click', function () { setView('list'); });
    }

    function init() {
        if (typeof initPlatformHeader === 'function') {
            initPlatformHeader({
                title: 'Document Author',
                currentSystem: 'author',
                showThemeToggle: true,
                authRequired: true,      // 미로그인 → login.html (헤더 onUnauth 기본)
                onAuth: function (user) {
                    document.body.style.visibility = 'visible';
                    document.body.classList.add('fade-in');
                    applyRbac(user);
                    // 편집기 작성자 필드 프리필용 (auth.js 미로드 환경 — md-editor 가 참조)
                    window.AuthState = { user: user };
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

        // 저작 편집기 저장 후: 좌측 패널 목록 갱신(현재 문서 강조 유지). 홈 목록은 워크스페이스 종료 시 갱신.
        window.onMdEditorSaved = function (name) {
            fetchDocs().then(function () { renderPanel(name); });
        };
        // 편집기 닫힘(✕·ESC) → 워크스페이스 종료·홈 복귀 (Plan-72 P3)
        window.onMdEditorClosed = exitWorkspace;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
