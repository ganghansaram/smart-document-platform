/* ===================================
   트리 메뉴 관리
   =================================== */

/**
 * 트리 메뉴 초기화
 */
function initTreeMenu() {
    loadMenuData();
    initTreeSearch();
    initIndexStatus();
}

/**
 * 트리 검색 초기화
 */
function initTreeSearch() {
    const searchInput = document.getElementById('tree-search-input');
    const clearBtn = document.getElementById('tree-search-clear');

    if (!searchInput || !clearBtn) return;

    let debounceTimer;

    // 검색 입력 이벤트 (debounce 적용)
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();

        // Clear 버튼 표시/숨김
        clearBtn.classList.toggle('visible', query.length > 0);

        // Debounce
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            filterTreeMenu(query);
        }, 200);
    });

    // Clear 버튼 클릭
    clearBtn.addEventListener('click', function() {
        searchInput.value = '';
        clearBtn.classList.remove('visible');
        filterTreeMenu('');
        searchInput.focus();
    });

    // ESC 키로 검색 초기화
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            searchInput.value = '';
            clearBtn.classList.remove('visible');
            filterTreeMenu('');
        }
    });
}

/**
 * 메뉴 데이터 로드
 */
function loadMenuData() {
    fetch('data/menu.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('메뉴 데이터를 불러올 수 없습니다.');
            }
            return response.json();
        })
        .then(data => {
            AppState.menuData = data;
            renderTreeMenu(data);
        })
        .catch(error => {
            console.error('메뉴 로드 오류:', error);
            const treeMenu = document.getElementById('tree-menu');
            treeMenu.innerHTML = '<p style="padding: 20px; color: #e74c3c;">메뉴를 불러오는데 실패했습니다.</p>';
        });
}

/**
 * 트리 메뉴 렌더링
 */
function renderTreeMenu(menuData) {
    const treeMenu = document.getElementById('tree-menu');
    const ul = createMenuList(menuData);
    treeMenu.innerHTML = '';
    treeMenu.appendChild(ul);
}

/**
 * 메뉴 리스트 생성 (재귀)
 */
function createMenuList(items) {
    const ul = document.createElement('ul');

    items.forEach(item => {
        const li = document.createElement('li');
        const hasChildren = item.children && item.children.length > 0;

        // 메뉴 아이템 생성
        const itemDiv = document.createElement('div');
        itemDiv.className = 'tree-item';
        if (hasChildren) {
            itemDiv.classList.add('has-children');
        }

        // 토글 아이콘 (폴더만)
        const toggleIcon = document.createElement('span');
        toggleIcon.className = 'toggle-icon';
        itemDiv.appendChild(toggleIcon);

        // 폴더/문서 아이콘
        const itemIcon = document.createElement('span');
        itemIcon.className = 'item-icon';

        // 특수 아이콘 (홈, 정보, 용어집, 대시보드)
        if (item.label === '홈') {
            itemIcon.classList.add('icon-home');
        } else if (item.label === '정보') {
            itemIcon.classList.add('icon-info');
        } else if (item.label === '용어집') {
            itemIcon.classList.add('icon-glossary');
        } else if (item.url === 'analytics:dashboard') {
            itemIcon.classList.add('icon-analytics');
        }

        // 대시보드 메뉴: admin 전용 (auth-admin-only 클래스)
        if (item.url === 'analytics:dashboard') {
            li.classList.add('auth-admin-only');
        }

        // URL이 있는 문서는 has-url 클래스 추가
        if (!hasChildren && item.url) {
            itemDiv.classList.add('has-url');
        }

        itemDiv.appendChild(itemIcon);

        // 레이블
        const label = document.createElement('span');
        label.className = 'tree-label';
        label.textContent = item.label;
        itemDiv.appendChild(label);

        // 업로드 버튼 (리프 노드 + UPLOAD_CONFIG.enabled)
        if (!hasChildren && typeof UPLOAD_CONFIG !== 'undefined' && UPLOAD_CONFIG.enabled) {
            itemDiv.classList.add('has-upload');
            const uploadBtn = document.createElement('button');
            uploadBtn.className = 'tree-upload-btn auth-editor-only';
            uploadBtn.title = '문서 업로드';
            uploadBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                var targetUrl = item.url || generateTargetPath(item.label, itemDiv);
                // URL 없는 노드는 menu.json 갱신을 위해 레이블 경로 전달
                var menuPath = item.url ? null : getMenuLabelPath(item.label, itemDiv);
                openUploadDialog(targetUrl, item.label, menuPath);
            });
            itemDiv.appendChild(uploadBtn);
        }

        // 클릭 이벤트
        itemDiv.addEventListener('click', function(e) {
            e.stopPropagation();

            if (hasChildren) {
                // 자식이 있으면 토글
                toggleMenuItem(itemDiv, li);
            } else if (item.url) {
                // URL이 있으면 페이지 로드
                loadContent(item.url);
                // 모든 활성 상태 제거
                document.querySelectorAll('.tree-item.active').forEach(el => {
                    el.classList.remove('active');
                });
                // 현재 항목 활성화
                itemDiv.classList.add('active');
                // URL 업데이트
                updatePageUrl(item.url);
            }
        });

        li.appendChild(itemDiv);

        // 자식 메뉴가 있으면 재귀적으로 생성
        if (hasChildren) {
            const childUl = createMenuList(item.children);
            childUl.className = 'child-menu';
            li.appendChild(childUl);
        }

        ul.appendChild(li);
    });

    return ul;
}

