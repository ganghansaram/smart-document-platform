/* ===================================
   Plan-60 — 통일 양식 마크다운 저작 편집기 (Toast UI 래퍼)

   기존 EditorCore(Monaco/HTML, js/editor-core.js)와 독립.
   - 저장: POST /api/save-markdown (contents/authored/ 전용, MD 원문)
   - front matter(제목·작성자·날짜·문서번호·보안등급)는 헤더 폼으로 관리 → 저장 시 합성
   - 본문은 Toast UI 로 Markdown↔WYSIWYG 작성 (통일 양식 사양 §1·§2)
   =================================== */
(function () {
    'use strict';

    var BACKEND = (window.EDITOR_CONFIG && EDITOR_CONFIG.backendUrl) || '';

    // 신규 문서 골격 (통일 양식 사양 §2)
    var SKELETON = ['# 개요', '', '## 배경', '', '## 목적', '', '# 본론', '', '# 결론', ''].join('\n');
    var CLASSIFICATIONS = ['', '일반', '대외비', '비밀'];

    var state = { open: false, editor: null, path: null, isNew: false, initial: '' };
    var dom = null;

    function todayISO() {
        var d = new Date();
        return d.getFullYear() + '-' +
            String(d.getMonth() + 1).padStart(2, '0') + '-' +
            String(d.getDate()).padStart(2, '0');
    }

    function isDark() {
        var t = document.body.getAttribute('data-theme') ||
                document.documentElement.getAttribute('data-theme');
        return t === 'dark';
    }

    // 제목 → 안전 파일명 (백엔드 정규식과 동일 허용집합)
    function slugify(title) {
        return (title || '').trim()
            .replace(/[^\w\-. ()가-힣]+/g, '-')
            .replace(/-+/g, '-')
            .replace(/^[-.]+|[-.]+$/g, '');
    }

    // 선두 front matter 파싱 → { meta, body }
    function parseFrontMatter(md) {
        var meta = {};
        var m = /^﻿?---\s*\n([\s\S]*?)\n---\s*\n?/.exec(md || '');
        if (!m) return { meta: meta, body: md || '' };
        m[1].split('\n').forEach(function (line) {
            var mm = /^\s*([A-Za-z_]+)\s*:\s*(.+?)\s*$/.exec(line);
            if (mm) meta[mm[1]] = mm[2].replace(/^["']|["']$/g, '');
        });
        return { meta: meta, body: md.slice(m[0].length) };
    }

    function buildFrontMatter(meta) {
        var order = ['title', 'subtitle', 'author', 'date', 'doc_number', 'classification'];
        var lines = ['---'];
        order.forEach(function (k) {
            if (meta[k]) lines.push(k + ': "' + String(meta[k]).replace(/"/g, "'") + '"');
        });
        lines.push('---', '');
        return lines.join('\n');
    }

    // 제어문자 제거 + 앞뒤 공백 정리 (메뉴 라벨·파일명 위생)
    function cleanField(v) {
        var s = v || '', out = '';
        for (var i = 0; i < s.length; i++) {
            var c = s.charCodeAt(i);
            if (c >= 32 && c !== 127) out += s.charAt(i);  // 제어문자 제외
        }
        return out.trim();
    }

    function metaFromFields() {
        return {
            title: cleanField(dom.title.value),
            author: cleanField(dom.author.value),
            doc_number: cleanField(dom.docNumber.value),
            classification: dom.classification.value,
            date: dom.date || todayISO(),
        };
    }

    function snapshot() {
        return JSON.stringify(metaFromFields()) + '' + (state.editor ? state.editor.getMarkdown() : '');
    }

    // ── DOM 구성 (1회) ──
    function buildDom() {
        if (dom) return;
        var ov = document.createElement('div');
        ov.className = 'md-editor-overlay';
        ov.innerHTML =
            '<div class="md-editor-header">' +
              '<div class="md-editor-row">' +
                '<input type="text" class="form-input md-editor-title" placeholder="문서 제목 (필수)" maxlength="120" />' +
                '<button type="button" class="btn btn-primary" data-act="save">저장</button>' +
                '<button type="button" class="btn btn-secondary" data-act="export">DOCX 내보내기</button>' +
                '<button type="button" class="btn btn-ghost" data-act="close">닫기</button>' +
              '</div>' +
              '<div class="md-editor-row md-editor-meta">' +
                '<label>작성자</label><input type="text" class="form-input form-input-sm" data-f="author" />' +
                '<label>문서번호</label><input type="text" class="form-input form-input-sm" data-f="docNumber" placeholder="TR-2026-001" />' +
                '<label>보안등급</label><select class="form-select form-select-sm" data-f="classification"></select>' +
              '</div>' +
            '</div>' +
            '<div class="md-editor-host"></div>';
        document.body.appendChild(ov);

        var sel = ov.querySelector('[data-f="classification"]');
        CLASSIFICATIONS.forEach(function (c) {
            var o = document.createElement('option');
            o.value = c; o.textContent = c || '(없음)';
            sel.appendChild(o);
        });

        dom = {
            overlay: ov,
            title: ov.querySelector('.md-editor-title'),
            author: ov.querySelector('[data-f="author"]'),
            docNumber: ov.querySelector('[data-f="docNumber"]'),
            classification: sel,
            host: ov.querySelector('.md-editor-host'),
            date: null,
        };

        ov.querySelector('[data-act="save"]').addEventListener('click', doSave);
        ov.querySelector('[data-act="export"]').addEventListener('click', doExport);
        ov.querySelector('[data-act="close"]').addEventListener('click', closeWithConfirm);
    }

    function mountEditor(initialBody) {
        if (state.editor) { try { state.editor.destroy(); } catch (e) {} state.editor = null; }
        dom.host.innerHTML = '';
        state.editor = new toastui.Editor({
            el: dom.host,
            height: '100%',
            initialEditType: 'markdown',
            previewStyle: 'vertical',
            language: 'ko-KR',
            usageStatistics: false,
            theme: isDark() ? 'dark' : 'default',
            initialValue: initialBody || '',
        });
    }

    // ── 열기 ──
    function open(opts) {
        buildDom();
        state.path = opts.path || null;
        state.isNew = !!opts.isNew;
        dom.title.value = opts.meta.title || '';
        dom.author.value = opts.meta.author || '';
        dom.docNumber.value = opts.meta.doc_number || '';
        dom.classification.value = CLASSIFICATIONS.indexOf(opts.meta.classification) >= 0 ? opts.meta.classification : '';
        dom.date = opts.meta.date || todayISO();
        dom.title.readOnly = !state.isNew;   // 기존 문서는 제목=파일명 고정
        mountEditor(opts.body);
        dom.overlay.classList.add('open');
        state.open = true;
        state.initial = snapshot();
        setTimeout(function () { (state.isNew ? dom.title : dom.host).focus(); }, 50);
    }

    function openNew() {
        open({ isNew: true, path: null, meta: { date: todayISO(), author: _currentUser() }, body: SKELETON });
    }

    function openExisting(path, rawMd) {
        var parsed = parseFrontMatter(rawMd);
        open({ isNew: false, path: path, meta: parsed.meta, body: parsed.body });
    }

    function _currentUser() {
        try { return (window.AuthState && AuthState.user && AuthState.user.username) || ''; }
        catch (e) { return ''; }
    }

    // ── 저장 ──
    async function doSave() {
        var wasNew = state.isNew;
        var meta = metaFromFields();
        if (!meta.title) { showToast('문서 제목을 입력하세요', 'error'); dom.title.focus(); return; }

        var path = state.path;
        if (state.isNew) {
            var slug = slugify(meta.title);
            if (!slug) { showToast('제목에 사용할 수 있는 문자가 없습니다', 'error'); return; }
            path = 'contents/authored/' + slug + '.md';
        }

        var content = buildFrontMatter(meta) + state.editor.getMarkdown() + '\n';

        try {
            var res = await fetch(BACKEND + '/api/save-markdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    path: path,
                    content: content,
                    createBackup: true,
                    overwrite: !state.isNew,   // 신규는 동명 파일 보호(409)
                }),
            });
            if (res.status === 409) { showToast('같은 제목의 문서가 이미 있습니다', 'error'); return; }
            if (!res.ok) {
                var err = await res.json().catch(function () { return {}; });
                throw new Error(err.detail || '저장 실패');
            }
            var data = await res.json();
            state.path = data.path;
            state.isNew = false;
            dom.title.readOnly = true;
            state.initial = snapshot();
            showToast('저장되었습니다', 'success');
            // 기존 문서를 보던 화면이면 배경 뷰 새로고침 (Monaco onSave 와 일관)
            if (!wasNew && typeof window.loadContent === 'function' &&
                window.AppState && AppState.currentPage === state.path) {
                loadContent(state.path);
            }
            // 신규 저작 문서는 좌측 "작성 문서" 메뉴에 즉시 반영 + 새 문서 짚어주기
            if (wasNew && typeof window.loadMenuData === 'function') {
                var savedUrl = state.path;
                window.loadMenuData(function () {
                    if (typeof window.highlightAuthoredDoc === 'function') window.highlightAuthoredDoc(savedUrl);
                });
            }
            // 호스트 시스템 저장 후 훅 (Author: 최근 문서 목록 갱신 — Plan-70). Explorer 는 미정의 → no-op
            if (typeof window.onMdEditorSaved === 'function') {
                // 훅 실패는 저장 성공(위)에 영향 없음 — 목록 갱신만 못 함, 삼켜서 저장 흐름 보호
                try { window.onMdEditorSaved(state.path, wasNew); } catch (e) {}
            }
        } catch (e) {
            showToast('저장 실패: ' + e.message, 'error');
        }
    }

    // ── 통일 양식 DOCX 내보내기 (Plan-60 Phase 3) ──
    async function doExport() {
        var meta = metaFromFields();
        if (!meta.title) { showToast('문서 제목을 입력하세요', 'error'); dom.title.focus(); return; }
        var content = buildFrontMatter(meta) + state.editor.getMarkdown() + '\n';
        showToast('DOCX 생성 중…');
        try {
            var res = await fetch(BACKEND + '/api/export-docx', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ md: content, filename: meta.title }),
            });
            if (!res.ok) {
                var err = await res.json().catch(function () { return {}; });
                throw new Error(err.detail || '내보내기 실패');
            }
            var blob = await res.blob();
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = meta.title + '.docx';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            showToast('DOCX 내보내기 완료', 'success');
        } catch (e) {
            showToast('내보내기 실패: ' + e.message, 'error');
        }
    }

    function isModified() { return state.open && state.initial !== snapshot(); }

    function close(force) {
        if (!state.open) return;
        if (!force && isModified()) { /* 호출 측에서 confirm 처리 */ }
        if (state.editor) { try { state.editor.destroy(); } catch (e) {} state.editor = null; }
        dom.overlay.classList.remove('open');
        state.open = false;
        state.path = null;
    }

    function closeWithConfirm() {
        if (state.open && isModified()) {
            if (!window.confirm('저장하지 않은 변경사항이 있습니다. 닫으시겠습니까?')) return;
        }
        close(true);
    }

    // ESC 닫기 (편집기 열려 있을 때만)
    document.addEventListener('keydown', function (e) {
        if (!state.open) return;
        if (e.key === 'Escape') { e.stopPropagation(); closeWithConfirm(); }
        else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); doSave(); }
    });

    window.MdEditor = {
        openNew: openNew,
        openExisting: openExisting,
        close: close,
        closeWithConfirm: closeWithConfirm,
        isOpen: function () { return state.open; },
        isModified: isModified,
    };
})();
