/* ===================================
   공통 문서 편집기 코어
   Monaco Editor 기반, Strategy 패턴
   Explorer(HTML)·Translator(MD) 공용
   =================================== */

/**
 * EditorCore — 문서 편집기 공통 엔진
 *
 * 사용법:
 *   var inst = EditorCore.create({
 *       language:       'html' | 'markdown',
 *       title:          '편집기 타이틀',
 *       renderPreview:  function(content) { return htmlString; },
 *       onSave:         async function(content) { ... },
 *       onClose:        function() { ... },           // 선택
 *       resolveAssets:  function(content) { return content; },  // 선택
 *       sourceLabel:    'HTML Source',                 // 좌측 패인 라벨
 *       previewLabel:   'Preview',                     // 우측 패인 라벨
 *       previewClass:   '',                            // 프리뷰 패인 추가 class
 *       autoSaveInterval: 0,                           // ms, 0이면 비활성
 *       monacoBasePath: 'js/monaco-editor/vs',
 *   });
 *
 *   inst.open(content, docPath);   // 모달 열기 + 에디터 초기화
 *   inst.close();                  // 모달 닫기
 *   inst.isOpen();                 // 현재 열려있는지
 *   inst.isModified();             // 변경 여부
 *   inst.getValue();               // 현재 편집 내용
 */