/**
 * 트리 메뉴 모두 펼치기
 */
function expandAllTree() {
    var treeMenu = document.getElementById('tree-menu');
    if (!treeMenu) return;
    treeMenu.querySelectorAll('.menu-item').forEach(function(item) {
        item.classList.add('expanded');
    });
    treeMenu.querySelectorAll('.child-menu').forEach(function(menu) {
        menu.classList.add('expanded');
    });
}

/**
 * 트리 메뉴 모두 접기
 */
function collapseAllTree() {
    var treeMenu = document.getElementById('tree-menu');
    if (!treeMenu) return;
    treeMenu.querySelectorAll('.menu-item').forEach(function(item) {
        item.classList.remove('expanded');
    });
    treeMenu.querySelectorAll('.child-menu').forEach(function(menu) {
        menu.classList.remove('expanded');
    });
}

/**
 * 메뉴 아이템 토글 (확장/축소)
 */
function toggleMenuItem(itemDiv, li) {
    const childMenu = li.querySelector('.child-menu');

    if (!childMenu) return;

    const isExpanded = itemDiv.classList.contains('expanded');

    if (isExpanded) {
        // 축소
        itemDiv.classList.remove('expanded');
        childMenu.classList.remove('expanded');
    } else {
        // 확장
        itemDiv.classList.add('expanded');
        childMenu.classList.add('expanded');
    }
}

/**
 * 현재 페이지 하이라이트 및 경로 확장
 */
function highlightCurrentPage(url) {
    // 모든 활성 상태 제거
    document.querySelectorAll('.tree-item.active').forEach(el => {
        el.classList.remove('active');
    });

    // 현재 페이지 찾기 및 활성화
    const allItems = document.querySelectorAll('.tree-item');
    let targetItem = null;

    allItems.forEach(item => {
        const itemUrl = findUrlInMenuItem(item);
        if (itemUrl === url) {
            item.classList.add('active');
            targetItem = item;
        }
    });

    // 부모 경로 확장
    if (targetItem) {
        expandParentPath(targetItem);
    }
}

/**
 * 메뉴 아이템에서 URL 찾기
 */
function findUrlInMenuItem(itemDiv) {
    // 메뉴 데이터에서 URL 찾기 (재귀 검색)
    function searchUrl(items, label) {
        for (const item of items) {
            if (item.label === label) {
                return item.url;
            }
            if (item.children) {
                const found = searchUrl(item.children, label);
                if (found) return found;
            }
        }
        return null;
    }

    const labelEl = itemDiv.querySelector('.tree-label') || itemDiv.querySelector('span:last-of-type');
    if (!labelEl) return null;
    return searchUrl(AppState.menuData || [], labelEl.textContent);
}

/**
 * 부모 경로 확장
 */
function expandParentPath(itemDiv) {
    let current = itemDiv.parentElement;

    while (current) {
        if (current.classList.contains('child-menu')) {
            current.classList.add('expanded');
            const parentLi = current.parentElement;
            if (parentLi) {
                const parentItem = parentLi.querySelector('.tree-item.has-children');
                if (parentItem) {
                    parentItem.classList.add('expanded');
                }
            }
        }
        current = current.parentElement;
    }
}

