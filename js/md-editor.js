/* ===================================
   Plan-60 — 통일 양식 마크다운 저작 편집기 (Toast UI 래퍼)

   기존 EditorCore(Monaco/HTML, js/editor-core.js)와 독립.
   - 저장: POST /api/save-markdown (name 기반, data/authored/ 저장, MD 원문 — Plan-72 P4)
   - Plan-72 P3: 전체화면 오버레이 폐기 → Author 셸(#au-editor-host)에 인셸 마운트(공통 헤더 유지)
   - front matter(제목·작성자·날짜·문서번호·보안등급)는 헤더 폼으로 관리 → 저장 시 합성
   - 본문은 Toast UI 로 Markdown↔WYSIWYG 작성 (통일 양식 사양 §1·§2)
   =================================== */
(function () {
    'use strict';

    var BACKEND = (window.EDITOR_CONFIG && EDITOR_CONFIG.backendUrl) || '';

    var CLASSIFICATIONS = ['', '일반', '대외비', '비밀'];

    var state = { open: false, editor: null, name: null, isNew: false, initial: '' };
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

    // ── 표지 요약 · dirty · 제목 auto-grow (전 입력원 공통) ──
    function summaryText(m) {
        var parts = [m.author, m.doc_number, m.classification].filter(Boolean);
        return parts.length ? '· ' + parts.join(' · ') : '';
    }

    function refreshStatus() {
        if (!dom) return;
        if (dom.summary) dom.summary.textContent = summaryText(metaFromFields());
        if (dom.status) {
            var mod = isModified();
            dom.status.textContent = mod ? '● 저장되지 않은 변경사항' : '저장됨';
            dom.status.classList.toggle('is-dirty', mod);
        }
    }

    // 제목 textarea 높이 자동 조절 (긴 제목 줄바꿈 — 클리핑 방지)
    function autoGrowTitle() {
        var t = dom && dom.title;
        if (!t) return;
        t.style.height = 'auto';
        t.style.height = t.scrollHeight + 'px';
    }

    function onTitleInput() {   // 제목: 높이 재계산 + dirty/요약
        autoGrowTitle();
        refreshStatus();
    }
    function onMetaInput() {     // 메타 필드: dirty/요약만 (제목 높이와 무관)
        refreshStatus();
    }

    // ── DOM 구성 (1회) ──
    function buildDom() {
        if (dom) return;
        var ov = document.createElement('div');
        ov.className = 'md-editor-overlay';
        ov.innerHTML =
            '<div class="md-editor-topbar">' +
              '<span class="md-editor-crumb">' +
                '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>' +
                '<span data-el="crumb">새 문서</span>' +
              '</span>' +
              '<span class="md-editor-spacer"></span>' +
              '<span class="md-editor-status" data-el="status">저장됨</span>' +
              '<button type="button" class="btn btn-primary" data-act="save">저장</button>' +
              '<button type="button" class="btn btn-secondary" data-act="export">DOCX 내보내기</button>' +
              '<button type="button" class="btn btn-ghost btn-icon" data-act="close" aria-label="닫기">✕</button>' +
            '</div>' +
            '<div class="md-editor-canvas">' +
              '<div class="md-editor-sheet">' +
                '<textarea class="md-editor-title" rows="1" placeholder="제목 없는 문서" maxlength="120"></textarea>' +
                '<details class="md-editor-meta">' +
                  '<summary>' +
                    '<svg class="md-editor-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>' +
                    '표지 정보 <span class="md-editor-summary-vals" data-el="summary"></span>' +
                  '</summary>' +
                  '<div class="md-editor-meta-fields">' +
                    '<div class="md-editor-field"><label>작성자</label><input type="text" class="form-input form-input-sm" data-f="author" /></div>' +
                    '<div class="md-editor-field"><label>문서번호</label><input type="text" class="form-input form-input-sm" data-f="docNumber" placeholder="TR-2026-001" /></div>' +
                    '<div class="md-editor-field"><label>보안등급</label><select class="form-select form-select-sm" data-f="classification"></select></div>' +
                  '</div>' +
                '</details>' +
                '<div class="md-editor-host"></div>' +
              '</div>' +
            '</div>';
        // Plan-72 P3: Author 셸 콘텐츠 영역에 마운트(공통 헤더 유지). 컨테이너 없으면 body 폴백.
        (document.getElementById('au-editor-host') || document.body).appendChild(ov);

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
            crumb: ov.querySelector('[data-el="crumb"]'),
            status: ov.querySelector('[data-el="status"]'),
            summary: ov.querySelector('[data-el="summary"]'),
        };

        ov.querySelector('[data-act="save"]').addEventListener('click', doSave);
        ov.querySelector('[data-act="export"]').addEventListener('click', doExport);
        ov.querySelector('[data-act="close"]').addEventListener('click', closeWithConfirm);

        // dirty · 요약 · auto-grow 배선 (전 입력원: 제목·작성자·문서번호·보안등급)
        dom.title.addEventListener('input', onTitleInput);
        dom.title.addEventListener('keydown', function (e) { if (e.key === 'Enter') e.preventDefault(); });
        dom.author.addEventListener('input', onMetaInput);
        dom.docNumber.addEventListener('input', onMetaInput);
        dom.classification.addEventListener('change', onMetaInput);
    }

    function mountEditor(initialBody) {
        if (state.editor) { try { state.editor.destroy(); } catch (e) {} state.editor = null; }
        dom.host.innerHTML = '';
        state.editor = new toastui.Editor({
            el: dom.host,
            height: '100%',
            initialEditType: 'wysiwyg',
            previewStyle: 'tab',
            language: 'ko-KR',
            usageStatistics: false,
            theme: isDark() ? 'dark' : 'default',
            initialValue: initialBody || '',
        });
        state.editor.on('change', refreshStatus);
    }

    // ── 열기 ──
    function open(opts) {
        buildDom();
        state.name = opts.name || null;
        state.isNew = !!opts.isNew;
        dom.title.value = opts.meta.title || '';
        dom.author.value = opts.meta.author || '';
        dom.docNumber.value = opts.meta.doc_number || '';
        dom.classification.value = CLASSIFICATIONS.indexOf(opts.meta.classification) >= 0 ? opts.meta.classification : '';
        dom.date = opts.meta.date || todayISO();
        dom.title.readOnly = !state.isNew;   // 기존 문서는 제목=파일명 고정
        dom.crumb.textContent = state.isNew ? '새 문서' : '문서 편집';  // 공유 편집기 — 진입 맥락 반영
        mountEditor(opts.body);
        dom.overlay.classList.add('open');
        state.open = true;
        state.initial = snapshot();
        autoGrowTitle();
        refreshStatus();
        setTimeout(function () { (state.isNew ? dom.title : dom.host).focus(); }, 50);
    }

    function openNew() {
        // 빈 문서로 시작 — 제목·작성자·문서번호 등은 헤더 폼(front matter)이 담당
        open({ isNew: true, name: null, meta: { date: todayISO(), author: _currentUser() }, body: '' });
    }

    function openExisting(name, rawMd) {
        var parsed = parseFrontMatter(rawMd);
        open({ isNew: false, name: name, meta: parsed.meta, body: parsed.body });
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

        var name = state.name;
        if (state.isNew) {
            var slug = slugify(meta.title);
            if (!slug) { showToast('제목에 사용할 수 있는 문자가 없습니다', 'error'); return; }
            name = slug + '.md';
        }

        var content = buildFrontMatter(meta) + state.editor.getMarkdown() + '\n';

        try {
            var res = await fetch(BACKEND + '/api/save-markdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    name: name,
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
            state.name = data.name;
            state.isNew = false;
            dom.title.readOnly = true;
            dom.crumb.textContent = '문서 편집';
            state.initial = snapshot();
            refreshStatus();
            showToast('저장되었습니다', 'success');
            // 호스트 시스템 저장 후 훅 (Author: 좌측 패널·최근 문서 목록 갱신). Explorer 는 미정의 → no-op
            if (typeof window.onMdEditorSaved === 'function') {
                // 훅 실패는 저장 성공(위)에 영향 없음 — 목록 갱신만 못 함, 삼켜서 저장 흐름 보호
                try { window.onMdEditorSaved(state.name, wasNew); } catch (e) {}
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
        state.name = null;
        // 셸 통합(Plan-72 P3): 호스트(Author)가 워크스페이스를 닫고 홈으로 복귀하도록 통지
        if (typeof window.onMdEditorClosed === 'function') {
            try { window.onMdEditorClosed(); } catch (e) {}
        }
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
