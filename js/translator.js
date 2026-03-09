    (function() {
        'use strict';

        // ── PDF.js 설정 ──
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'js/lib/pdfjs/pdf.worker.min.js';

        var API = (typeof AUTH_CONFIG !== 'undefined' && AUTH_CONFIG.backendUrl)
            ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';

        // ── Platform Header ──
        var $pageNavSource = document.getElementById('page-nav');
        $pageNavSource.style.display = '';

        var header = initPlatformHeader({
            title: 'Translator',
            currentSystem: 'translator',
            navItems: [
                { id: 'back-list', label: 'Home', hidden: true },
                { id: 'search-trigger', label: 'Search', onClick: function() { openSearchOverlay(); } },
            ],
            midSlot: $pageNavSource,
            showThemeToggle: true,
            onAuth: function(user) {
                currentUser = user;
                document.body.style.visibility = 'visible';
                document.body.classList.add('fade-in');
                loadDocuments();
                loadModels();
            }
        });

        // ── 푸터 ──
        if (typeof initPlatformFooter === 'function') {
            initPlatformFooter('translator-footer');
        }

        // ── 테마 토글 ──
        var $themeToggle = document.getElementById('theme-toggle');
        if ($themeToggle) {
            $themeToggle.addEventListener('click', function() {
                var isDark = document.body.dataset.theme === 'dark';
                document.body.dataset.theme = isDark ? 'light' : 'dark';
                localStorage.setItem('theme', isDark ? 'light' : 'dark');
            });
        }

        var $backList = header.nav['back-list'];
        $backList.addEventListener('click', function() { showList(); });

        // ══════════════════════════════════════
        // State
        // ══════════════════════════════════════
        var currentUser = null;
        var currentDocId = null;
        var currentPage = 1;
        var totalPages = 1;
        var modelsList = [];
        var defaultModel = '';
        var pageStatusCache = {};  // page_num → { status, ... }
        var annotationsCache = null; // { highlights: [...] } — 문서 단위 캐시
        var hasLegacyTranslation = false;
        var pollingTimer = null;

        // PDF.js state — left (original)
        var leftPdfDoc = null;
        var leftRenderTask = null;

        // PDF.js state — right (translation)
        var rightPdfDoc = null;
        var rightRenderTask = null;
        var legacyPdfDoc = null;  // 레거시 translated.pdf 캐시

        // Zoom
        var zoom = 1.0;
        var ZOOM_STEP = 0.1;
        var ZOOM_MIN = 0.5;
        var ZOOM_MAX = 3.0;

        // Scroll sync
        var scrollSyncEnabled = true;
        var scrollSyncing = false;  // 재진입 방지

        // ── DOM refs ──
        var $viewList       = document.getElementById('view-list');
        var $viewViewer     = document.getElementById('view-viewer');
        var $docGrid        = document.getElementById('doc-grid');
        var $uploadZone     = document.getElementById('upload-zone');
        var $fileInput      = document.getElementById('file-input');
        var $pageInfo       = document.getElementById('page-info');
        var $pagePrev       = document.getElementById('page-prev');
        var $pageNext       = document.getElementById('page-next');
        var $zoomLevel      = document.getElementById('zoom-level');
        var $zoomIn         = document.getElementById('zoom-in');
        var $zoomOut        = document.getElementById('zoom-out');
        var $scrollSyncBtn  = document.getElementById('scroll-sync-btn');

        // Left panel
        var $panelLeft      = document.getElementById('panel-left');
        var $leftCanvas     = document.getElementById('left-canvas');
        var $leftContainer  = document.getElementById('left-page-container');
        var $leftTextLayer  = document.getElementById('left-text-layer');
        var $leftAnnotationLayer = document.getElementById('left-annotation-layer');

        // Right panel
        var $panelRight     = document.getElementById('panel-right');
        var $rightCanvas    = document.getElementById('right-canvas');
        var $rightContainer = document.getElementById('right-page-container');
        var $rightTextLayer = document.getElementById('right-text-layer');
        var $rightAnnotationLayer = document.getElementById('right-annotation-layer');
        var $rightPlaceholder = document.getElementById('right-placeholder');

        // 마킹 플로팅 위젯
        var $markingFloat = document.getElementById('marking-float');
        var $mfBody  = document.getElementById('mf-body');
        var $mfBadge = document.getElementById('mf-badge');
        var $mfCount = document.getElementById('mf-count');

        // Toolbar
        var $toolbarStatus  = document.getElementById('toolbar-page-status');
        var $modelSelect    = document.getElementById('model-select');
        var $translateBtn   = document.getElementById('translate-page-btn');
        var $rangeBtn       = document.getElementById('range-translate-btn');
        var $cancelBtn      = document.getElementById('cancel-page-btn');

        // Engine radio + font scale
        var $engineRadio    = document.getElementById('engine-radio');
        var $fontControls   = document.getElementById('font-scale-controls');
        var $fontScaleDown  = document.getElementById('font-scale-down');
        var $fontScaleUp    = document.getElementById('font-scale-up');
        var $fontScaleValue = document.getElementById('font-scale-value');

        var translateEngine = 'pdf'; // 'pdf' | 'text'
        var textFontScale   = parseFloat(localStorage.getItem('tt-font-scale') || '1.0');
        var textPageStatusCache = {}; // 텍스트 번역 상태 캐시 (pdf 캐시와 독립)

        // Range dialog
        var $rangeOverlay   = document.getElementById('range-dialog-overlay');
        var $rangeStart     = document.getElementById('range-start');
        var $rangeEnd       = document.getElementById('range-end');
        var $rangeError     = document.getElementById('range-error');
        var $rangeCancelBtn = document.getElementById('range-cancel-btn');
        var $rangeSubmitBtn = document.getElementById('range-submit-btn');

        // ══════════════════════════════════════
        // Upload
        // ══════════════════════════════════════

        $uploadZone.addEventListener('click', function() { $fileInput.click(); });
        $fileInput.addEventListener('change', function() {
            if ($fileInput.files.length) uploadFile($fileInput.files[0]);
        });
        $uploadZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            $uploadZone.classList.add('dragover');
        });
        $uploadZone.addEventListener('dragleave', function() {
            $uploadZone.classList.remove('dragover');
        });
        $uploadZone.addEventListener('drop', function(e) {
            e.preventDefault();
            $uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
        });

        function uploadFile(file) {
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                alert('PDF 파일만 업로드할 수 있습니다.');
                return;
            }
            var formData = new FormData();
            formData.append('file', file);

            $uploadZone.style.pointerEvents = 'none';
            $uploadZone.querySelector('.upload-zone-text').textContent = '업로드 중...';

            fetch(API + '/api/translator/upload', {
                method: 'POST',
                body: formData,
                credentials: 'include',
            }).then(function(resp) {
                if (!resp.ok) return resp.json().then(function(e) { throw new Error(e.detail || 'Upload failed'); });
                return resp.json();
            }).then(function() {
                $fileInput.value = '';
                loadDocuments();
            }).catch(function(err) {
                alert('업로드 오류: ' + err.message);
            }).finally(function() {
                $uploadZone.style.pointerEvents = '';
                $uploadZone.querySelector('.upload-zone-text').textContent = 'PDF 파일을 드래그하거나 클릭하여 업로드';
            });
        }

        // ══════════════════════════════════════
        // 모델 목록
        // ══════════════════════════════════════

        function loadModels() {
            fetch(API + '/api/translator/models', { credentials: 'include' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var models = (data.models || []).filter(function(m) {
                        var name = m.name || '';
                        return name.indexOf('embed') === -1 && name.indexOf('bge') === -1
                            && name.indexOf('rerank') === -1;
                    });
                    modelsList = models.map(function(m) { return m.name; });

                    fetch(API + '/api/settings/public', { credentials: 'include' })
                        .then(function(r) { return r.json(); })
                        .catch(function() { return {}; })
                        .then(function(pub) {
                            defaultModel = '';
                            populateModelSelect();
                        });
                })
                .catch(function() {
                    modelsList = [];
                });
        }

        function populateModelSelect() {
            $modelSelect.innerHTML = '';
            modelsList.forEach(function(name) {
                var opt = document.createElement('option');
                opt.value = name;
                opt.textContent = name;
                if (name === (defaultModel || modelsList[0])) opt.selected = true;
                $modelSelect.appendChild(opt);
            });
            if (modelsList.length === 0) {
                var opt = document.createElement('option');
                opt.value = '';
                opt.textContent = '모델 없음';
                $modelSelect.appendChild(opt);
            }
        }

        // ══════════════════════════════════════
        // Document List
        // ══════════════════════════════════════

        function loadDocuments() { loadTreeData(); }

        function renderDocGrid(docs) {
            if (!docs.length) {
                $docGrid.innerHTML = '<div class="doc-empty">워크스페이스가 비어 있습니다.<br>PDF를 업로드하거나, 내 문서에서 드래그하세요.</div>';
                return;
            }

            $docGrid.innerHTML = '';
            docs.forEach(function(doc) {
                var card = createDocCard(doc);
                $docGrid.appendChild(card);
            });
        }

        function createDocCard(doc) {
            var card = document.createElement('div');
            card.className = 'doc-card';
            card.setAttribute('data-doc-id', doc.id);

            var title = document.createElement('div');
            title.className = 'doc-card-title';
            var titleText = document.createElement('span');
            titleText.textContent = doc.title || doc.filename;
            title.title = doc.title || doc.filename;
            title.appendChild(titleText);

            var editBtn = document.createElement('button');
            editBtn.className = 'title-edit-btn';
            editBtn.title = '이름 변경';
            editBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>';
            editBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                startTitleEdit(title, titleText, doc);
            });
            title.appendChild(editBtn);
            card.appendChild(title);

            var meta = document.createElement('div');
            meta.className = 'doc-card-meta';
            meta.textContent = (doc.total_pages || doc.pages || 0) + '페이지';
            if (doc.uploaded_at) {
                meta.textContent += ' · ' + formatDate(doc.uploaded_at);
            }
            card.appendChild(meta);

            // 상태 표시
            var statusEl = document.createElement('div');
            statusEl.className = 'doc-card-status';
            var translated = doc.translated_pages || 0;
            var total = doc.total_pages || doc.pages || 0;
            if (doc.has_legacy_translation) {
                statusEl.classList.add('status-done');
                statusEl.textContent = '번역완료 (전체)';
            } else if (translated > 0) {
                statusEl.classList.add('status-partial');
                statusEl.textContent = translated + '/' + total + ' 페이지 번역됨';
            } else {
                statusEl.textContent = '준비됨';
            }
            card.appendChild(statusEl);

            // 액션
            var actions = document.createElement('div');
            actions.className = 'doc-card-actions';

            var openBtn = document.createElement('button');
            openBtn.className = 'card-btn primary';
            openBtn.textContent = '열기';
            openBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                openViewer(doc.id, doc.total_pages || doc.pages || 1);
            });
            actions.appendChild(openBtn);

            var deleteBtn = document.createElement('button');
            deleteBtn.className = 'card-btn danger';
            deleteBtn.textContent = '삭제';
            deleteBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (!confirm((doc.title || doc.filename) + ' 문서를 삭제하시겠습니까?')) return;
                fetch(API + '/api/translator/document/' + doc.id, {
                    method: 'DELETE',
                    credentials: 'include',
                }).then(function() { loadDocuments(); });
            });
            actions.appendChild(deleteBtn);

            card.appendChild(actions);

            // 카드 클릭 → 뷰어
            card.addEventListener('click', function(e) {
                if (e.target.tagName === 'BUTTON') return;
                openViewer(doc.id, doc.total_pages || doc.pages || 1);
            });

            return card;
        }

        function startTitleEdit(titleDiv, titleSpan, doc) {
            var input = document.createElement('input');
            input.type = 'text';
            input.className = 'title-edit-input';
            input.value = doc.title || doc.filename;

            var editBtn = titleDiv.querySelector('.title-edit-btn');
            titleSpan.style.display = 'none';
            if (editBtn) editBtn.style.display = 'none';
            titleDiv.appendChild(input);
            input.focus();
            input.select();

            // 드래그 방지 (편집 중 카드 드래그 차단)
            var card = titleDiv.closest('.doc-card');
            if (card) card.setAttribute('draggable', 'false');

            var finished = false;
            function finish(save) {
                if (finished) return;
                finished = true;
                var newTitle = input.value.trim();
                if (input.parentNode) input.parentNode.removeChild(input);
                titleSpan.style.display = '';
                if (editBtn) editBtn.style.display = '';
                if (card) card.setAttribute('draggable', 'true');

                if (save && newTitle && newTitle !== (doc.title || doc.filename)) {
                    fetch(API + '/api/translator/document/' + doc.id, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ title: newTitle }),
                    }).then(function(r) {
                        if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail); });
                        loadTreeData(); // 카드 + 트리 동기화
                    }).catch(function(err) { alert('이름 변경 실패: ' + err.message); });
                }
            }

            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); finish(true); }
                if (e.key === 'Escape') { finish(false); }
            });
            input.addEventListener('blur', function() { finish(true); });
            input.addEventListener('click', function(e) { e.stopPropagation(); });
        }

        // ══════════════════════════════════════
        // Viewer
        // ══════════════════════════════════════

        function openViewer(docId, pages) {
            currentDocId = docId;
            totalPages = pages || 1;
            currentPage = 1;
            pageStatusCache = {};
            hasLegacyTranslation = false;
            zoom = 1.0;
            $zoomLevel.textContent = '100%';

            showViewer();
            annotationsCache = null;

            // 페이지 상태 요약 로드 후 렌더링
            fetchPageSummary(function() {
                loadLeftPdf();
                updateRightPanel();
                loadAnnotations(); // 마킹 데이터 로드 → renderLeftPage 내에서 렌더
            });
        }

        function showViewer() {
            $viewList.style.display = 'none';
            $viewViewer.style.display = 'flex';
            header.midSlot.classList.add('visible');
            header.nav['back-list'].style.display = '';
            updatePageNav();
        }

        function showList() {
            $viewViewer.style.display = 'none';
            $viewList.style.display = 'flex';
            header.midSlot.classList.remove('visible');
            header.nav['back-list'].style.display = 'none';
            currentDocId = null;
            annotationsCache = null;
            stopPolling();
            destroyPdfs();
            loadDocuments();
        }

        function destroyPdfs() {
            if (leftPdfDoc) { leftPdfDoc.destroy(); leftPdfDoc = null; }
            if (rightPdfDoc && rightPdfDoc !== legacyPdfDoc) { rightPdfDoc.destroy(); }
            rightPdfDoc = null;
            if (legacyPdfDoc) { legacyPdfDoc.destroy(); legacyPdfDoc = null; }
            if (leftRenderTask) { leftRenderTask.cancel(); leftRenderTask = null; }
            if (rightRenderTask) { rightRenderTask.cancel(); rightRenderTask = null; }
        }

        function fetchPageSummary(cb) {
            fetch(API + '/api/translator/document/' + currentDocId + '/pages', { credentials: 'include' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    totalPages = data.pages || totalPages;
                    hasLegacyTranslation = data.has_legacy_translation || false;
                    pageStatusCache = data.page_status || {};
                    updatePageNav();
                    if (cb) cb();
                })
                .catch(function() { if (cb) cb(); });
        }

        // ── Left Panel: Original PDF ──

        function loadLeftPdf() {
            if (leftPdfDoc) { leftPdfDoc.destroy(); leftPdfDoc = null; }
            var url = API + '/api/translator/pdf/' + currentDocId;
            pdfjsLib.getDocument({ url: url, withCredentials: true }).promise.then(function(pdf) {
                leftPdfDoc = pdf;
                totalPages = pdf.numPages;
                updatePageNav();
                renderLeftPage(currentPage);
            }).catch(function(err) {
                console.error('[PDF.js] left load error:', err);
            });
        }

        function renderLeftPage(pageNum) {
            if (!leftPdfDoc) return;
            if (leftRenderTask) { leftRenderTask.cancel(); leftRenderTask = null; }

            leftPdfDoc.getPage(pageNum).then(function(page) {
                var wrapWidth = $panelLeft.clientWidth - 32;
                var viewport = page.getViewport({ scale: 1 });
                var fitScale = wrapWidth / viewport.width;
                var baseScale = Math.min(fitScale, 1.5);
                var scale = baseScale * zoom;
                var scaledViewport = page.getViewport({ scale: scale });

                $leftCanvas.width = scaledViewport.width;
                $leftCanvas.height = scaledViewport.height;
                $leftCanvas.style.width = scaledViewport.width + 'px';
                $leftCanvas.style.height = scaledViewport.height + 'px';

                $leftContainer.style.width = scaledViewport.width + 'px';
                $leftContainer.style.height = scaledViewport.height + 'px';

                $leftTextLayer.innerHTML = '';
                $leftTextLayer.style.width = scaledViewport.width + 'px';
                $leftTextLayer.style.height = scaledViewport.height + 'px';
                $leftTextLayer.style.setProperty('--scale-factor', scale);

                $leftAnnotationLayer.style.width = scaledViewport.width + 'px';
                $leftAnnotationLayer.style.height = scaledViewport.height + 'px';

                var ctx = $leftCanvas.getContext('2d');
                leftRenderTask = page.render({ canvasContext: ctx, viewport: scaledViewport });
                leftRenderTask.promise.then(function() {
                    leftRenderTask = null;
                    return page.getTextContent();
                }).then(function(textContent) {
                    if (textContent) {
                        pdfjsLib.renderTextLayer({
                            textContentSource: textContent,
                            container: $leftTextLayer,
                            viewport: scaledViewport,
                            textDivs: [],
                        });
                    }
                    // 마킹 복원
                    if (typeof renderAnnotations === 'function') renderAnnotations();
                }).catch(function() { leftRenderTask = null; });
            });
        }

        // ── Right Panel: Translation PDF or Placeholder ──

        function updateRightPanel() {
            if (translateEngine === 'text') {
                // 텍스트 번역 모드
                var tps = textPageStatusCache[String(currentPage)];
                var tStatus = tps ? tps.status : 'pending';

                if (tStatus === 'done') {
                    showRightTextTranslatedPage();
                    updateToolbarForStatus('done');
                } else if (tStatus === 'translating') {
                    showRightTranslating(tps);
                    updateToolbarForStatus('translating');
                    startTextPolling();
                } else if (tStatus === 'error') {
                    showRightError(tps);
                    updateToolbarForStatus('error');
                } else {
                    // 서버에서 기존 텍스트 번역 결과 확인
                    fetch(API + '/api/translator/text-translate/' + currentDocId + '/page/' + currentPage + '/status', {
                        credentials: 'include',
                    }).then(function(r) {
                        if (!r.ok) throw new Error('not found');
                        return r.json();
                    }).then(function(st) {
                        if (st.status === 'done' || st.status === 'translating' || st.status === 'error') {
                            textPageStatusCache[String(currentPage)] = st;
                        }
                        if (st.status === 'done') {
                            showRightTextTranslatedPage();
                            updateToolbarForStatus('done');
                        } else if (st.status === 'translating') {
                            showRightTranslating(st);
                            updateToolbarForStatus('translating');
                            startTextPolling();
                        } else {
                            showRightPending();
                            updateToolbarForStatus('pending');
                        }
                    }).catch(function() {
                        showRightPending();
                        updateToolbarForStatus('pending');
                    });
                }
                return;
            }

            // PDF 번역 모드 (기존)
            var ps = pageStatusCache[String(currentPage)];
            var status = ps ? ps.status : 'pending';

            // 레거시 통번역이 있으면 그걸 표시
            if (hasLegacyTranslation && status === 'pending') {
                showRightLegacy();
                updateToolbarForStatus('legacy');
                return;
            }

            if (status === 'done') {
                showRightTranslatedPage();
                updateToolbarForStatus('done');
            } else if (status === 'translating') {
                showRightTranslating(ps);
                updateToolbarForStatus('translating');
                startPolling();
            } else if (status === 'error') {
                showRightError(ps);
                updateToolbarForStatus('error');
            } else {
                showRightPending();
                updateToolbarForStatus('pending');
            }
        }

        function showRightPending() {
            $rightContainer.style.display = 'none';
            $rightPlaceholder.style.display = 'flex';
            $rightPlaceholder.innerHTML =
                '<div class="placeholder-icon">&#128221;</div>' +
                '<div class="placeholder-text">이 페이지는 아직 번역되지 않았습니다</div>' +
                '<div class="placeholder-hint">아래 "이 페이지 번역" 버튼을 눌러 시작하세요 (~30초)</div>';
        }

        function showRightTranslating(ps) {
            $rightContainer.style.display = 'none';
            $rightPlaceholder.style.display = 'flex';
            var stage = (ps && ps.progress_stage) || '번역 준비 중...';
            $rightPlaceholder.innerHTML =
                '<div class="page-spinner"></div>' +
                '<div class="placeholder-text">' + escHtml(stage) + '</div>';
        }

        function showRightError(ps) {
            $rightContainer.style.display = 'none';
            $rightPlaceholder.style.display = 'flex';
            var errMsg = (ps && ps.error) || '알 수 없는 오류';
            $rightPlaceholder.innerHTML =
                '<div class="placeholder-icon">&#9888;&#65039;</div>' +
                '<div class="placeholder-error">' + escHtml(errMsg) + '</div>' +
                '<div class="placeholder-hint">"이 페이지 번역" 버튼으로 재시도하세요</div>';
        }

        function showRightTranslatedPage() {
            // 로딩 상태 표시 (placeholder 유지)
            var textEl = $rightPlaceholder.querySelector('.placeholder-text');
            var hintEl = $rightPlaceholder.querySelector('.placeholder-hint');
            if (textEl) textEl.textContent = '번역 PDF 로드 중...';
            if (hintEl) hintEl.textContent = '';
            $rightPlaceholder.style.display = 'flex';
            $rightContainer.style.display = 'none';

            // 페이지별 번역 PDF 로드 (1페이지짜리)
            if (rightPdfDoc && rightPdfDoc !== legacyPdfDoc) { rightPdfDoc.destroy(); }
            rightPdfDoc = null;
            var url = API + '/api/translator/translated-pdf/' + currentDocId + '/page/' + currentPage;
            pdfjsLib.getDocument({ url: url, withCredentials: true }).promise.then(function(pdf) {
                rightPdfDoc = pdf;
                $rightPlaceholder.style.display = 'none';
                $rightContainer.style.display = 'inline-block';
                renderRightPage(1); // 1페이지짜리 PDF의 첫 페이지
            }).catch(function(err) {
                console.error('[PDF.js] right page load error:', err);
                showRightError({ error: 'PDF 로드 실패' });
            });
        }

        function showRightTextTranslatedPage() {
            // 로딩 상태 표시 (placeholder 유지)
            var textEl = $rightPlaceholder.querySelector('.placeholder-text');
            var hintEl = $rightPlaceholder.querySelector('.placeholder-hint');
            if (textEl) textEl.textContent = '번역 PDF 로드 중...';
            if (hintEl) hintEl.textContent = '';
            $rightPlaceholder.style.display = 'flex';
            $rightContainer.style.display = 'none';

            // 텍스트 번역 PDF 로드
            if (rightPdfDoc && rightPdfDoc !== legacyPdfDoc) { rightPdfDoc.destroy(); }
            rightPdfDoc = null;
            var url = API + '/api/translator/text-translated-pdf/' + currentDocId + '/page/' + currentPage;
            pdfjsLib.getDocument({ url: url, withCredentials: true }).promise.then(function(pdf) {
                rightPdfDoc = pdf;
                $rightPlaceholder.style.display = 'none';
                $rightContainer.style.display = 'inline-block';
                renderRightPage(1);
            }).catch(function(err) {
                console.error('[PDF.js] text-translated page load error:', err);
                showRightError({ error: 'PDF 로드 실패' });
            });
        }

        function showRightLegacy() {
            $rightPlaceholder.style.display = 'none';
            $rightContainer.style.display = 'inline-block';

            // 레거시 translated.pdf 캐시 재사용 (매 페이지 전환 시 재다운로드 방지)
            if (legacyPdfDoc) {
                if (rightPdfDoc !== legacyPdfDoc) {
                    if (rightPdfDoc) { rightPdfDoc.destroy(); }
                    rightPdfDoc = legacyPdfDoc;
                }
                renderRightPage(currentPage);
                return;
            }

            if (rightPdfDoc) { rightPdfDoc.destroy(); rightPdfDoc = null; }
            var url = API + '/api/translator/translated-pdf/' + currentDocId;
            pdfjsLib.getDocument({ url: url, withCredentials: true }).promise.then(function(pdf) {
                legacyPdfDoc = pdf;
                rightPdfDoc = pdf;
                renderRightPage(currentPage);
            }).catch(function(err) {
                console.error('[PDF.js] right legacy load error:', err);
                hasLegacyTranslation = false;
                showRightPending();
                updateToolbarForStatus('pending');
            });
        }

        function renderRightPage(pageNum) {
            if (!rightPdfDoc) return;
            if (rightRenderTask) { rightRenderTask.cancel(); rightRenderTask = null; }

            rightPdfDoc.getPage(pageNum).then(function(page) {
                var wrapWidth = $panelRight.clientWidth - 32;
                var viewport = page.getViewport({ scale: 1 });
                var fitScale = wrapWidth / viewport.width;
                var baseScale = Math.min(fitScale, 1.5);
                var scale = baseScale * zoom;
                var scaledViewport = page.getViewport({ scale: scale });

                $rightCanvas.width = scaledViewport.width;
                $rightCanvas.height = scaledViewport.height;
                $rightCanvas.style.width = scaledViewport.width + 'px';
                $rightCanvas.style.height = scaledViewport.height + 'px';

                $rightContainer.style.width = scaledViewport.width + 'px';
                $rightContainer.style.height = scaledViewport.height + 'px';

                $rightTextLayer.innerHTML = '';
                $rightTextLayer.style.width = scaledViewport.width + 'px';
                $rightTextLayer.style.height = scaledViewport.height + 'px';
                $rightTextLayer.style.setProperty('--scale-factor', scale);

                $rightAnnotationLayer.style.width = scaledViewport.width + 'px';
                $rightAnnotationLayer.style.height = scaledViewport.height + 'px';

                var ctx = $rightCanvas.getContext('2d');
                rightRenderTask = page.render({ canvasContext: ctx, viewport: scaledViewport });
                rightRenderTask.promise.then(function() {
                    rightRenderTask = null;
                    return page.getTextContent();
                }).then(function(textContent) {
                    if (textContent) {
                        pdfjsLib.renderTextLayer({
                            textContentSource: textContent,
                            container: $rightTextLayer,
                            viewport: scaledViewport,
                            textDivs: [],
                        });
                    }
                    // 우측 마킹 동기화
                    if (typeof renderAnnotationsRight === 'function') renderAnnotationsRight();
                }).catch(function() { rightRenderTask = null; });
            });
        }

        // ── Toolbar status ──

        function updateToolbarForStatus(status) {
            if (status === 'pending' || status === 'error') {
                $translateBtn.style.display = '';
                $translateBtn.disabled = false;
                $translateBtn.textContent = status === 'error' ? '재시도' : '이 페이지 번역';
                $rangeBtn.style.display = translateEngine === 'text' ? 'none' : '';
                $cancelBtn.style.display = 'none';
                $modelSelect.style.display = '';
                $toolbarStatus.textContent = '';
                $fontScaleDown.disabled = false;
                $fontScaleUp.disabled = false;
            } else if (status === 'translating') {
                $translateBtn.style.display = 'none';
                $rangeBtn.style.display = 'none';
                $cancelBtn.style.display = '';
                $modelSelect.style.display = 'none';
                $toolbarStatus.textContent = '번역 중...';
                $fontScaleDown.disabled = true;
                $fontScaleUp.disabled = true;
            } else if (status === 'done') {
                $translateBtn.style.display = '';
                $translateBtn.textContent = '재번역';
                $translateBtn.disabled = false;
                $fontScaleDown.disabled = false;
                $fontScaleUp.disabled = false;
                $rangeBtn.style.display = translateEngine === 'text' ? 'none' : '';
                $cancelBtn.style.display = 'none';
                $modelSelect.style.display = '';
                var ps = translateEngine === 'text'
                    ? textPageStatusCache[String(currentPage)]
                    : pageStatusCache[String(currentPage)];
                var info = translateEngine === 'text' ? '[텍스트] ' : '';
                if (ps) {
                    if (ps.model) info += ps.model;
                    if (ps.elapsed_sec) info += ', ' + ps.elapsed_sec + '초';
                    if (ps.batch) info += ' (' + ps.batch + 'p 일괄)';
                }
                $toolbarStatus.textContent = info;
                if (translateEngine === 'text') updateFontScaleDisplay();
            } else if (status === 'legacy') {
                $translateBtn.style.display = '';
                $translateBtn.textContent = '페이지 번역';
                $translateBtn.disabled = false;
                $rangeBtn.style.display = '';
                $cancelBtn.style.display = 'none';
                $modelSelect.style.display = '';
                $toolbarStatus.textContent = '통번역 (레거시)';
            }
        }

        // ── Engine radio ──

        $engineRadio.addEventListener('change', function(e) {
            if (e.target.name !== 'translate-engine') return;
            translateEngine = e.target.value;
            $fontControls.style.display = translateEngine === 'text' ? '' : 'none';
            updateFontScaleDisplay();

            // 모드 전환 시 해당 모드의 캐시된 결과 표시
            updateRightPanel();
        });

        function updateFontScaleDisplay() {
            var pct = Math.round(textFontScale * 100) + '%';
            // 번역 완료 상태에서 현재 스케일과 baked 스케일이 다르면 표시
            var tps = textPageStatusCache[String(currentPage)];
            if (tps && tps.status === 'done' && tps.font_scale) {
                var bakedMultiplier = Math.round((tps.font_scale / 0.75) * 100) / 100;
                if (Math.abs(bakedMultiplier - textFontScale) > 0.01) {
                    pct += '*';
                    $translateBtn.textContent = '이 크기로 재번역';
                } else if ($translateBtn.textContent === '이 크기로 재번역') {
                    $translateBtn.textContent = '재번역';
                }
            }
            $fontScaleValue.textContent = pct;
        }
        updateFontScaleDisplay();

        $fontScaleDown.addEventListener('click', function() {
            textFontScale = Math.max(0.5, Math.round((textFontScale - 0.1) * 10) / 10);
            localStorage.setItem('tt-font-scale', String(textFontScale));
            updateFontScaleDisplay();
        });

        $fontScaleUp.addEventListener('click', function() {
            textFontScale = Math.min(1.5, Math.round((textFontScale + 0.1) * 10) / 10);
            localStorage.setItem('tt-font-scale', String(textFontScale));
            updateFontScaleDisplay();
        });

        // ── Translate page button ──

        $translateBtn.addEventListener('click', function() {
            if (!currentDocId) return;
            var model = $modelSelect.value;
            $translateBtn.disabled = true;

            if (translateEngine === 'text') {
                // 텍스트 번역 모드
                var baseFontScale = 0.75; // config 기본값
                var effectiveScale = baseFontScale * textFontScale;
                fetch(API + '/api/translator/text-translate/' + currentDocId + '/page/' + currentPage, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: model, font_scale: effectiveScale }),
                    credentials: 'include',
                }).then(function(resp) {
                    if (!resp.ok) return resp.json().then(function(e) { throw new Error(e.detail); });
                    textPageStatusCache[String(currentPage)] = {
                        status: 'translating',
                        progress_stage: '번역 준비 중...',
                        model: model,
                    };
                    updateRightPanel();
                }).catch(function(err) {
                    alert('텍스트 번역 시작 실패: ' + err.message);
                    $translateBtn.disabled = false;
                });
            } else {
                // PDF 번역 모드 (기존 pdf2zh)
                fetch(API + '/api/translator/translate/' + currentDocId + '/page/' + currentPage, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: model }),
                    credentials: 'include',
                }).then(function(resp) {
                    if (!resp.ok) return resp.json().then(function(e) { throw new Error(e.detail); });
                    pageStatusCache[String(currentPage)] = {
                        status: 'translating',
                        progress_stage: '번역 준비 중...',
                        model: model,
                    };
                    updateRightPanel();
                }).catch(function(err) {
                    alert('번역 시작 실패: ' + err.message);
                    $translateBtn.disabled = false;
                });
            }
        });

        $cancelBtn.addEventListener('click', function() {
            if (!currentDocId) return;
            if (!confirm('번역을 취소하시겠습니까?')) return;

            var cancelUrl = translateEngine === 'text'
                ? API + '/api/translator/text-translate/' + currentDocId + '/page/' + currentPage + '/cancel'
                : API + '/api/translator/translate/' + currentDocId + '/page/' + currentPage + '/cancel';

            fetch(cancelUrl, { method: 'POST', credentials: 'include' })
            .then(function() {
                if (translateEngine === 'text') {
                    delete textPageStatusCache[String(currentPage)];
                } else {
                    delete pageStatusCache[String(currentPage)];
                }
                stopPolling();
                updateRightPanel();
            });
        });

        // ── Range translate dialog ──

        $rangeBtn.addEventListener('click', function() {
            $rangeStart.value = currentPage;
            $rangeEnd.value = Math.min(currentPage + 4, totalPages);
            $rangeStart.max = totalPages;
            $rangeEnd.max = totalPages;
            $rangeError.textContent = '';
            $rangeOverlay.style.display = 'block';
        });

        $rangeCancelBtn.addEventListener('click', function() {
            $rangeOverlay.style.display = 'none';
        });

        $rangeOverlay.addEventListener('click', function(e) {
            if (e.target === $rangeOverlay) $rangeOverlay.style.display = 'none';
        });

        $rangeSubmitBtn.addEventListener('click', function() {
            var start = parseInt($rangeStart.value, 10);
            var end = parseInt($rangeEnd.value, 10);

            if (isNaN(start) || isNaN(end)) {
                $rangeError.textContent = '숫자를 입력하세요';
                return;
            }
            if (start < 1 || end < 1 || start > totalPages || end > totalPages) {
                $rangeError.textContent = '페이지 범위: 1~' + totalPages;
                return;
            }
            if (end < start) {
                $rangeError.textContent = '끝 페이지가 시작보다 작습니다';
                return;
            }
            if (end - start + 1 > 5) {
                $rangeError.textContent = '최대 5페이지까지 가능합니다';
                return;
            }

            $rangeOverlay.style.display = 'none';
            var model = $modelSelect.value;

            fetch(API + '/api/translator/translate/' + currentDocId + '/pages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ page_start: start, page_end: end, model: model }),
                credentials: 'include',
            }).then(function(resp) {
                if (!resp.ok) return resp.json().then(function(e) { throw new Error(e.detail); });
                // 범위 내 모든 페이지를 translating으로
                for (var p = start; p <= end; p++) {
                    pageStatusCache[String(p)] = {
                        status: 'translating',
                        progress_stage: '번역 준비 중...',
                        model: model,
                    };
                }
                updateRightPanel();
            }).catch(function(err) {
                alert('범위 번역 시작 실패: ' + err.message);
            });
        });

        // ── Polling ──

        function startPolling() {
            stopPolling();
            pollingTimer = setInterval(function() {
                if (!currentDocId) { stopPolling(); return; }

                fetch(API + '/api/translator/translate/' + currentDocId + '/page/' + currentPage + '/status', {
                    credentials: 'include',
                }).then(function(r) { return r.json(); })
                  .then(function(ps) {
                    pageStatusCache[String(currentPage)] = ps;
                    if (ps.status === 'translating') {
                        // 진행 단계 업데이트
                        var stage = ps.progress_stage || '번역 중...';
                        var textEl = $rightPlaceholder.querySelector('.placeholder-text');
                        if (textEl) textEl.textContent = stage;
                        $toolbarStatus.textContent = stage;
                    } else {
                        // 완료/에러
                        stopPolling();
                        updateRightPanel();
                    }
                }).catch(function() {
                    stopPolling();
                });
            }, 3000);
        }

        function stopPolling() {
            if (pollingTimer) {
                clearInterval(pollingTimer);
                pollingTimer = null;
            }
        }

        // ── Text translation polling ──

        var textPollingTimer = null;

        function startTextPolling() {
            stopTextPolling();
            textPollingTimer = setInterval(function() {
                if (!currentDocId) { stopTextPolling(); return; }

                fetch(API + '/api/translator/text-translate/' + currentDocId + '/page/' + currentPage + '/status', {
                    credentials: 'include',
                }).then(function(r) { return r.json(); })
                  .then(function(st) {
                    textPageStatusCache[String(currentPage)] = st;
                    if (st.status === 'translating') {
                        var stage = st.progress_stage || '번역 중...';
                        var textEl = $rightPlaceholder.querySelector('.placeholder-text');
                        if (textEl) textEl.textContent = stage;
                        $toolbarStatus.textContent = stage;
                    } else {
                        stopTextPolling();
                        updateRightPanel();
                    }
                }).catch(function() {
                    stopTextPolling();
                });
            }, 3000);
        }

        function stopTextPolling() {
            if (textPollingTimer) {
                clearInterval(textPollingTimer);
                textPollingTimer = null;
            }
        }

        // ── Page navigation ──

        function updatePageNav() {
            $pageInfo.textContent = currentPage + ' / ' + totalPages;
            $pagePrev.disabled = currentPage <= 1;
            $pageNext.disabled = currentPage >= totalPages;
        }

        $pagePrev.addEventListener('click', function() {
            if (currentPage > 1) goToPage(currentPage - 1);
        });
        $pageNext.addEventListener('click', function() {
            if (currentPage < totalPages) goToPage(currentPage + 1);
        });

        function goToPage(page) {
            if (page < 1 || page > totalPages) return;
            hidePopover(true);
            hideActionBar(); hideAiPopover();
            stopPolling();
            stopTextPolling();
            currentPage = page;
            updatePageNav();

            // Left: 원문 렌더링
            renderLeftPage(currentPage);
            $panelLeft.scrollTop = 0;

            if (translateEngine === 'text') {
                // 텍스트 모드: updateRightPanel()이 자체적으로 서버 fetch
                updateRightPanel();
            } else if (rightPdfDoc && hasLegacyTranslation && !pageStatusCache[String(currentPage)]) {
                // 레거시 PDF 유지, 해당 페이지 렌더링
                $rightPlaceholder.style.display = 'none';
                $rightContainer.style.display = 'inline-block';
                renderRightPage(currentPage);
                updateToolbarForStatus('legacy');
            } else {
                // PDF 모드: 페이지별 상태 확인 → 서버에서 갱신
                fetch(API + '/api/translator/translate/' + currentDocId + '/page/' + currentPage + '/status', {
                    credentials: 'include',
                }).then(function(r) { return r.json(); })
                  .then(function(ps) {
                    pageStatusCache[String(currentPage)] = ps;
                    updateRightPanel();
                }).catch(function() {
                    updateRightPanel();
                });
            }

            $panelRight.scrollTop = 0;
        }

        // ── Keyboard shortcuts ──
        document.addEventListener('keydown', function(e) {
            if (!currentDocId) return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
            if (e.key === 'ArrowLeft') goToPage(currentPage - 1);
            if (e.key === 'ArrowRight') goToPage(currentPage + 1);
        });

        // ── Zoom ──
        $zoomLevel.addEventListener('click', function() {
            zoom = 1.0;
            $zoomLevel.textContent = '100%';
            rerenderBothPanels();
        });
        $zoomIn.addEventListener('click', function() {
            zoom = Math.min(ZOOM_MAX, zoom + ZOOM_STEP);
            $zoomLevel.textContent = Math.round(zoom * 100) + '%';
            rerenderBothPanels();
        });
        $zoomOut.addEventListener('click', function() {
            zoom = Math.max(ZOOM_MIN, zoom - ZOOM_STEP);
            $zoomLevel.textContent = Math.round(zoom * 100) + '%';
            rerenderBothPanels();
        });

        function rerenderBothPanels() {
            hidePopover(true);
            hideActionBar(); hideAiPopover();
            renderLeftPage(currentPage);
            // Right: 상태에 따라
            var ps = pageStatusCache[String(currentPage)];
            var status = ps ? ps.status : 'pending';
            if (status === 'done') {
                renderRightPage(1);
            } else if (hasLegacyTranslation && status === 'pending' && rightPdfDoc) {
                renderRightPage(currentPage);
            }
        }

        // ── Resize handler ──
        var resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                if (currentDocId) rerenderBothPanels();
            }, 200);
        });

        // ── Scroll Sync ──
        $scrollSyncBtn.addEventListener('click', function() {
            scrollSyncEnabled = !scrollSyncEnabled;
            $scrollSyncBtn.classList.toggle('active', scrollSyncEnabled);
        });

        function syncScroll(source, target) {
            if (!scrollSyncEnabled || scrollSyncing) return;
            scrollSyncing = true;
            var maxS = source.scrollHeight - source.clientHeight;
            var maxT = target.scrollHeight - target.clientHeight;
            if (maxS > 0 && maxT > 0) {
                var ratio = source.scrollTop / maxS;
                target.scrollTop = ratio * maxT;
            }
            scrollSyncing = false;
        }

        $panelLeft.addEventListener('scroll', function() {
            syncScroll($panelLeft, $panelRight);
        });
        $panelRight.addEventListener('scroll', function() {
            syncScroll($panelRight, $panelLeft);
        });

        // ══════════════════════════════════════
        // Annotations (마킹/형광펜)
        // ══════════════════════════════════════

        var HIGHLIGHT_COLORS = {
            yellow: 'color-yellow',
            green:  'color-green',
            red:    'color-red',
            blue:   'color-blue',
        };

        // ── 하이라이트 div 생성 ──

        function createHighlightDiv(h) {
            var colorClass = HIGHLIGHT_COLORS[h.color] || 'color-yellow';
            var group = document.createElement('div');
            group.className = 'highlight-group ' + colorClass;
            group.dataset.annId = h.id;
            var rects = h.rects || [];
            // 줄 높이 통일 (최대 높이 사용)
            var maxH = 0;
            for (var i = 0; i < rects.length; i++) {
                if (rects[i].h > maxH) maxH = rects[i].h;
            }
            var pad = 0.3; // 좌우 여백 (%)
            for (var i = 0; i < rects.length; i++) {
                var r = rects[i];
                var div = document.createElement('div');
                div.className = 'highlight ' + colorClass;
                // 첫 번째 rect + 메모 있으면 표시점
                if (i === 0 && h.memo) {
                    div.classList.add('has-memo');
                }
                div.style.left   = Math.max(0, r.x - pad) + '%';
                div.style.top    = r.y + '%';
                div.style.width  = Math.min(100 - r.x + pad, r.w + pad * 2) + '%';
                div.style.height = maxH + '%';
                div.dataset.annId = h.id;
                div.title = h.memo || h.text || '';
                group.appendChild(div);
            }
            return group;
        }

        // ── 현재 페이지 마킹 렌더 (좌측) ──

        function renderAnnotations() {
            // popover 보존: render 전 분리, render 후 재부착
            var savedPopover = $popover;
            if (savedPopover && savedPopover.parentNode) {
                savedPopover.parentNode.removeChild(savedPopover);
            }
            $leftAnnotationLayer.innerHTML = '';
            if (!annotationsCache || !annotationsCache.highlights) return;
            var page = currentPage;
            var highlights = annotationsCache.highlights;
            for (var i = 0; i < highlights.length; i++) {
                if (highlights[i].page === page) {
                    $leftAnnotationLayer.appendChild(createHighlightDiv(highlights[i]));
                }
            }
            // popover 재부착
            if (savedPopover) {
                $leftAnnotationLayer.appendChild(savedPopover);
            }
        }

        // ── 우측 마진 마커 div 생성 ──

        function createMarginMarkerDiv(h) {
            var frag = document.createDocumentFragment();
            var rects = h.rects || [];
            if (!rects.length) return frag;
            var minY = rects[0].y, maxYH = rects[0].y + rects[0].h;
            for (var i = 1; i < rects.length; i++) {
                minY = Math.min(minY, rects[i].y);
                maxYH = Math.max(maxYH, rects[i].y + rects[i].h);
            }
            var div = document.createElement('div');
            div.className = 'margin-marker ' + (HIGHLIGHT_COLORS[h.color] || 'color-yellow');
            div.style.top = minY + '%';
            div.style.height = (maxYH - minY) + '%';
            div.dataset.annId = h.id;
            div.title = h.memo || h.text || '';
            frag.appendChild(div);
            return frag;
        }

        // ── 현재 페이지 마킹 렌더 (우측 마진 마커) ──

        function renderAnnotationsRight() {
            $rightAnnotationLayer.innerHTML = '';
            if (!annotationsCache || !annotationsCache.highlights) return;
            if ($rightContainer.style.display === 'none') return;
            var page = currentPage;
            var highlights = annotationsCache.highlights;
            for (var i = 0; i < highlights.length; i++) {
                if (highlights[i].page === page) {
                    $rightAnnotationLayer.appendChild(createMarginMarkerDiv(highlights[i]));
                }
            }
        }

        // ── annotations 서버 로드 ──

        function loadAnnotations(callback) {
            if (!currentDocId) return;
            fetch(API + '/api/translator/document/' + currentDocId + '/annotations', {
                credentials: 'include',
            }).then(function(r) { return r.json(); })
              .then(function(data) {
                annotationsCache = data;
                updateMarkingBadge();
                if (callback) callback();
            }).catch(function() {
                annotationsCache = { highlights: [] };
                updateMarkingBadge();
                if (callback) callback();
            });
        }

        // ── 선택 좌표 → % 변환 ──

        function selectionToPercentRects(selection) {
            if (!selection.rangeCount) return null;
            var range = selection.getRangeAt(0);
            var clientRects = range.getClientRects();
            if (!clientRects.length) return null;

            var containerRect = $leftContainer.getBoundingClientRect();
            var cW = containerRect.width;
            var cH = containerRect.height;
            if (cW === 0 || cH === 0) return null;

            var rects = [];
            for (var i = 0; i < clientRects.length; i++) {
                var cr = clientRects[i];
                // 컨테이너 범위 내의 rect만
                var x = ((cr.left - containerRect.left) / cW) * 100;
                var y = ((cr.top - containerRect.top) / cH) * 100;
                var w = (cr.width / cW) * 100;
                var h = (cr.height / cH) * 100;
                // 매우 작은 rect 무시 (선택 아티팩트)
                if (w < 0.5 || h < 0.1) continue;
                // 비정상적으로 큰 rect 무시 (브라우저가 range 전체 bounding box 반환)
                if (h > 6) continue;
                // 컨테이너 밖 rect 무시
                if (x < -1 || y < -1 || x + w > 101 || y + h > 101) continue;
                rects.push({
                    x: Math.round(x * 100) / 100,
                    y: Math.round(y * 100) / 100,
                    w: Math.round(w * 100) / 100,
                    h: Math.round(h * 100) / 100,
                });
            }
            // 인접 rect 병합 (같은 줄의 span 여러 개 → 하나로)
            rects = mergeAdjacentRects(rects);
            return rects.length ? rects : null;
        }

        function mergeAdjacentRects(rects) {
            if (rects.length <= 1) return rects;
            // y 기준 정렬
            rects.sort(function(a, b) { return a.y - b.y || a.x - b.x; });

            // Step 1: 같은 줄 rects 그룹핑 (y 중심이 겹치면 같은 줄)
            var lines = [[rects[0]]];
            for (var i = 1; i < rects.length; i++) {
                var curr = rects[i];
                var lineRef = lines[lines.length - 1][0];
                var lineCenter = lineRef.y + lineRef.h / 2;
                var currCenter = curr.y + curr.h / 2;
                if (Math.abs(currCenter - lineCenter) < Math.max(lineRef.h, curr.h) * 0.6) {
                    lines[lines.length - 1].push(curr);
                } else {
                    lines.push([curr]);
                }
            }

            // Step 2: 각 줄을 하나의 rect로 병합 (높이 통일)
            var merged = [];
            for (var l = 0; l < lines.length; l++) {
                var lr = lines[l];
                var minX = lr[0].x, maxXW = lr[0].x + lr[0].w;
                var minY = lr[0].y, maxYH = lr[0].y + lr[0].h;
                for (var j = 1; j < lr.length; j++) {
                    minX = Math.min(minX, lr[j].x);
                    maxXW = Math.max(maxXW, lr[j].x + lr[j].w);
                    minY = Math.min(minY, lr[j].y);
                    maxYH = Math.max(maxYH, lr[j].y + lr[j].h);
                }
                merged.push({
                    x: Math.round(minX * 100) / 100,
                    y: Math.round(minY * 100) / 100,
                    w: Math.round((maxXW - minX) * 100) / 100,
                    h: Math.round((maxYH - minY) * 100) / 100,
                });
            }

            // Step 3: 줄 간 gap 제거 (줄 높이의 60% 이하 gap → 채움)
            for (var k = 0; k < merged.length - 1; k++) {
                var cur = merged[k];
                var nxt = merged[k + 1];
                var gap = nxt.y - (cur.y + cur.h);
                if (gap > 0 && gap < cur.h * 0.6) {
                    var half = gap / 2;
                    cur.h = Math.round((cur.h + half) * 100) / 100;
                    nxt.y = Math.round((nxt.y - half) * 100) / 100;
                    nxt.h = Math.round((nxt.h + half) * 100) / 100;
                }
            }

            return merged;
        }

        // ── 텍스트 선택 액션 바 (마킹/번역/요약) ──

        var $actionBar = null;
        var $aiPopover = null;
        var _selRects = null;
        var _selText = null;
        var _aiAbortController = null;

        /** 팝오버가 뷰포트(스크롤 영역) 밖으로 넘치면 안쪽으로 당김 */
        function clampPopoverToViewport(el) {
            var elRect = el.getBoundingClientRect();
            var vpRect = $panelLeft.getBoundingClientRect();
            var parentRect = $leftAnnotationLayer.getBoundingClientRect();
            var margin = 8;
            var dx = 0, dy = 0;

            if (elRect.right > vpRect.right - margin) {
                dx = vpRect.right - margin - elRect.right;
            }
            if (elRect.bottom > vpRect.bottom - margin) {
                dy = vpRect.bottom - margin - elRect.bottom;
            }
            if (elRect.left + dx < vpRect.left + margin) {
                dx = vpRect.left + margin - elRect.left;
            }
            if (elRect.top + dy < vpRect.top + margin) {
                dy = vpRect.top + margin - elRect.top;
            }

            if (dx !== 0 || dy !== 0) {
                var pw = parentRect.width || 1;
                var ph = parentRect.height || 1;
                el.style.left = (parseFloat(el.style.left) + dx / pw * 100) + '%';
                el.style.top = (parseFloat(el.style.top) + dy / ph * 100) + '%';
            }
        }

        function hideActionBar() {
            if ($actionBar) {
                $actionBar.parentNode.removeChild($actionBar);
                $actionBar = null;
            }
        }

        function hideAiPopover() {
            if (_aiAbortController) {
                _aiAbortController.abort();
                _aiAbortController = null;
            }
            if ($aiPopover) {
                $aiPopover.parentNode.removeChild($aiPopover);
                $aiPopover = null;
            }
        }

        function showActionBar(selection) {
            hideActionBar();
            _selRects = selectionToPercentRects(selection);
            if (!_selRects || !_selRects.length) return;
            _selText = selection.toString().trim();
            if (!_selText) return;

            var lastRect = _selRects[_selRects.length - 1];
            var btnX = lastRect.x + lastRect.w;
            var btnY = lastRect.y + lastRect.h + 0.5;

            $actionBar = document.createElement('div');
            $actionBar.className = 'marking-action-bar';
            $actionBar.style.left = btnX + '%';
            $actionBar.style.top = btnY + '%';

            var actions = [
                { label: '마킹',  icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l-6 6v3h9l3-3"/><path d="M22 12l-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/></svg>', action: 'mark' },
                { label: '번역',  icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8l6 10"/><path d="M4 14h8"/><path d="M10 2h1c4.4 0 8 3.6 8 8v1"/><path d="M15 16l4 4"/><path d="M19 16l-4 4"/></svg>', action: 'translate' },
                { label: '요약',  icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="7" y1="8" x2="17" y2="8"/><line x1="7" y1="12" x2="14" y2="12"/><line x1="7" y1="16" x2="11" y2="16"/></svg>', action: 'summarize' },
            ];

            actions.forEach(function(a) {
                var btn = document.createElement('button');
                btn.innerHTML = a.icon + '<span>' + a.label + '</span>';
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    if (a.action === 'mark') {
                        createMarkingFromSelection(_selRects, _selText);
                        hideActionBar();
                        window.getSelection().removeAllRanges();
                    } else {
                        showAiPopover(a.action, a.label, btnX, btnY);
                    }
                });
                $actionBar.appendChild(btn);
            });

            $leftAnnotationLayer.appendChild($actionBar);
            clampPopoverToViewport($actionBar);
        }

        // ── AI 결과 팝오버 ──

        function showAiPopover(action, label, posX, posY) {
            hideActionBar();
            hideAiPopover();
            window.getSelection().removeAllRanges();

            var text = _selText;
            var rects = _selRects;
            if (!text || !currentDocId) return;

            $aiPopover = document.createElement('div');
            $aiPopover.className = 'ai-result-popover';
            $aiPopover.style.left = posX + '%';
            $aiPopover.style.top = posY + '%';

            // 헤더
            var header = document.createElement('div');
            header.className = 'ai-pop-header';
            var titleSpan = document.createElement('span');
            titleSpan.textContent = label;
            var modelSpan = document.createElement('span');
            modelSpan.className = 'ai-pop-model';
            modelSpan.style.display = 'none';
            var closeBtn = document.createElement('button');
            closeBtn.className = 'ai-pop-close';
            closeBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                hideAiPopover();
            });
            var titleWrap = document.createElement('span');
            titleWrap.appendChild(titleSpan);
            titleWrap.appendChild(modelSpan);
            header.appendChild(titleWrap);
            header.appendChild(closeBtn);

            // 본문 (스켈레톤)
            var body = document.createElement('div');
            body.className = 'ai-pop-body';
            body.innerHTML = '<div class="ai-skeleton"><div class="sk-line"></div><div class="sk-line"></div><div class="sk-line"></div></div>';

            // 하단 버튼
            var footer = document.createElement('div');
            footer.className = 'ai-pop-footer';
            var copyBtn = document.createElement('button');
            copyBtn.textContent = '복사';
            copyBtn.disabled = true;
            var markMemoBtn = document.createElement('button');
            markMemoBtn.textContent = '마킹+메모';
            markMemoBtn.disabled = true;
            footer.appendChild(copyBtn);
            footer.appendChild(markMemoBtn);

            $aiPopover.appendChild(header);
            $aiPopover.appendChild(body);
            $aiPopover.appendChild(footer);
            $leftAnnotationLayer.appendChild($aiPopover);
            clampPopoverToViewport($aiPopover);

            requestAnimationFrame(function() {
                $aiPopover && $aiPopover.classList.add('visible');
            });

            // 현재 선택된 모델
            var modelSel = document.getElementById('model-select');
            var model = modelSel ? modelSel.value : undefined;

            // API 호출 (AbortController로 취소 가능)
            _aiAbortController = new AbortController();
            fetch(API + '/api/translator/ai/selection', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, action: action, model: model }),
                signal: _aiAbortController.signal,
            }).then(function(r) {
                if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || '오류'); });
                return r.json();
            }).then(function(data) {
                if (!$aiPopover) return;
                var resultText = data.result || '(결과 없음)';
                body.textContent = resultText;
                if (data.model) {
                    modelSpan.textContent = ' (' + data.model + ')';
                    modelSpan.style.display = '';
                }
                copyBtn.disabled = false;
                markMemoBtn.disabled = false;

                copyBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    navigator.clipboard.writeText(resultText).then(function() {
                        copyBtn.textContent = '복사됨 ✓';
                        setTimeout(function() { copyBtn.textContent = '복사'; }, 1500);
                    });
                });

                markMemoBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    // 마킹 생성 + AI 결과를 memo로
                    var markBody = {
                        page: currentPage,
                        rects: rects,
                        color: 'yellow',
                        text: text.substring(0, 500),
                        memo: resultText,
                    };
                    fetch(API + '/api/translator/document/' + currentDocId + '/annotations', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(markBody),
                    }).then(function(r) { return r.json(); })
                      .then(function(h) {
                        if (!annotationsCache) annotationsCache = { highlights: [] };
                        annotationsCache.highlights.push(h);
                        $leftAnnotationLayer.appendChild(createHighlightDiv(h));
                        if ($rightContainer.style.display !== 'none') {
                            $rightAnnotationLayer.appendChild(createMarginMarkerDiv(h));
                        }
                        updateMarkingBadge();
                        renderMarkingList();
                        hideAiPopover();
                    });
                });
            }).catch(function(err) {
                if (err && err.name === 'AbortError') return; // 팝오버 닫힘으로 인한 취소
                if (!$aiPopover) return;
                body.textContent = err.message || 'AI 서비스에 연결할 수 없습니다';
                body.style.color = '#e74c3c';
            });
        }

        function createMarkingFromSelection(rects, text) {
            if (!currentDocId) return;
            var body = {
                page: currentPage,
                rects: rects,
                color: 'yellow',
                text: text.substring(0, 500),
            };
            fetch(API + '/api/translator/document/' + currentDocId + '/annotations', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            }).then(function(r) { return r.json(); })
              .then(function(h) {
                if (!annotationsCache) annotationsCache = { highlights: [] };
                annotationsCache.highlights.push(h);
                $leftAnnotationLayer.appendChild(createHighlightDiv(h));
                if ($rightContainer.style.display !== 'none') {
                    $rightAnnotationLayer.appendChild(createMarginMarkerDiv(h));
                }
                updateMarkingBadge();
                renderMarkingList();
            }).catch(function(err) {
                console.error('[Annotations] create error:', err);
            });
        }

        $leftTextLayer.addEventListener('mouseup', function() {
            setTimeout(function() {
                var selection = window.getSelection();
                if (!selection || selection.isCollapsed) {
                    hideActionBar();
                    return;
                }
                showActionBar(selection);
            }, 10);
        });

        document.addEventListener('mousedown', function(e) {
            if ($actionBar && !$actionBar.contains(e.target)) {
                hideActionBar();
            }
            // AI 결과 팝오버는 바깥 클릭으로 닫지 않음 (X 버튼으로만 닫기)
            // popover 외부 클릭 시 닫기 (메모 저장)
            if ($popover && !$popover.contains(e.target) && !e.target.classList.contains('highlight')) {
                hidePopover(true);
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                if ($aiPopover) { hideAiPopover(); }
                if ($actionBar) { hideActionBar(); }
            }
        });

        // ── 마킹 popover (Phase 3) ──

        var $popover = null;
        var popoverAnnId = null;

        function findAnnotation(annId) {
            if (!annotationsCache || !annotationsCache.highlights) return null;
            for (var i = 0; i < annotationsCache.highlights.length; i++) {
                if (annotationsCache.highlights[i].id === annId) return annotationsCache.highlights[i];
            }
            return null;
        }

        function showPopover(annId, anchorEl) {
            hidePopover(true);
            var ann = findAnnotation(annId);
            if (!ann) return;
            popoverAnnId = annId;

            $popover = document.createElement('div');
            $popover.className = 'marking-popover';

            // 색상 팔레트
            var palette = document.createElement('div');
            palette.className = 'color-palette';
            ['yellow', 'green', 'red', 'blue'].forEach(function(color) {
                var dot = document.createElement('div');
                dot.className = 'color-dot dot-' + color + (ann.color === color ? ' active' : '');
                dot.addEventListener('click', function(e) {
                    e.stopPropagation();
                    changeColor(annId, color);
                    palette.querySelectorAll('.color-dot').forEach(function(d) { d.classList.remove('active'); });
                    dot.classList.add('active');
                });
                palette.appendChild(dot);
            });
            $popover.appendChild(palette);

            // 메모 영역: 있으면 읽기 모드, 없으면 바로 편집
            var hasMemo = ann.memo && ann.memo.trim();
            if (hasMemo) {
                // 읽기 모드
                var memoDisplay = document.createElement('div');
                memoDisplay.className = 'memo-display';
                memoDisplay.textContent = ann.memo;
                memoDisplay.addEventListener('click', function(e) {
                    e.stopPropagation();
                    // 읽기 → 편집 전환
                    var textarea = document.createElement('textarea');
                    textarea.placeholder = '메모 추가...';
                    textarea.value = ann.memo || '';
                    memoDisplay.parentNode.replaceChild(textarea, memoDisplay);
                    textarea.focus();
                });
                $popover.appendChild(memoDisplay);
            } else {
                var textarea = document.createElement('textarea');
                textarea.placeholder = '메모 추가...';
                textarea.value = '';
                $popover.appendChild(textarea);
            }

            // 삭제 버튼 (메모 있으면 확인 단계)
            var delBtn = document.createElement('div');
            delBtn.className = 'popover-delete-btn';
            delBtn.textContent = '삭제';
            delBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                var currentAnn = findAnnotation(annId);
                var currentHasMemo = currentAnn && currentAnn.memo && currentAnn.memo.trim();
                if (currentHasMemo) {
                    // 확인 문구 표시
                    var existing = $popover.querySelector('.delete-confirm');
                    if (existing) return; // 이미 표시됨
                    var confirm = document.createElement('div');
                    confirm.className = 'delete-confirm';
                    confirm.innerHTML = '메모가 포함된 마킹입니다. <span class="confirm-yes">삭제</span> <span class="confirm-no">취소</span>';
                    confirm.querySelector('.confirm-yes').addEventListener('click', function(ev) {
                        ev.stopPropagation();
                        deleteAnnotation(annId);
                        hidePopover(false);
                    });
                    confirm.querySelector('.confirm-no').addEventListener('click', function(ev) {
                        ev.stopPropagation();
                        confirm.parentNode.removeChild(confirm);
                    });
                    delBtn.parentNode.appendChild(confirm);
                } else {
                    deleteAnnotation(annId);
                    hidePopover(false);
                }
            });
            $popover.appendChild(delBtn);

            // 위치: anchorEl 아래에 배치
            var rect = anchorEl.getBoundingClientRect();
            var containerRect = $leftContainer.getBoundingClientRect();
            var x = ((rect.left - containerRect.left) / containerRect.width) * 100;
            var y = ((rect.bottom - containerRect.top) / containerRect.height) * 100 + 0.5;
            $popover.style.left = x + '%';
            $popover.style.top = y + '%';

            $leftAnnotationLayer.appendChild($popover);
            clampPopoverToViewport($popover);
            requestAnimationFrame(function() { $popover.classList.add('visible'); });
        }

        function hidePopover(save) {
            if (!$popover) return;
            if (save && popoverAnnId) {
                // textarea가 있을 때만 저장 (읽기 모드면 textarea 없음)
                var textarea = $popover.querySelector('textarea');
                var ann = findAnnotation(popoverAnnId);
                if (textarea && ann && textarea.value !== (ann.memo || '')) {
                    saveMemo(popoverAnnId, textarea.value);
                }
            }
            if ($popover.parentNode) {
                $popover.parentNode.removeChild($popover);
            }
            $popover = null;
            popoverAnnId = null;
        }

        function changeColor(annId, color) {
            fetch(API + '/api/translator/document/' + currentDocId + '/annotations/' + annId, {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ color: color }),
            }).then(function(r) { return r.json(); })
              .then(function() {
                var ann = findAnnotation(annId);
                if (ann) ann.color = color;
                renderAnnotations();
                renderAnnotationsRight();
            });
        }

        function saveMemo(annId, memo) {
            fetch(API + '/api/translator/document/' + currentDocId + '/annotations/' + annId, {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ memo: memo }),
            }).then(function(r) { return r.json(); })
              .then(function() {
                var ann = findAnnotation(annId);
                if (ann) ann.memo = memo;
                renderAnnotations();
                renderAnnotationsRight();
            });
        }

        function deleteAnnotation(annId) {
            fetch(API + '/api/translator/document/' + currentDocId + '/annotations/' + annId, {
                method: 'DELETE',
                credentials: 'include',
            }).then(function(r) {
                if (r.ok) {
                    if (annotationsCache) {
                        annotationsCache.highlights = annotationsCache.highlights.filter(
                            function(h) { return h.id !== annId; }
                        );
                    }
                    ['left', 'right'].forEach(function(side) {
                        var layer = side === 'left' ? $leftAnnotationLayer : $rightAnnotationLayer;
                        var divs = layer.querySelectorAll('[data-ann-id="' + annId + '"]');
                        for (var i = 0; i < divs.length; i++) {
                            divs[i].parentNode.removeChild(divs[i]);
                        }
                    });
                    updateMarkingBadge();
                    renderMarkingList();
                }
            }).catch(function(err) {
                console.error('[Annotations] delete error:', err);
            });
        }

        // 하이라이트 클릭 → popover
        $leftAnnotationLayer.addEventListener('click', function(e) {
            var target = e.target;
            if (!target.classList.contains('highlight')) return;
            e.stopPropagation();
            var annId = target.dataset.annId;
            if (!annId || !currentDocId) return;
            showPopover(annId, target);
        });

        // ══════════════════════════════════════
        // Utility
        // ══════════════════════════════════════

        function escHtml(str) {
            var d = document.createElement('div');
            d.textContent = str;
            return d.innerHTML;
        }

        function formatDate(iso) {
            try {
                var d = new Date(iso);
                return d.getFullYear() + '-' +
                    String(d.getMonth() + 1).padStart(2, '0') + '-' +
                    String(d.getDate()).padStart(2, '0') + ' ' +
                    String(d.getHours()).padStart(2, '0') + ':' +
                    String(d.getMinutes()).padStart(2, '0');
            } catch(e) { return iso; }
        }

        // ══════════════════════════════════════
        // Tree Panel
        // ══════════════════════════════════════

        var $tpTrigger  = document.getElementById('tp-trigger');
        var $tpOverlay  = document.getElementById('tp-overlay');
        var $tpTree     = document.getElementById('tp-tree');
        var $tpPin      = document.getElementById('tp-pin');
        var $tpNewFolder = document.getElementById('tp-new-folder');
        var $ctxMenu    = document.getElementById('tp-ctx-menu');
        var $fpOverlay  = document.getElementById('fp-overlay');
        var $fpList     = document.getElementById('fp-list');
        var $fpCancel   = document.getElementById('fp-cancel');
        var $fpSubmit   = document.getElementById('fp-submit');

        var tpPinned = localStorage.getItem('tp-pinned') === 'true';
        var tpExpandedSet = JSON.parse(localStorage.getItem('tp-expanded') || '{}');
        var treeFolders = [];
        var treeDocs = [];
        var fpTargetDocId = null;     // 폴더 피커에서 이동할 문서 ID
        var fpSelectedFolder = undefined; // 폴더 피커에서 선택한 폴더 ID
        var ctxTargetId = null;       // 컨텍스트 메뉴 대상 ID
        var ctxTargetType = null;     // 'folder' | 'doc'

        // Pin 초기화
        if (tpPinned) {
            $tpPin.classList.add('pinned');
            $tpOverlay.classList.add('open');
        }

        // ── 패널 열기/닫기 ──
        function openTreePanel() {
            $tpOverlay.classList.add('open');
        }
        function closeTreePanel() {
            if (!tpPinned) $tpOverlay.classList.remove('open');
        }

        $tpTrigger.addEventListener('mouseenter', function() { openTreePanel(); });
        $tpTrigger.addEventListener('click', function() { openTreePanel(); });

        $tpOverlay.addEventListener('mouseleave', function(e) {
            if (!tpPinned) {
                // 커서가 트리거 쪽으로 갔으면 닫지 않음
                var rect = $tpTrigger.getBoundingClientRect();
                if (e.clientX <= rect.right) return;
                closeTreePanel();
            }
        });

        $tpPin.addEventListener('click', function() {
            tpPinned = !tpPinned;
            $tpPin.classList.toggle('pinned', tpPinned);
            localStorage.setItem('tp-pinned', tpPinned);
            if (!tpPinned && !$tpOverlay.matches(':hover')) {
                closeTreePanel();
            }
        });

        // ── 트리 데이터 로드 ──
        function loadTreeData() {
            Promise.all([
                fetch(API + '/api/translator/folders', { credentials: 'include' }).then(function(r) { return r.json(); }).catch(function() { return []; }),
                fetch(API + '/api/translator/documents', { credentials: 'include' }).then(function(r) { return r.json(); }).catch(function() { return []; }),
            ]).then(function(results) {
                treeFolders = results[0];
                treeDocs = results[1];
                renderTree();
                renderDocGrid(filteredDocs());
            });
        }

        function filteredDocs() {
            return treeDocs.filter(function(d) { return !d.folder; });
        }

        // loadDocuments()는 위에서 loadTreeData()를 호출하도록 정의됨

        // ── 트리 렌더링 ──
        function renderTree() {
            $tpTree.innerHTML = '';
            var rootUl = document.createElement('ul');

            // 루트 노드: "내 문서"
            var rootLi = document.createElement('li');
            var rootItem = document.createElement('div');
            rootItem.className = 'tree-item has-children expanded';
            rootItem.innerHTML = '<span class="toggle-icon"></span><span class="item-icon"></span><span class="tree-label">내 문서</span>';
            rootItem.querySelector('.toggle-icon').addEventListener('click', function(e) {
                e.stopPropagation();
                var expanded = rootItem.classList.toggle('expanded');
                var childMenu = rootLi.querySelector(':scope > ul.child-menu');
                if (childMenu) childMenu.classList.toggle('expanded', expanded);
            });
            rootItem.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                showCtxMenu(e, null, 'root');
            });
            rootLi.appendChild(rootItem);

            var rootChildUl = document.createElement('ul');
            rootChildUl.className = 'child-menu expanded';

            // 폴더 + 문서 렌더링
            buildTreeLevel(rootChildUl, null);

            rootLi.appendChild(rootChildUl);
            rootUl.appendChild(rootLi);
            $tpTree.appendChild(rootUl);

            // /* (미래) "공유 문서" 루트 노드 자리 예약 */
        }

        function buildTreeLevel(parentUl, parentId) {
            // 폴더
            var folders = treeFolders.filter(function(f) { return (f.parent_id || null) === parentId; });
            folders.sort(function(a, b) { return (a.order || 0) - (b.order || 0); });

            folders.forEach(function(folder) {
                var li = document.createElement('li');
                var hasKids = treeFolders.some(function(f) { return f.parent_id === folder.id; })
                    || treeDocs.some(function(d) { return (d.folder || null) === folder.id; });
                var isExpanded = !!tpExpandedSet[folder.id];

                var item = document.createElement('div');
                item.className = 'tree-item has-children' + (isExpanded ? ' expanded' : '');
                item.setAttribute('data-folder-id', folder.id);
                item.innerHTML = '<span class="toggle-icon"></span><span class="item-icon"></span><span class="tree-label" title="' + escHtml(folder.name) + '">' + escHtml(folder.name) + '</span>';

                // 토글 (클릭 시 펼침/접힘만)
                item.addEventListener('click', function() {
                    var expanded = item.classList.toggle('expanded');
                    var childMenu = li.querySelector(':scope > ul');
                    if (childMenu) childMenu.classList.toggle('expanded', expanded);
                    if (expanded) tpExpandedSet[folder.id] = true;
                    else delete tpExpandedSet[folder.id];
                    localStorage.setItem('tp-expanded', JSON.stringify(tpExpandedSet));
                });

                // 우클릭
                item.addEventListener('contextmenu', function(e) {
                    e.preventDefault();
                    showCtxMenu(e, folder.id, 'folder');
                });

                // 드롭 타겟
                item.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'move';
                    item.classList.add('drag-over');
                });
                item.addEventListener('dragleave', function() {
                    item.classList.remove('drag-over');
                });
                item.addEventListener('drop', function(e) {
                    e.preventDefault();
                    item.classList.remove('drag-over');
                    var docId = e.dataTransfer.getData('text/plain');
                    if (docId) moveDocToFolder(docId, folder.id);
                });

                li.appendChild(item);

                if (hasKids) {
                    var childUl = document.createElement('ul');
                    childUl.className = 'child-menu' + (isExpanded ? ' expanded' : '');
                    buildTreeLevel(childUl, folder.id);
                    li.appendChild(childUl);
                }

                parentUl.appendChild(li);
            });

            // 이 레벨의 문서 (루트에서는 비소속 문서 표시 안 함)
            var docs = treeDocs.filter(function(d) {
                if (!parentId) return false;
                return (d.folder || null) === parentId;
            });
            docs.forEach(function(doc) {
                var li = document.createElement('li');
                var item = document.createElement('div');
                item.className = 'tree-item has-url';
                item.setAttribute('data-doc-id', doc.id);

                var pages = doc.total_pages || doc.pages || 0;
                var displayName = doc.title || doc.filename;
                item.innerHTML = '<span class="item-icon"></span><span class="tree-label" title="' + escHtml(displayName) + '">' + escHtml(displayName) + '</span>' +
                    (pages ? '<span class="tree-doc-badge">' + pages + 'p</span>' : '');

                item.addEventListener('click', function() {
                    openViewer(doc.id, pages || 1);
                });

                item.addEventListener('contextmenu', function(e) {
                    e.preventDefault();
                    showCtxMenu(e, doc.id, 'doc');
                });

                // 트리 문서 드래그 (워크스페이스로 이동 지원)
                item.setAttribute('draggable', 'true');
                item.addEventListener('dragstart', function(e) {
                    e.dataTransfer.setData('text/plain', doc.id);
                    e.dataTransfer.effectAllowed = 'move';
                    item.classList.add('dragging');
                });
                item.addEventListener('dragend', function() {
                    item.classList.remove('dragging');
                });

                li.appendChild(item);
                parentUl.appendChild(li);
            });
        }

        // ── 드래그 앤 드롭 (카드 → 트리) ──
        // createDocCard에 draggable 추가 — 기존 함수를 래핑
        var _origCreateDocCard = createDocCard;
        createDocCard = function(doc) {
            var card = _origCreateDocCard(doc);
            card.setAttribute('draggable', 'true');
            card.addEventListener('dragstart', function(e) {
                e.dataTransfer.setData('text/plain', doc.id);
                e.dataTransfer.effectAllowed = 'move';
                card.classList.add('dragging');
            });
            card.addEventListener('dragend', function() {
                card.classList.remove('dragging');
            });
            return card;
        };

        // 카드 그리드를 드롭 타겟으로 (트리 → 워크스페이스 이동)
        $docGrid.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            $docGrid.classList.add('drag-over');
        });
        $docGrid.addEventListener('dragleave', function(e) {
            if (!$docGrid.contains(e.relatedTarget)) $docGrid.classList.remove('drag-over');
        });
        $docGrid.addEventListener('drop', function(e) {
            e.preventDefault();
            $docGrid.classList.remove('drag-over');
            var docId = e.dataTransfer.getData('text/plain');
            if (docId) moveDocToFolder(docId, null);
        });

        // ── 컨텍스트 메뉴 ──
        function showCtxMenu(e, targetId, targetType) {
            e.stopPropagation();
            ctxTargetId = targetId;
            ctxTargetType = targetType;

            $ctxMenu.innerHTML = '';

            if (targetType === 'root' || targetType === 'folder') {
                addCtxItem('새 폴더', function() {
                    var name = prompt('새 폴더 이름:');
                    if (!name || !name.trim()) return;
                    var parentId = targetType === 'folder' ? targetId : null;
                    fetch(API + '/api/translator/folders', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: name.trim(), parent_id: parentId }),
                        credentials: 'include',
                    }).then(function(r) {
                        if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail); });
                        loadTreeData();
                    }).catch(function(err) { alert(err.message); });
                });
            }

            if (targetType === 'folder') {
                addCtxItem('이름 변경', function() {
                    var folder = treeFolders.find(function(f) { return f.id === targetId; });
                    var name = prompt('새 이름:', folder ? folder.name : '');
                    if (!name || !name.trim()) return;
                    fetch(API + '/api/translator/folders/' + targetId, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: name.trim() }),
                        credentials: 'include',
                    }).then(function(r) {
                        if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail); });
                        loadTreeData();
                    }).catch(function(err) { alert(err.message); });
                });

                addCtxItem('삭제', function() {
                    var folder = treeFolders.find(function(f) { return f.id === targetId; });
                    if (!confirm('"' + (folder ? folder.name : '') + '" 폴더를 삭제하시겠습니까?\n하위 항목은 상위 폴더로 이동됩니다.')) return;
                    fetch(API + '/api/translator/folders/' + targetId, {
                        method: 'DELETE',
                        credentials: 'include',
                    }).then(function(r) {
                        if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail); });
                        loadTreeData();
                    }).catch(function(err) { alert(err.message); });
                }, true);
            }

            if (targetType === 'doc') {
                addCtxItem('워크스페이스로 이동', function() {
                    moveDocToFolder(targetId, null);
                });
                addCtxItem('이름 변경', function() {
                    var doc = treeDocs.find(function(d) { return d.id === targetId; });
                    var cur = doc ? (doc.title || doc.filename) : '';
                    var newTitle = prompt('문서 제목:', cur);
                    if (!newTitle || !newTitle.trim() || newTitle.trim() === cur) return;
                    fetch(API + '/api/translator/document/' + targetId, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ title: newTitle.trim() }),
                    }).then(function(r) {
                        if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail); });
                        loadTreeData();
                    }).catch(function(err) { alert(err.message); });
                });
                addCtxItem('이동...', function() {
                    openFolderPicker(targetId);
                });
            }

            if ($ctxMenu.children.length === 0) return;

            $ctxMenu.style.left = e.clientX + 'px';
            $ctxMenu.style.top = e.clientY + 'px';
            $ctxMenu.style.display = 'block';

            // 화면 밖 보정
            requestAnimationFrame(function() {
                var rect = $ctxMenu.getBoundingClientRect();
                if (rect.right > window.innerWidth) $ctxMenu.style.left = (e.clientX - rect.width) + 'px';
                if (rect.bottom > window.innerHeight) $ctxMenu.style.top = (e.clientY - rect.height) + 'px';
            });
        }

        function addCtxItem(label, onClick, isDanger) {
            var btn = document.createElement('button');
            btn.className = 'ctx-item' + (isDanger ? ' danger' : '');
            btn.textContent = label;
            btn.addEventListener('click', function() {
                hideCtxMenu();
                onClick();
            });
            $ctxMenu.appendChild(btn);
        }

        function hideCtxMenu() { $ctxMenu.style.display = 'none'; }

        document.addEventListener('click', function() { hideCtxMenu(); });
        document.addEventListener('contextmenu', function(e) {
            if (!$ctxMenu.contains(e.target)) hideCtxMenu();
        });

        // ── 새 폴더 버튼 (헤더) ──
        $tpNewFolder.addEventListener('click', function() {
            var name = prompt('새 폴더 이름:');
            if (!name || !name.trim()) return;
            fetch(API + '/api/translator/folders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim(), parent_id: null }),
                credentials: 'include',
            }).then(function(r) {
                if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail); });
                loadTreeData();
            }).catch(function(err) { alert(err.message); });
        });

        // ── 폴더 피커 다이얼로그 ──
        function openFolderPicker(docId) {
            fpTargetDocId = docId;
            var doc = treeDocs.find(function(d) { return d.id === docId; });
            fpSelectedFolder = doc ? (doc.folder || null) : null;

            $fpList.innerHTML = '';

            // 루트
            var rootBtn = document.createElement('button');
            rootBtn.className = 'folder-picker-item' + (fpSelectedFolder === null ? ' selected' : '');
            rootBtn.textContent = '워크스페이스 (폴더 해제)';
            rootBtn.addEventListener('click', function() {
                fpSelectedFolder = null;
                $fpList.querySelectorAll('.folder-picker-item').forEach(function(b) { b.classList.remove('selected'); });
                rootBtn.classList.add('selected');
            });
            $fpList.appendChild(rootBtn);

            // 폴더 (flat, indent로 계층 표시)
            buildFolderPickerLevel(null, 0);

            $fpOverlay.style.display = 'block';
        }

        function buildFolderPickerLevel(parentId, depth) {
            var folders = treeFolders.filter(function(f) { return (f.parent_id || null) === parentId; });
            folders.sort(function(a, b) { return (a.order || 0) - (b.order || 0); });
            folders.forEach(function(folder) {
                var btn = document.createElement('button');
                btn.className = 'folder-picker-item' + (fpSelectedFolder === folder.id ? ' selected' : '');
                btn.style.paddingLeft = (12 + depth * 16) + 'px';
                btn.textContent = folder.name;
                btn.addEventListener('click', function() {
                    fpSelectedFolder = folder.id;
                    $fpList.querySelectorAll('.folder-picker-item').forEach(function(b) { b.classList.remove('selected'); });
                    btn.classList.add('selected');
                });
                $fpList.appendChild(btn);
                buildFolderPickerLevel(folder.id, depth + 1);
            });
        }

        $fpCancel.addEventListener('click', function() {
            $fpOverlay.style.display = 'none';
        });

        $fpOverlay.addEventListener('click', function(e) {
            if (e.target === $fpOverlay) $fpOverlay.style.display = 'none';
        });

        $fpSubmit.addEventListener('click', function() {
            if (!fpTargetDocId) return;
            $fpOverlay.style.display = 'none';
            moveDocToFolder(fpTargetDocId, fpSelectedFolder);
        });

        // ── 문서 이동 API 호출 ──
        function moveDocToFolder(docId, folderId) {
            fetch(API + '/api/translator/document/' + docId + '/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder_id: folderId || null }),
                credentials: 'include',
            }).then(function(r) {
                if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail); });
                loadTreeData();
            }).catch(function(err) { alert('이동 실패: ' + err.message); });
        }

        // ══════════════════════════════════════
        // 마킹 플로팅 위젯 (Phase 4)
        // ══════════════════════════════════════

        // ── 마킹 뱃지 카운트 갱신 ──

        function updateMarkingBadge() {
            var count = (annotationsCache && annotationsCache.highlights)
                ? annotationsCache.highlights.length : 0;
            // 트리거 옆 숫자
            $mfCount.textContent = count;
            $mfCount.style.display = count > 0 ? '' : 'none';
            // 드롭다운 헤더 뱃지
            $mfBadge.textContent = count;
        }

        // ── 마킹 목록 렌더 ──

        function renderMarkingList() {
            $mfBody.innerHTML = '';

            if (!currentDocId) {
                $mfBody.innerHTML = '<div class="marking-list-empty">문서를 열어주세요.</div>';
                return;
            }

            if (!annotationsCache || !annotationsCache.highlights || !annotationsCache.highlights.length) {
                $mfBody.innerHTML = '<div class="marking-list-empty">저장된 마킹이 없습니다.<br>원문에서 텍스트를 드래그하여<br>마킹할 수 있습니다.</div>';
                return;
            }

            // 페이지별 그룹핑
            var pageMap = {};
            var highlights = annotationsCache.highlights;
            for (var i = 0; i < highlights.length; i++) {
                var h = highlights[i];
                var p = h.page || 1;
                if (!pageMap[p]) pageMap[p] = [];
                pageMap[p].push(h);
            }

            var pages = Object.keys(pageMap).sort(function(a, b) { return Number(a) - Number(b); });

            for (var pi = 0; pi < pages.length; pi++) {
                var pageNum = Number(pages[pi]);
                var items = pageMap[pageNum];

                var group = document.createElement('div');
                group.className = 'ml-page-group';

                // 페이지 헤더
                var header = document.createElement('div');
                header.className = 'ml-page-header' + (pageNum === currentPage ? ' current-page' : '');
                header.innerHTML = '<span class="ml-toggle">▾</span> ' + pageNum + '페이지 (' + items.length + ')';
                header.dataset.page = pageNum;

                var itemsContainer = document.createElement('div');
                itemsContainer.className = 'ml-items';

                header.addEventListener('click', (function(container, hdr) {
                    return function() {
                        var collapsed = container.style.display === 'none';
                        container.style.display = collapsed ? '' : 'none';
                        hdr.querySelector('.ml-toggle').textContent = collapsed ? '▾' : '▸';
                    };
                })(itemsContainer, header));

                // 항목들
                for (var j = 0; j < items.length; j++) {
                    var h = items[j];
                    var item = document.createElement('div');
                    item.className = 'ml-item';
                    item.dataset.annId = h.id;
                    item.dataset.page = pageNum;

                    var colorClass = HIGHLIGHT_COLORS[h.color] || 'dot-yellow';
                    var dotClass = colorClass.replace('color-', 'dot-');

                    var dot = document.createElement('div');
                    dot.className = 'ml-color-dot ' + dotClass;

                    var textWrap = document.createElement('div');
                    textWrap.className = 'ml-text';

                    var preview = document.createElement('div');
                    preview.className = 'ml-text-preview';
                    preview.textContent = (h.text || '').substring(0, 40) || '(텍스트 없음)';

                    textWrap.appendChild(preview);

                    if (h.memo && h.memo.trim()) {
                        var memo = document.createElement('div');
                        memo.className = 'ml-memo-preview';
                        memo.textContent = h.memo.substring(0, 50);
                        textWrap.appendChild(memo);
                    }

                    item.appendChild(dot);
                    item.appendChild(textWrap);

                    item.addEventListener('click', (function(annId, pg) {
                        return function() {
                            if (pg !== currentPage) {
                                goToPage(pg);
                                // 렌더 완료 후 포커스 효과
                                setTimeout(function() { flashHighlight(annId); }, 500);
                            } else {
                                flashHighlight(annId);
                            }
                        };
                    })(h.id, pageNum));

                    itemsContainer.appendChild(item);
                }

                group.appendChild(header);
                group.appendChild(itemsContainer);
                $mfBody.appendChild(group);
            }
        }

        // ── 하이라이트 포커스 효과 ──

        function flashHighlight(annId) {
            var el = $leftAnnotationLayer.querySelector('.highlight-group[data-ann-id="' + annId + '"]');
            if (!el) return;
            el.classList.remove('focus-flash');
            // 리플로우 강제 → 애니메이션 재시작
            void el.offsetWidth;
            el.classList.add('focus-flash');
            el.addEventListener('animationend', function() {
                el.classList.remove('focus-flash');
            }, { once: true });
        }

        // ── 마킹 변경 시 목록 갱신 훅 ──

        var _origRenderAnnotations = renderAnnotations;
        renderAnnotations = function() {
            _origRenderAnnotations();
            updateMarkingBadge();
            renderMarkingList();
        };

        var _origRenderAnnotationsRight = renderAnnotationsRight;
        renderAnnotationsRight = function() {
            _origRenderAnnotationsRight();
            updateMarkingBadge();
        };


        // ══════════════════════════════════════
        // 검색 기능
        // ══════════════════════════════════════
        var $searchOverlay = document.getElementById('ts-search-overlay');
        var $searchInput = document.getElementById('ts-search-input');
        var $searchResults = document.getElementById('ts-search-results');
        var $searchClose = document.getElementById('ts-search-close');
        var _searchTimeout = null;

        function openSearchOverlay() {
            $searchOverlay.classList.add('active');
            $searchInput.value = '';
            $searchResults.innerHTML = '';
            setTimeout(function() { $searchInput.focus(); }, 100);
        }

        function closeSearchOverlay() {
            $searchOverlay.classList.remove('active');
            $searchInput.value = '';
            $searchResults.innerHTML = '';
        }

        // 닫기 버튼
        $searchClose.addEventListener('click', closeSearchOverlay);

        // 배경 클릭
        $searchOverlay.addEventListener('click', function(e) {
            if (e.target === $searchOverlay) closeSearchOverlay();
        });

        // ESC 키
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && $searchOverlay.classList.contains('active')) {
                closeSearchOverlay();
            }
        });

        // 입력 디바운스
        $searchInput.addEventListener('input', function() {
            clearTimeout(_searchTimeout);
            var q = $searchInput.value.trim();
            if (!q) {
                $searchResults.innerHTML = '';
                return;
            }
            _searchTimeout = setTimeout(function() { performSearch(q); }, 300);
        });

        function performSearch(query) {
            $searchResults.innerHTML = '<div class="ts-search-empty">검색 중...</div>';
            fetch(API + '/api/translator/search?q=' + encodeURIComponent(query), {
                credentials: 'include',
            })
            .then(function(r) { return r.json(); })
            .then(function(data) { renderSearchResults(data, query); })
            .catch(function(err) {
                console.error('[Search]', err);
                $searchResults.innerHTML = '<div class="ts-search-empty">검색 중 오류가 발생했습니다.</div>';
            });
        }

        function renderSearchResults(data, query) {
            var html = '';
            var memos = data.memos || [];
            var pages = data.pages || [];

            if (memos.length === 0 && pages.length === 0) {
                $searchResults.innerHTML = '<div class="ts-search-empty">검색 결과가 없습니다.</div>';
                return;
            }

            // 메모 결과
            if (memos.length > 0) {
                html += '<div class="ts-search-group-label">메모 (' + memos.length + '건)</div>';
                memos.forEach(function(m) {
                    html += '<button class="ts-search-item" data-action="open" data-doc="' + escAttr(m.doc_id) + '" data-page="' + m.page + '">';
                    html += '<span class="ts-search-item-memo-badge" style="background:' + memoColor(m.color) + '"></span>';
                    html += '<span class="ts-search-item-title">' + escHtml(m.doc_title) + '</span>';
                    html += '<span class="ts-search-item-page">p.' + m.page + '</span>';
                    html += '<span class="ts-search-item-snippet">' + highlightSnippet(m.snippet, query) + '</span>';
                    html += '</button>';
                });
            }

            // 본문 결과
            if (pages.length > 0) {
                html += '<div class="ts-search-group-label">본문 (' + pages.length + '건)</div>';
                pages.forEach(function(p) {
                    html += '<button class="ts-search-item" data-action="open" data-doc="' + escAttr(p.doc_id) + '" data-page="' + p.page + '">';
                    html += '<span class="ts-search-item-title">' + escHtml(p.doc_title) + '</span>';
                    html += '<span class="ts-search-item-page">p.' + p.page + '</span>';
                    html += '<span class="ts-search-item-snippet">' + highlightSnippet(p.snippet, query) + '</span>';
                    html += '</button>';
                });
            }

            $searchResults.innerHTML = html;
        }

        // 이벤트 위임: 검색 결과 클릭
        $searchResults.addEventListener('click', function(e) {
            var item = e.target.closest('.ts-search-item');
            if (!item) return;
            var docId = item.dataset.doc;
            var page = parseInt(item.dataset.page, 10) || 1;
            closeSearchOverlay();

            if (docId === currentDocId) {
                // 같은 문서: 페이지 이동만
                goToPage(page);
            } else {
                // 다른 문서: 메타 fetch → 뷰어 열기 → 페이지 이동
                fetch(API + '/api/translator/document/' + encodeURIComponent(docId), { credentials: 'include' })
                    .then(function(r) { return r.json(); })
                    .then(function(meta) {
                        openViewer(docId, meta.pages || 1);
                        // openViewer가 fetchPageSummary 콜백 후 page 1을 렌더하므로,
                        // 약간의 딜레이 후 원하는 페이지로 이동
                        if (page > 1) {
                            setTimeout(function() { goToPage(page); }, 500);
                        }
                    })
                    .catch(function(err) {
                        console.error('[Search] doc open error:', err);
                    });
            }
        });

        function escHtml(str) {
            var div = document.createElement('div');
            div.textContent = str || '';
            return div.innerHTML;
        }

        function escAttr(str) {
            return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;');
        }

        function highlightSnippet(snippet, query) {
            if (!snippet) return '';
            var safe = escHtml(snippet);
            var terms = query.split(/\s+/).filter(function(t) { return t.length >= 1; });
            terms.forEach(function(term) {
                var re = new RegExp('(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
                safe = safe.replace(re, '<mark>$1</mark>');
            });
            return safe;
        }

        function memoColor(color) {
            var map = { yellow: '#fde68a', green: '#86efac', blue: '#93c5fd', pink: '#f9a8d4' };
            return map[color] || '#fde68a';
        }


    })();