/**
 * 메뉴에서 URL로 아이템 찾기
 */
function findMenuItemByUrl(items, url) {
    for (const item of items) {
        if (item.url === url) {
            return item;
        }
        if (item.children) {
            const found = findMenuItemByUrl(item.children, url);
            if (found) return found;
        }
    }
    return null;
}

/**
 * 트리 메뉴 필터링 (하이브리드 방식)
 */
function filterTreeMenu(query) {
    const treeMenu = document.getElementById('tree-menu');

    // 검색어 없으면 원래 메뉴 복원
    if (!query) {
        renderTreeMenu(AppState.menuData);
        return;
    }

    const lowerQuery = query.toLowerCase();

    // 매칭 항목과 부모 경로 찾기
    const filteredData = filterMenuItems(AppState.menuData, lowerQuery);

    if (filteredData.length === 0) {
        treeMenu.innerHTML = '<div class="tree-no-results">검색 결과가 없습니다.</div>';
        return;
    }

    // 필터된 메뉴 렌더링
    renderFilteredTreeMenu(filteredData, lowerQuery);
}

/**
 * 메뉴 항목 필터링 (재귀) - 매칭 항목과 부모 경로 유지
 */
function filterMenuItems(items, query) {
    const result = [];

    for (const item of items) {
        const labelMatch = item.label.toLowerCase().includes(query);
        let filteredChildren = [];

        // 자식 항목 재귀 검색
        if (item.children) {
            filteredChildren = filterMenuItems(item.children, query);
        }

        // 현재 항목이 매칭되거나 자식 중 매칭이 있으면 포함
        if (labelMatch || filteredChildren.length > 0) {
            result.push({
                ...item,
                _matched: labelMatch,  // 직접 매칭 여부
                children: filteredChildren.length > 0 ? filteredChildren :
                          (labelMatch && item.children ? item.children : undefined)
            });
        }
    }

    return result;
}

/**
 * 필터된 트리 메뉴 렌더링 (검색어 하이라이트 + 자동 확장)
 */
function renderFilteredTreeMenu(menuData, query) {
    const treeMenu = document.getElementById('tree-menu');
    const ul = createFilteredMenuList(menuData, query);
    treeMenu.innerHTML = '';
    treeMenu.appendChild(ul);
}

/**
 * 필터된 메뉴 리스트 생성 (재귀)
 */
function createFilteredMenuList(items, query) {
    const ul = document.createElement('ul');

    items.forEach(item => {
        const li = document.createElement('li');
        const hasChildren = item.children && item.children.length > 0;

        // 메뉴 아이템 생성
        const itemDiv = document.createElement('div');
        itemDiv.className = 'tree-item';
        if (hasChildren) {
            itemDiv.classList.add('has-children');
            itemDiv.classList.add('expanded');  // 검색 시 자동 확장
        }

        // 토글 아이콘
        const toggleIcon = document.createElement('span');
        toggleIcon.className = 'toggle-icon';
        itemDiv.appendChild(toggleIcon);

        // 폴더/문서 아이콘
        const itemIcon = document.createElement('span');
        itemIcon.className = 'item-icon';
        if (item.label === '홈') {
            itemIcon.classList.add('icon-home');
        } else if (item.label === '정보') {
            itemIcon.classList.add('icon-info');
        } else if (item.label === '용어집') {
            itemIcon.classList.add('icon-glossary');
        } else if (item.url === 'analytics:dashboard') {
            itemIcon.classList.add('icon-analytics');
        }
        if (item.url === 'analytics:dashboard') {
            li.classList.add('auth-admin-only');
        }
        // URL이 있는 문서는 has-url 클래스 추가
        if (!hasChildren && item.url) {
            itemDiv.classList.add('has-url');
        }
        itemDiv.appendChild(itemIcon);

        // 레이블 (검색어 하이라이트)
        const label = document.createElement('span');
        label.className = 'tree-label';
        label.innerHTML = highlightText(item.label, query);
        itemDiv.appendChild(label);

        // 업로드 버튼 (필터 모드에서도 표시)
        if (!hasChildren && typeof UPLOAD_CONFIG !== 'undefined' && UPLOAD_CONFIG.enabled) {
            itemDiv.classList.add('has-upload');
            const uploadBtn = document.createElement('button');
            uploadBtn.className = 'tree-upload-btn auth-editor-only';
            uploadBtn.title = '문서 업로드';
            uploadBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                var targetUrl = item.url || generateTargetPath(item.label, itemDiv);
                var menuPath = item.url ? null : getMenuLabelPath(item.label, itemDiv);
                openUploadDialog(targetUrl, item.label, menuPath);
            });
            itemDiv.appendChild(uploadBtn);
        }

        // 클릭 이벤트
        itemDiv.addEventListener('click', function(e) {
            e.stopPropagation();

            if (hasChildren) {
                toggleMenuItem(itemDiv, li);
            } else if (item.url) {
                loadContent(item.url);
                document.querySelectorAll('.tree-item.active').forEach(el => {
                    el.classList.remove('active');
                });
                itemDiv.classList.add('active');
                updatePageUrl(item.url);
            }
        });

        li.appendChild(itemDiv);

        // 자식 메뉴 (자동 확장된 상태로)
        if (hasChildren) {
            const childUl = createFilteredMenuList(item.children, query);
            childUl.className = 'child-menu expanded';
            li.appendChild(childUl);
        }

        ul.appendChild(li);
    });

    return ul;
}