var EditorCore = (function () {
    'use strict';

    /* ── 기본값 ── */
    var DEFAULTS = {
        language: 'html',
        title: 'Document Editor',
        sourceLabel: 'Source',
        previewLabel: 'Preview',
        previewClass: '',
        autoSaveInterval: 0,
        monacoBasePath: 'js/monaco-editor/vs',
        renderPreview: function (c) { return c; },
        onSave: null,
        onClose: null,
        resolveAssets: null,
    };

    /* ── 유틸 ── */
    function escapeHtml(text) {
        var d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    /* Monaco 로드 (전역 1회) */
    var _monacoReady = null;
    function loadMonaco(basePath) {
        if (_monacoReady) return _monacoReady;
        _monacoReady = new Promise(function (resolve, reject) {
            if (typeof monaco !== 'undefined') { resolve(); return; }
            var s = document.createElement('script');
            s.src = basePath + '/../vs/loader.js';
            // basePath 가 "js/monaco-editor/vs" 이면 loader 는 상위에 없으므로 직접 지정
            s.src = basePath.replace(/\/vs\/?$/, '') + '/vs/loader.js';
            s.onload = function () {
                require.config({ paths: { vs: basePath } });
                require(['vs/editor/editor.main'], resolve);
            };
            s.onerror = reject;
            document.head.appendChild(s);
        });
        return _monacoReady;
    }

    /* ── DOM 구축 (모달 + 확인 다이얼로그) ── */
    var _domBuilt = false;
    var _modalEl, _confirmEl;

    function ensureDOM() {
        if (_domBuilt) return;
        _domBuilt = true;

        // 모달
        _modalEl = document.createElement('div');
        _modalEl.id = 'ec-modal';
        _modalEl.className = 'editor-modal';
        _modalEl.innerHTML =
            '<div class="editor-container">' +
                '<div class="editor-header">' +
                    '<div class="editor-title">' +
                        '<h3 id="ec-title">Document Editor</h3>' +
                        '<span class="doc-path" id="ec-doc-path"></span>' +
                    '</div>' +
                    '<div class="editor-actions">' +
                        '<button class="btn btn-icon btn-icon-lg editor-fullscreen-btn" id="ec-fullscreen" title="Fullscreen">' +
                            '<span class="icon"></span>' +
                        '</button>' +
                        '<button class="btn btn-secondary editor-cancel-btn" id="ec-cancel">Cancel</button>' +
                        '<button class="btn btn-primary editor-save-btn" id="ec-save">' +
                            '<span class="icon"></span> Save' +
                        '</button>' +
                        '<button class="btn btn-icon btn-icon-lg editor-close-btn" id="ec-close">&times;</button>' +
                    '</div>' +
                '</div>' +
                '<div class="editor-body">' +
                    '<div id="ec-body-inner"></div>' +
                '</div>' +
                '<div class="editor-footer">' +
                    '<div class="editor-status">' +
                        '<span class="status-indicator" id="ec-status-indicator"></span>' +
                        '<span id="ec-status-text">Ready</span>' +
                    '</div>' +
                    '<div class="editor-autosave" id="ec-autosave-info"></div>' +
                '</div>' +
            '</div>';
        document.body.appendChild(_modalEl);

        // 확인 다이얼로그
        _confirmEl = document.createElement('div');
        _confirmEl.id = 'ec-confirm';
        _confirmEl.className = 'editor-confirm-dialog';
        _confirmEl.innerHTML =
            '<div class="editor-confirm-content">' +
                '<h4 id="ec-confirm-title">Unsaved Changes</h4>' +
                '<p id="ec-confirm-msg">You have unsaved changes. Are you sure you want to close?</p>' +
                '<div class="editor-confirm-actions">' +
                    '<button class="confirm-no" id="ec-confirm-no">Cancel</button>' +
                    '<button class="confirm-yes" id="ec-confirm-yes">Discard</button>' +
                '</div>' +
            '</div>';
        document.body.appendChild(_confirmEl);
    }

    /* ── 인스턴스 생성 ── */
    function create(opts) {
        var cfg = {};
        for (var k in DEFAULTS) cfg[k] = DEFAULTS[k];
        for (var k in opts) cfg[k] = opts[k];

        ensureDOM();

        var state = {
            open: false,
            modified: false,
            editor: null,          // Monaco 인스턴스
            previewTimer: null,
            autoSaveTimer: null,
            originalContent: null,
            docPath: null,
            _previewEl: null,
        };

        /* ── 내부 함수 ── */

        function updateStatus(text, isModified) {
            var ind = document.getElementById('ec-status-indicator');
            var txt = document.getElementById('ec-status-text');
            if (txt) txt.textContent = text;
            if (ind) ind.className = 'status-indicator' + (isModified ? ' modified' : '');
        }

        function renderPreviewSafe(content) {
            var resolved = (typeof cfg.resolveAssets === 'function')
                ? cfg.resolveAssets(content) : content;
            return cfg.renderPreview(resolved);
        }

        /* 분할 리사이즈 핸들 */
        function initSplitResize(container) {
            var handle = container.querySelector('.monaco-split-handle');
            if (!handle) return;
            var editorPane = container.querySelector('.monaco-editor-pane');
            var previewPane = container.querySelector('.monaco-preview-pane');
            var isDragging = false;

            handle.addEventListener('mousedown', function (e) {
                isDragging = true;
                document.body.style.cursor = 'col-resize';
                document.body.classList.add('resizing');
                e.preventDefault();
            });
            document.addEventListener('mousemove', function (e) {
                if (!isDragging) return;
                var rect = container.getBoundingClientRect();
                var offset = e.clientX - rect.left;
                var ratio = Math.max(0.2, Math.min(0.8, offset / rect.width));
                editorPane.style.flex = 'none';
                editorPane.style.width = (ratio * 100) + '%';
                previewPane.style.flex = 'none';
                previewPane.style.width = ((1 - ratio) * 100) + '%';
            });
            document.addEventListener('mouseup', function () {
                if (isDragging) {
                    isDragging = false;
                    document.body.style.cursor = '';
                    document.body.classList.remove('resizing');
                }
            });
            handle.addEventListener('dblclick', function () {
                editorPane.style.flex = '1';
                editorPane.style.width = '';
                previewPane.style.flex = '1';
                previewPane.style.width = '';
            });
        }

        /* Monaco 인스턴스 생성 */
        function createMonacoInstance(content, editorEl, previewEl) {
            state._previewEl = previewEl;

            // 초기 프리뷰
            previewEl.innerHTML = renderPreviewSafe(content);

            // 다크모드 감지
            var isDark = document.body.getAttribute('data-theme') === 'dark';

            state.editor = monaco.editor.create(editorEl, {
                value: content,
                language: cfg.language,
                theme: isDark ? 'vs-dark' : 'vs',
                fontSize: 14,
                lineNumbers: 'on',
                minimap: { enabled: false },
                wordWrap: 'on',
                automaticLayout: true,
                scrollBeyondLastLine: false,
                tabSize: 2,
            });

            // 변경 감지 + 프리뷰 디바운스 업데이트
            state.editor.onDidChangeModelContent(function () {
                state.modified = true;
                updateStatus('Modified', true);
                clearTimeout(state.previewTimer);
                state.previewTimer = setTimeout(function () {
                    var val = state.editor.getValue();
                    previewEl.innerHTML = renderPreviewSafe(val);
                }, 300);
            });

            // 커서 → 프리뷰 하이라이트
            state.editor.onDidChangeCursorPosition(function (e) {
                highlightAtCursor(e.position, previewEl);
            });

            // 프리뷰 클릭 → 소스 이동
            previewEl.addEventListener('click', function (e) {
                var target = e.target.closest('h1,h2,h3,h4,h5,h6,p,li,td,th,tr,table,div,span,a,img,ul,ol,strong,em,blockquote,pre,code');
                if (target) navigateToSource(target, previewEl);
            });
        }

        /* 커서 위치 → 프리뷰 하이라이트 */
        function highlightAtCursor(position, previewEl) {
            var prev = previewEl.querySelector('.editor-highlight');
            if (prev) prev.classList.remove('editor-highlight');
            if (!state.editor) return;

            var content = state.editor.getValue();
            var lines = content.split('\n');
            var textBefore = '';
            for (var i = 0; i < position.lineNumber - 1; i++) {
                textBefore += lines[i] + '\n';
            }
            textBefore += lines[position.lineNumber - 1].substring(0, position.column - 1);

            if (cfg.language === 'html') {
                _highlightHTML(textBefore, previewEl);
            } else {
                _highlightMarkdown(textBefore, position, lines, previewEl);
            }
        }

        /* HTML 모드: ID → 태그+텍스트 → 순서 */
        function _highlightHTML(textBefore, previewEl) {
            var idMatch = textBefore.match(/id=["']([^"']+)["'][^>]*$/i);
            if (idMatch) {
                var el = previewEl.querySelector('#' + CSS.escape(idMatch[1]));
                if (el) { _applyHighlight(el); return; }
            }
            var tagMatch = textBefore.match(/<(h[1-6]|p|li|td|th|tr|table|div|span|a|img|ul|ol)[^>]*>([^<]*)?$/i);
            if (tagMatch) {
                _findByTagAndText(tagMatch[1].toLowerCase(), tagMatch[2], textBefore, previewEl);
            }
        }

        /* Markdown 모드: 헤딩/리스트/단락 매칭 */
        function _highlightMarkdown(textBefore, position, lines, previewEl) {
            var curLine = lines[position.lineNumber - 1] || '';

            // 헤딩 매칭 (# ~ ######)
            var headingMatch = curLine.match(/^(#{1,6})\s+(.+)/);
            if (headingMatch) {
                var level = headingMatch[1].length;
                var text = headingMatch[2].trim();
                var headings = previewEl.querySelectorAll('h' + level);
                for (var i = 0; i < headings.length; i++) {
                    if (headings[i].textContent.trim().indexOf(text.substring(0, 20)) === 0) {
                        _applyHighlight(headings[i]); return;
                    }
                }
            }

            // 일반 텍스트 — 같은 줄 텍스트로 가장 가까운 요소 찾기
            var trimmed = curLine.trim();
            if (trimmed.length > 5) {
                var snippet = trimmed.replace(/^[#*\->\d.]+\s*/, '').substring(0, 30);
                if (snippet.length > 3) {
                    var allEls = previewEl.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,td,th,blockquote');
                    for (var i = 0; i < allEls.length; i++) {
                        if (allEls[i].textContent.indexOf(snippet) >= 0) {
                            _applyHighlight(allEls[i]); return;
                        }
                    }
                }
            }
        }

        function _findByTagAndText(tagName, textAfterTag, textBefore, previewEl) {
            var text = (textAfterTag || '').trim();
            var elements = previewEl.querySelectorAll(tagName);
            for (var i = 0; i < elements.length; i++) {
                if (text && elements[i].textContent.trim().indexOf(text) === 0) {
                    _applyHighlight(elements[i]); return;
                }
            }
            // 순서 기반 폴백
            var regex = new RegExp('<' + tagName + '[^>]*>', 'gi');
            var allBefore = textBefore.match(regex) || [];
            var idx = allBefore.length - 1;
            if (elements[idx]) _applyHighlight(elements[idx]);
        }

        function _applyHighlight(el) {
            el.classList.add('editor-highlight');
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        /* 프리뷰 클릭 → 소스 이동 */
        function navigateToSource(element, previewEl) {
            if (!state.editor) return;
            var source = state.editor.getValue();
            var tagName = element.tagName.toLowerCase();
            var text = element.textContent.trim().substring(0, 60);
            var id = element.id;
            var line = 0;

            if (cfg.language === 'html') {
                line = _findLineHTML(source, tagName, text, id, element, previewEl);
            } else {
                line = _findLineMarkdown(source, tagName, text, element, previewEl);
            }

            if (line) {
                state.editor.revealLineInCenter(line);
                state.editor.setPosition({ lineNumber: line, column: 1 });
                state.editor.focus();
                var prev = previewEl.querySelector('.editor-highlight');
                if (prev) prev.classList.remove('editor-highlight');
                element.classList.add('editor-highlight');
            }
        }

        function _findLineHTML(source, tagName, text, id, element, previewEl) {
            var lines = source.split('\n');
            // 1) ID
            if (id) {
                var idPat = new RegExp('id=["\']' + id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '["\']');
                for (var i = 0; i < lines.length; i++) {
                    if (idPat.test(lines[i])) return i + 1;
                }
            }
            // 2) 태그 + 텍스트
            if (text) {
                var esc = text.substring(0, 30).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                var pat = new RegExp('<' + tagName + '[^>]*>[^<]*' + esc);
                for (var i = 0; i < lines.length; i++) {
                    if (pat.test(lines[i])) return i + 1;
                }
            }
            // 3) 순서 기반
            var allElements = previewEl.querySelectorAll(tagName);
            var idx = Array.from(allElements).indexOf(element);
            if (idx >= 0) {
                var count = 0;
                var tp = new RegExp('<' + tagName + '[\\s>]', 'i');
                for (var i = 0; i < lines.length; i++) {
                    if (tp.test(lines[i])) {
                        if (count === idx) return i + 1;
                        count++;
                    }
                }
            }
            return 0;
        }

        function _findLineMarkdown(source, tagName, text, element, previewEl) {
            var lines = source.split('\n');
            var snippet = text.substring(0, 40);

            // 헤딩 → # 라인 찾기
            if (/^h[1-6]$/.test(tagName)) {
                var level = parseInt(tagName[1]);
                var prefix = '';
                for (var j = 0; j < level; j++) prefix += '#';
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i].indexOf(prefix + ' ') === 0 && lines[i].indexOf(snippet.substring(0, 20)) > 0) {
                        return i + 1;
                    }
                }
            }

            // 일반 텍스트 매칭
            if (snippet.length > 5) {
                var s = snippet.substring(0, 25);
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i].indexOf(s) >= 0) return i + 1;
                }
            }

            return 0;
        }

        /* 폴백 에디터 (Monaco 로드 실패 시) */
        function createFallbackEditor(content, containerEl) {
            containerEl.innerHTML =
                '<textarea id="ec-fallback" style="width:100%;height:100%;padding:20px;' +
                'font-family:Consolas,monospace;font-size:14px;line-height:1.6;' +
                'border:none;resize:none;outline:none;">' + escapeHtml(content) + '</textarea>';
            var ta = document.getElementById('ec-fallback');
            ta.addEventListener('input', function () {
                state.modified = true;
                updateStatus('Modified', true);
            });
            state.editor = {
                getValue: function () { return ta.value; },
                dispose: function () {},
                layout: function () {},
            };
        }

        /* 자동 저장 */
        function startAutoSave() {
            if (!cfg.autoSaveInterval) return;
            document.getElementById('ec-autosave-info').textContent =
                'Auto-save: every ' + (cfg.autoSaveInterval / 1000) + 's';
            state.autoSaveTimer = setInterval(function () {
                if (state.modified) doSave(true);
            }, cfg.autoSaveInterval);
        }
        function stopAutoSave() {
            if (state.autoSaveTimer) { clearInterval(state.autoSaveTimer); state.autoSaveTimer = null; }
        }

        /* 저장 */
        async function doSave(silent) {
            if (!state.editor || typeof cfg.onSave !== 'function') return;
            var content = state.editor.getValue();
            updateStatus('Saving...', true);
            var ind = document.getElementById('ec-status-indicator');
            if (ind) ind.classList.add('saving');
            try {
                await cfg.onSave(content);
                state.modified = false;
                state.originalContent = content;
                updateStatus('Saved', false);
                if (!silent && typeof showToast === 'function') {
                    showToast('Document saved successfully', 'success');
                }
            } catch (err) {
                // save error — status bar shows 'Save failed'
                updateStatus('Save failed', true);
                if (!silent && typeof showToast === 'function') {
                    showToast('Failed to save: ' + (err.message || err), 'error');
                }
            }
            if (ind) ind.classList.remove('saving');
        }

        /* 닫기 */
        function doClose(force) {
            if (!force && state.modified) return;
            stopAutoSave();
            _modalEl.classList.remove('active');
            state.open = false;
            state.modified = false;
            state.originalContent = null;
            state.docPath = null;
            if (state.editor && state.editor.dispose) state.editor.dispose();
            state.editor = null;
            state._previewEl = null;
            clearTimeout(state.previewTimer);
            state.previewTimer = null;
            if (typeof cfg.onClose === 'function') cfg.onClose();
        }

        function closeWithConfirm() {
            if (state.modified) {
                document.getElementById('ec-confirm-title').textContent = 'Unsaved Changes';
                document.getElementById('ec-confirm-msg').textContent =
                    'You have unsaved changes. Are you sure you want to close without saving?';
                _confirmEl.classList.add('active');
            } else {
                doClose(true);
            }
        }

        /* ── 이벤트 바인딩 (1회) ── */
        var _eventsBound = false;
        function bindEvents() {
            if (_eventsBound) return;
            _eventsBound = true;

            document.getElementById('ec-fullscreen').addEventListener('click', function () {
                var c = _modalEl.querySelector('.editor-container');
                c.classList.toggle('fullscreen');
                this.title = c.classList.contains('fullscreen') ? 'Exit Fullscreen' : 'Fullscreen';
                if (state.editor && state.editor.layout) {
                    setTimeout(function () { state.editor.layout(); }, 100);
                }
            });
            document.getElementById('ec-save').addEventListener('click', function () { doSave(false); });
            document.getElementById('ec-cancel').addEventListener('click', function () { closeWithConfirm(); });
            document.getElementById('ec-close').addEventListener('click', function () { closeWithConfirm(); });
            _modalEl.addEventListener('click', function (e) {
                if (e.target === _modalEl) closeWithConfirm();
            });

            document.addEventListener('keydown', function (e) {
                if (!state.open) return;
                if (e.key === 'Escape') {
                    var c = _modalEl.querySelector('.editor-container');
                    if (c && c.classList.contains('fullscreen')) {
                        c.classList.remove('fullscreen');
                        document.getElementById('ec-fullscreen').title = 'Fullscreen';
                        return;
                    }
                    closeWithConfirm();
                }
                if (e.ctrlKey && e.key === 's') {
                    e.preventDefault();
                    doSave(false);
                }
            });

            document.getElementById('ec-confirm-yes').addEventListener('click', function () {
                _confirmEl.classList.remove('active');
                doClose(true);
            });
            document.getElementById('ec-confirm-no').addEventListener('click', function () {
                _confirmEl.classList.remove('active');
            });

            // 다크/라이트 테마 전환 시 Monaco 테마 동기화
            new MutationObserver(function () {
                if (!state.open || !state.editor) return;
                var isDark = document.body.getAttribute('data-theme') === 'dark';
                monaco.editor.setTheme(isDark ? 'vs-dark' : 'vs');
            }).observe(document.body, { attributes: true, attributeFilter: ['data-theme'] });
        }

        bindEvents();

        /* ── 공개 API ── */
        return {
            /** 에디터 열기 */
            open: function (content, docPath) {
                state.docPath = docPath || '';
                state.originalContent = content;
                state.modified = false;

                document.getElementById('ec-title').textContent = cfg.title;
                document.getElementById('ec-doc-path').textContent = docPath || '';

                // 분할 뷰 빌드
                var inner = document.getElementById('ec-body-inner');
                // critical flex 속성 — CSS 캐시 지연에 의존하지 않도록 인라인 보장
                inner.style.overflow = 'hidden';
                inner.style.minHeight = '0';
                inner.innerHTML =
                    '<div class="editor-loading-overlay" id="ec-loading">' +
                        '<div class="spinner spinner-lg"></div>' +
                        '<div class="loading-text">Loading editor...</div>' +
                    '</div>' +
                    '<div class="monaco-split-container">' +
                        '<div class="monaco-editor-pane" style="min-height:0">' +
                            '<div class="pane-header">' + escapeHtml(cfg.sourceLabel) + '</div>' +
                            '<div id="ec-monaco" style="flex:1;min-height:0"></div>' +
                        '</div>' +
                        '<div class="monaco-split-handle" id="ec-split-handle"></div>' +
                        '<div class="monaco-preview-pane" style="min-height:0">' +
                            '<div class="pane-header">' + escapeHtml(cfg.previewLabel) + '</div>' +
                            '<div id="ec-preview" class="' + (cfg.previewClass || '') + '" style="flex:1;min-height:0;overflow:auto"></div>' +
                        '</div>' +
                    '</div>';

                initSplitResize(inner.querySelector('.monaco-split-container'));

                _modalEl.classList.add('active');
                state.open = true;
                updateStatus('Ready', false);

                var editorEl = document.getElementById('ec-monaco');
                var previewEl = document.getElementById('ec-preview');

                // Monaco 로드
                loadMonaco(cfg.monacoBasePath).then(function () {
                    createMonacoInstance(content, editorEl, previewEl);
                    // 레이아웃 안정화 (CSS 적용 타이밍 보장)
                    setTimeout(function () {
                        if (state.editor && state.editor.layout) state.editor.layout();
                    }, 50);
                    // 로딩 오버레이 제거
                    var overlay = document.getElementById('ec-loading');
                    if (overlay) {
                        overlay.style.opacity = '0';
                        setTimeout(function () { overlay.remove(); }, 300);
                    }
                }).catch(function (err) {
                    // Monaco load failed — fallback to textarea
                    createFallbackEditor(content, inner);
                    var overlay = document.getElementById('ec-loading');
                    if (overlay) overlay.remove();
                });

                startAutoSave();
            },

            /** 에디터 닫기 */
            close: function () { doClose(true); },

            /** 확인 후 닫기 */
            closeWithConfirm: function () { closeWithConfirm(); },

            /** 저장 */
            save: function (silent) { return doSave(silent); },

            /** 현재 열려있는지 */
            isOpen: function () { return state.open; },

            /** 변경 여부 */
            isModified: function () { return state.modified; },

            /** 현재 편집 내용 */
            getValue: function () { return state.editor ? state.editor.getValue() : null; },

            /** Monaco 인스턴스 직접 접근 (고급) */
            getMonaco: function () { return state.editor; },
        };
    }

    return { create: create };
})();