/**
 * 텍스트에서 검색어 하이라이트
 */
function highlightText(text, query) {
    if (!query) return text;

    const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

/**
 * 정규식 특수문자 이스케이프
 */
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* ===================================
   문서 업로드 기능
   =================================== */

/**
 * URL 없는 노드의 대상 경로 자동 생성
 * 트리 상의 부모 폴더 경로 + 레이블로 contents/{경로}/{레이블}/{레이블}.html 형태 생성
 */
function generateTargetPath(label, itemDiv) {
    // 부모 폴더들의 레이블을 수집 (트리를 거슬러 올라감)
    var parts = [];
    var current = itemDiv.closest('li');
    while (current) {
        var parentMenu = current.parentElement;
        if (parentMenu && parentMenu.classList.contains('child-menu')) {
            var parentLi = parentMenu.parentElement;
            if (parentLi) {
                var parentLabel = parentLi.querySelector('.tree-item .tree-label');
                if (parentLabel) {
                    parts.unshift(sanitizePathSegment(parentLabel.textContent));
                }
            }
            current = parentLi;
        } else {
            break;
        }
    }

    var safeName = sanitizePathSegment(label);
    parts.push(safeName);
    return 'contents/' + parts.join('/') + '/' + safeName + '.html';
}

/**
 * 메뉴 노드의 레이블 경로 수집 (루트→현재 노드)
 * menu.json에서 노드를 식별하기 위한 용도
 */
function getMenuLabelPath(label, itemDiv) {
    var labels = [];
    var current = itemDiv.closest('li');
    while (current) {
        var parentMenu = current.parentElement;
        if (parentMenu && parentMenu.classList.contains('child-menu')) {
            var parentLi = parentMenu.parentElement;
            if (parentLi) {
                var parentLabel = parentLi.querySelector('.tree-item .tree-label');
                if (parentLabel) {
                    labels.unshift(parentLabel.textContent);
                }
            }
            current = parentLi;
        } else {
            break;
        }
    }
    labels.push(label);
    return labels;
}

/**
 * 경로 세그먼트 정리 (특수문자 제거, 공백→하이픈)
 */
function sanitizePathSegment(text) {
    return text
        .replace(/[\[\]\(\)\/\\:*?"<>|]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
        .substring(0, 50);
}

/**
 * 업로드 다이얼로그 열기
 * @param {string} targetUrl - 대상 경로
 * @param {string} docLabel - 문서 레이블
 * @param {string[]|null} menuPath - 메뉴 레이블 경로 (URL 없는 노드일 때)
 */
function openUploadDialog(targetUrl, docLabel, menuPath) {
    // 인증 필요 체크
    if (typeof requireAdmin === 'function') {
        requireAdmin(function() { _openUploadDialogInner(targetUrl, docLabel, menuPath); });
        return;
    }
    _openUploadDialogInner(targetUrl, docLabel, menuPath);
}

function _openUploadDialogInner(targetUrl, docLabel, menuPath) {
    var config = typeof UPLOAD_CONFIG !== 'undefined' ? UPLOAD_CONFIG : {};
    var backendUrl = config.backendUrl || 'http://localhost:8000';
    var acceptFormats = config.acceptFormats || ['.docx', '.pdf'];
    var maxFileSize = config.maxFileSize || 50 * 1024 * 1024;

    // 파일 선택 input 생성
    var fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = acceptFormats.join(',');
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    fileInput.addEventListener('change', function() {
        var file = fileInput.files[0];
        if (!file) {
            document.body.removeChild(fileInput);
            return;
        }

        // 파일 크기 검증
        if (file.size > maxFileSize) {
            showToast('파일 크기 초과: ' + (file.size / 1024 / 1024).toFixed(1) + 'MB (최대 ' + (maxFileSize / 1024 / 1024) + 'MB)', 'error');
            document.body.removeChild(fileInput);
            return;
        }

        // 확인 다이얼로그
        var confirmMsg = '"' + docLabel + '" 위치에\n"' + file.name + '" 파일을 업로드하시겠습니까?\n\n기존 문서가 있으면 자동 백업됩니다.';
        if (!confirm(confirmMsg)) {
            document.body.removeChild(fileInput);
            return;
        }

        // 업로드 실행
        uploadDocument(file, targetUrl, backendUrl, menuPath);
        document.body.removeChild(fileInput);
    });

    fileInput.click();
}

/**
 * 문서 업로드 실행 (NDJSON 스트리밍)
 * @param {File} file - 업로드할 파일
 * @param {string} targetUrl - 대상 경로
 * @param {string} backendUrl - 백엔드 URL
 * @param {string[]|null} menuPath - 메뉴 레이블 경로 (URL 없는 노드일 때)
 */
async function uploadDocument(file, targetUrl, backendUrl, menuPath) {
    var config = typeof UPLOAD_CONFIG !== 'undefined' ? UPLOAD_CONFIG : {};
    var formData = new FormData();
    formData.append('file', file);
    formData.append('target_path', targetUrl);
    formData.append('auto_search_index', config.autoSearchIndex !== false ? 'true' : 'false');
    formData.append('auto_vector_index', config.autoVectorIndex !== false ? 'true' : 'false');

    if (menuPath) {
        formData.append('menu_path', JSON.stringify(menuPath));
    }

    showStepProgress(true, 'upload');

    try {
        var response = await fetch(backendUrl + '/api/upload', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        // 유효성 에러는 스트리밍 전에 HTTPException으로 반환됨
        if (!response.ok) {
            var errData = await response.json();
            throw new Error(errData.detail || '업로드 실패');
        }

        var result = await readProgressStream(response);
        showStepProgress(false);

        if (result && result.success) {
            showToast('변환 완료', 'success');

            if (menuPath) {
                reloadTreeMenuAndLoad(result.output_path);
            } else if (result.output_path) {
                loadContent(result.output_path);
            }

            checkIndexStatus();
        } else {
            showToast('업로드 실패: ' + (result ? result.message : ''), 'error');
        }
    } catch (error) {
        showStepProgress(false);
        var msg = error.message;
        if (msg === 'Failed to fetch' || msg === 'NetworkError when attempting to fetch resource.') {
            msg = '백엔드 서버에 연결할 수 없습니다. 서버 실행 상태를 확인하세요.';
        }
        showToast(msg, 'error');
        console.error('Upload error:', error);
    }
}

/**
 * 트리 메뉴 새로고침 후 문서 로드
 * menu.json 갱신 후 트리를 다시 렌더링하고, 업로드된 문서를 표시
 */
function reloadTreeMenuAndLoad(outputPath) {
    fetch('data/menu.json')
        .then(function(response) {
            if (!response.ok) throw new Error('메뉴 데이터 갱신 실패');
            return response.json();
        })
        .then(function(data) {
            // 메뉴 데이터 갱신 및 트리 재렌더링
            AppState.menuData = data;
            renderTreeMenu(data);

            // 업로드된 문서 로드 및 노드 활성화
            if (outputPath) {
                loadContent(outputPath);
                highlightCurrentPage(outputPath);
            }
        })
        .catch(function(error) {
            console.error('메뉴 새로고침 실패:', error);
            // 메뉴 새로고침 실패해도 문서는 로드 시도
            if (outputPath) {
                loadContent(outputPath);
            }
        });
}

/**
 * 단계별 진행 모달 표시/제거
 * @param {boolean} show - 표시 여부
 * @param {'upload'|'reindex'} mode - 모드에 따라 표시할 단계가 다름
 */
function showStepProgress(show, mode) {
    var existing = document.getElementById('upload-progress-overlay');
    if (!show) {
        if (existing) existing.remove();
        return;
    }
    if (existing) return;

    var uploadConfig = typeof UPLOAD_CONFIG !== 'undefined' ? UPLOAD_CONFIG : {};
    var steps;
    if (mode === 'upload') {
        steps = [{ id: 'conversion', label: '문서 변환' }];
        if (uploadConfig.autoSearchIndex !== false)
            steps.push({ id: 'search_index', label: '검색 인덱스 생성' });
        if (uploadConfig.autoVectorIndex !== false)
            steps.push({ id: 'vector_index', label: '벡터 인덱스 갱신' });
    } else {
        steps = [
            { id: 'search_index', label: '검색 인덱스 재생성' },
            { id: 'vector_index', label: '벡터 인덱스 재생성' }
        ];
    }

    var stepsHtml = steps.map(function(s) {
        return '<div class="progress-step" data-step="' + s.id + '">' +
            '<div class="step-icon"></div>' +
            '<span class="step-label">' + s.label + '</span>' +
            '<span class="step-status"></span>' +
            '</div>';
    }).join('');

    var title = mode === 'upload' ? '처리 진행 상황' : '인덱스 재생성';

    var overlay = document.createElement('div');
    overlay.id = 'upload-progress-overlay';
    overlay.className = 'upload-progress-overlay';
    overlay.innerHTML = '<div class="upload-progress-box">' +
        '<div class="progress-title">' + title + '</div>' +
        '<div class="progress-steps">' + stepsHtml + '</div>' +
        '</div>';
    document.body.appendChild(overlay);
}

/**
 * NDJSON 이벤트에 따라 단계 아이콘/상태 갱신
 * @param {Object} event - 파싱된 이벤트 객체
 */
function updateStepProgress(event) {
    if (event.step === 'done') return;
    var stepEl = document.querySelector('.progress-step[data-step="' + event.step + '"]');
    if (!stepEl) return;

    var icon = stepEl.querySelector('.step-icon');
    var status = stepEl.querySelector('.step-status');

    if (event.status === 'started') {
        icon.className = 'step-icon active';
        status.textContent = event.message || '진행 중...';
    } else if (event.status === 'completed') {
        icon.className = 'step-icon completed';
        status.textContent = event.message || '완료';
    } else if (event.status === 'skipped') {
        icon.className = 'step-icon skipped';
        status.textContent = event.message || '건너뜀';
    } else if (event.status === 'error') {
        icon.className = 'step-icon error';
        status.textContent = event.message || '오류';
    }
}

/**
 * ReadableStream에서 NDJSON 줄 단위 파싱
 * @param {Response} response - fetch Response 객체
 * @returns {Promise<Object>} 최종 결과 이벤트 (step=done 또는 마지막 이벤트)
 */
async function readProgressStream(response) {
    var reader = response.body.getReader();
    var decoder = new TextDecoder();
    var buffer = '';
    var lastEvent = null;

    while (true) {
        var result = await reader.read();
        if (result.done) break;

        buffer += decoder.decode(result.value, { stream: true });
        var lines = buffer.split('\n');
        buffer = lines.pop(); // 마지막 불완전한 줄은 버퍼에 보관

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line) continue;
            try {
                var event = JSON.parse(line);
                lastEvent = event;
                updateStepProgress(event);
            } catch (e) {
                console.warn('NDJSON parse error:', line);
            }
        }
    }

    // 남은 버퍼 처리
    if (buffer.trim()) {
        try {
            var event = JSON.parse(buffer.trim());
            lastEvent = event;
            updateStepProgress(event);
        } catch (e) {
            console.warn('NDJSON parse error (final):', buffer);
        }
    }

    return lastEvent;
}

/* ===================================
   인덱스 상태 관리
   =================================== */

/**
 * 인덱스 상태 바 초기화
 */
function initIndexStatus() {
    var statusBar = document.getElementById('index-status-bar');
    if (!statusBar) return;

    // 상태 바 항상 표시 (analytics active users)
    statusBar.style.display = 'flex';

    // Upload 기능이 비활성이면 인덱스 상태 숨김, 재생성 건너뜀
    if (typeof UPLOAD_CONFIG === 'undefined' || !UPLOAD_CONFIG.enabled) {
        var dot = statusBar.querySelector('.index-status-dot');
        var text = statusBar.querySelector('.index-status-text');
        var rbtn = document.getElementById('reindex-btn');
        if (dot) dot.style.display = 'none';
        if (text) text.style.display = 'none';
        if (rbtn) rbtn.style.display = 'none';
        return;
    }

    var reindexBtn = document.getElementById('reindex-btn');

    // 상태 확인
    checkIndexStatus();

    // 재생성 버튼 이벤트
    if (reindexBtn) {
        reindexBtn.addEventListener('click', function() {
            runManualReindex();
        });
    }
}

/**
 * 인덱스 상태 확인
 */
function checkIndexStatus() {
    var config = typeof UPLOAD_CONFIG !== 'undefined' ? UPLOAD_CONFIG : {};
    var backendUrl = config.backendUrl || 'http://localhost:8000';

    var dot = document.querySelector('.index-status-dot');
    var text = document.querySelector('.index-status-text');
    if (!dot || !text) return;

    dot.className = 'index-status-dot checking';
    text.textContent = '확인 중...';

    fetch(backendUrl + '/api/index-status?t=' + Date.now(), { credentials: 'include' })
        .then(function(response) {
            if (!response.ok) throw new Error('Status check failed');
            return response.json();
        })
        .then(function(data) {
            if (data.up_to_date) {
                dot.className = 'index-status-dot';
                text.textContent = '인덱스: 최신';
            } else {
                dot.className = 'index-status-dot outdated';
                text.textContent = '인덱스: 갱신 필요';
            }
        })
        .catch(function() {
            dot.className = 'index-status-dot outdated';
            text.textContent = '인덱스: 상태 확인 불가';
        });
}

/**
 * 수동 인덱스 재생성 (NDJSON 스트리밍)
 */
async function runManualReindex() {
    // 인증 필요 체크
    if (typeof requireAdmin === 'function') {
        requireAdmin(function() { _runManualReindexInner(); });
        return;
    }
    _runManualReindexInner();
}

async function _runManualReindexInner() {
    var config = typeof UPLOAD_CONFIG !== 'undefined' ? UPLOAD_CONFIG : {};
    var backendUrl = config.backendUrl || 'http://localhost:8000';

    var reindexBtn = document.getElementById('reindex-btn');
    var dot = document.querySelector('.index-status-dot');
    var text = document.querySelector('.index-status-text');
    if (!reindexBtn || !dot || !text) return;

    reindexBtn.disabled = true;
    reindexBtn.classList.add('spinning');
    dot.className = 'index-status-dot checking';
    text.textContent = '인덱스 재생성 중...';

    showStepProgress(true, 'reindex');

    try {
        var response = await fetch(backendUrl + '/api/reindex', { method: 'POST', credentials: 'include' });

        if (!response.ok) {
            var errData = await response.json();
            throw new Error(errData.detail || 'Reindex failed');
        }

        var result = await readProgressStream(response);
        showStepProgress(false);

        if (result && result.success) {
            dot.className = 'index-status-dot';
            var countMsg = result.indexed_count ? ' (' + result.indexed_count + '건)' : '';
            text.textContent = '인덱스: 최신' + countMsg;
            showToast('인덱스 재생성 완료' + countMsg, 'success');
        } else {
            dot.className = 'index-status-dot outdated';
            text.textContent = '인덱스: 재생성 실패';
            showToast('인덱스 재생성 실패: ' + (result ? result.message : ''), 'error');
        }
    } catch (error) {
        showStepProgress(false);
        dot.className = 'index-status-dot outdated';
        text.textContent = '인덱스: 재생성 실패';
        showToast('인덱스 재생성 실패: ' + error.message, 'error');
    } finally {
        reindexBtn.disabled = false;
        reindexBtn.classList.remove('spinning');
    }
}
