/* ===================================
   Analytics — heartbeat, page tracking, dashboard
   =================================== */

(function() {
    var _backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG)
        ? AUTH_CONFIG.backendUrl : '';
    var _heartbeatInterval = null;
    var _activeUsersPollInterval = null;
    var _subsystem = null;  // Plan-41: 서브시스템 태그 (initAnalytics 호출 시 설정)

    // -- Init ----------------------------------------------------------------

    /**
     * Initialize analytics: start heartbeat + active users poll.
     * @param {string} [subsystem] - 'explorer' | 'translator' | 'verify' |
     *                               'notebook' | 'launcher' | 'login'.
     *                               생략 시 백엔드에서 COALESCE('explorer') 처리.
     */
    window.initAnalytics = function(subsystem) {
        _subsystem = subsystem || null;
        // Send initial heartbeat
        _sendHeartbeat();
        // Heartbeat every 60 seconds
        _heartbeatInterval = setInterval(_sendHeartbeat, 60000);

        // Poll active users for status bar (admin only — will silently fail for non-admin)
        _pollActiveUsers();
        _activeUsersPollInterval = setInterval(_pollActiveUsers, 30000);
    };

    // -- Heartbeat -----------------------------------------------------------

    function _sendHeartbeat() {
        var username = (typeof AuthState !== 'undefined' && AuthState.user)
            ? AuthState.user.username : null;
        fetch(_backendUrl + '/api/analytics/heartbeat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, subsystem: _subsystem }),
            credentials: 'include'
        }).catch(function() { /* silent */ });
    }

    // -- Page View Tracking --------------------------------------------------

    /**
     * Track a page view event.
     * @param {string} url - The content URL being viewed
     * @param {string} [subsystem] - 서브시스템 명시 (생략 시 initAnalytics 에 주입된 값)
     */
    window.trackPageView = function(url, subsystem) {
        if (!url || url === 'contents/home.html') return;
        fetch(_backendUrl + '/api/analytics/page-view', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, subsystem: subsystem || _subsystem }),
            credentials: 'include'
        }).catch(function() { /* silent */ });
    };

    // -- Active Users Poll ---------------------------------------------------

    function _pollActiveUsers() {
        var wrap = document.getElementById('analytics-active-users-wrap');
        if (!wrap) return;
        // Only poll if element is visible (admin logged in)
        if (wrap.offsetParent === null && wrap.style.display === 'none') return;

        fetch(_backendUrl + '/api/analytics/active-users', { credentials: 'include' })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var countEl = document.getElementById('analytics-active-count');
                if (countEl) {
                    countEl.textContent = data.count || 0;
                }
            })
            .catch(function() { /* silent */ });
    }

    // -- Dashboard Rendering -------------------------------------------------

    // Plan-43: 자동 갱신 (30초) — 기존 _pollActiveUsers 주기와 동일
    var _dashRefreshInterval = null;
    var _dashRefreshTarget = null;
    var _DASH_REFRESH_MS = 30000;

    /**
     * @param {string|HTMLElement} [container] - container element or ID (default: '#main-content')
     */
    window.renderAnalyticsDashboard = function(container) {
        var target = (typeof container === 'string')
            ? document.getElementById(container)
            : (container || document.getElementById('main-content'));
        if (!target) return;

        // 초기 진입 시에만 로딩 스피너, 자동 갱신 시엔 이전 화면 유지
        if (target !== _dashRefreshTarget) {
            target.innerHTML = '<div class="analytics-dashboard"><div class="ad-loading">Loading dashboard...</div></div>';
            if (typeof updateSectionNav === 'function') updateSectionNav();
        }
        _dashRefreshTarget = target;

        fetch(_backendUrl + '/api/analytics/dashboard', { credentials: 'include' })
            .then(function(r) {
                if (!r.ok) {
                    if (r.status === 401) {
                        if (typeof window.handleApiUnauthorized === 'function') {
                            window.handleApiUnauthorized();
                        }
                        throw new Error('로그인이 필요합니다.');
                    }
                    throw new Error('Dashboard data load failed');
                }
                return r.json();
            })
            .then(function(data) {
                // 자동 갱신 중에도 대상 컨테이너가 DOM 에서 분리됐으면 중단
                if (!document.body.contains(target)) {
                    _stopDashboardAutoRefresh();
                    return;
                }
                _renderDashboardHTML(target, data);
                _startDashboardAutoRefresh();
            })
            .catch(function(err) {
                if (document.body.contains(target)) {
                    target.innerHTML = '<div class="analytics-dashboard">' +
                        '<div class="ad-no-data">' + _escHtml(err.message) + '</div></div>';
                }
                _stopDashboardAutoRefresh();
            });
    };

    function _startDashboardAutoRefresh() {
        if (_dashRefreshInterval) return;
        _dashRefreshInterval = setInterval(function() {
            if (!_dashRefreshTarget || !document.body.contains(_dashRefreshTarget)) {
                _stopDashboardAutoRefresh();
                return;
            }
            window.renderAnalyticsDashboard(_dashRefreshTarget);
        }, _DASH_REFRESH_MS);
    }

    function _stopDashboardAutoRefresh() {
        if (_dashRefreshInterval) {
            clearInterval(_dashRefreshInterval);
            _dashRefreshInterval = null;
        }
        _dashRefreshTarget = null;
    }

    function _formatUpdateTime(d) {
        function pad(n) { return (n < 10 ? '0' : '') + n; }
        return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    }

    function _renderDashboardHTML(container, data) {
        var html = '<div class="analytics-dashboard">';

        // 0. Last update timestamp (Plan-43)
        html += '<div class="ad-last-update-wrap">';
        html += '<span class="ad-last-update" title="데이터 기준 시각 · 30초마다 자동 갱신">' +
                _formatUpdateTime(new Date()) + ' 업데이트</span>';
        html += '</div>';

        // 1. Platform summary (플랫폼 전체 합산)
        html += '<div class="ad-summary">';
        var ipCount = (data.active_ips != null) ? data.active_ips : 0;
        var activeTitle = '로그인된 사용자 유니크 (최근 2분 활동). 전체 IP 접근 수 ' +
                          ipCount + '개 (익명·로그인페이지 포함). 클릭: 상세 목록.';
        html += '<div class="ad-card ad-card-clickable" id="ad-active-card" title="' + _escHtml(activeTitle) + '">';
        html += '<div class="ad-card-label">현재 로그인 사용자</div>';
        html += '<div class="ad-card-value active">' + (data.active_users || 0) + '</div>';
        if (ipCount > (data.active_users || 0)) {
            html += '<div class="ad-card-sub">총 IP ' + ipCount + '</div>';
        }
        html += '</div>';
        html += _summaryCard('오늘 방문', data.today_visitors, '');
        html += _summaryCard('이번 주', data.week_visitors, '');
        html += _summaryCard('누적 방문', data.total_visitors, '');
        html += '</div>';

        // 2. System health badges (Plan-43: 상단 이동 — 운영 상태 최우선)
        html += _renderHealthBadges(data.health);

        // 3. Subsystem tiles (Plan-41)
        html += _renderSubsystemTiles(data.by_subsystem);

        // 4. Daily visitors chart
        html += '<div class="ad-vbar-chart">';
        html += '<div class="ad-section-title">접속 추이 (최근 14일)</div>';
        html += _verticalBarChart(data.daily_visitors, 'visitor');
        html += '</div>';

        // 5. Top pages
        html += '<div class="ad-hbar-chart">';
        html += '<div class="ad-section-title">인기 문서 TOP 10</div>';
        if (data.top_pages && data.top_pages.length > 0) {
            html += _horizontalBarChart(data.top_pages, 'page');
        } else {
            html += '<div class="ad-no-data">데이터 없음</div>';
        }
        html += '</div>';

        // 6. Top searches
        html += '<div class="ad-hbar-chart">';
        html += '<div class="ad-section-title">검색 키워드 TOP 10</div>';
        if (data.top_searches && data.top_searches.length > 0) {
            html += _horizontalBarChart(data.top_searches, 'search');
        } else {
            html += '<div class="ad-no-data">데이터 없음</div>';
        }
        html += '</div>';

        // 7. Top users (Plan-41)
        html += _renderTopUsers(data.top_users);

        // 8. Chat stats
        html += '<div class="ad-chat-stats">';
        html += '<div class="ad-section-title">챗봇 사용 통계</div>';
        var cs = data.chat_stats || { total: 0, today: 0 };
        html += '<div class="ad-chat-summary">';
        html += '<div class="ad-chat-stat"><span class="ad-chat-stat-label">전체 질문</span><span class="ad-chat-stat-value">' + cs.total + '</span></div>';
        html += '<div class="ad-chat-stat"><span class="ad-chat-stat-label">오늘</span><span class="ad-chat-stat-value">' + cs.today + '</span></div>';
        html += '</div>';
        if (data.daily_chat && data.daily_chat.length > 0) {
            html += _miniVerticalBarChart(data.daily_chat);
        }
        html += '</div>';

        // 9. Feedback stats (Plan-43: 데이터 있을 때만 렌더)
        html += _renderFeedbackSection(data.feedback);

        // 10. Recent failures (Plan-41)
        html += _renderRecentFailures(data.recent_failures);

        // 11. Action buttons
        html += '<div class="ad-actions">';
        html += '<button class="ad-btn" id="ad-seed-btn">데모 데이터 생성</button>';
        html += '<button class="ad-btn ad-btn-danger" id="ad-reset-btn">데이터 초기화</button>';
        html += '</div>';

        html += '</div>';
        container.innerHTML = html;

        // Bind active card click -> show IP list modal
        var activeCard = document.getElementById('ad-active-card');
        if (activeCard) {
            activeCard.addEventListener('click', function() {
                _showActiveUsersModal();
            });
        }

        // Bind action buttons
        var seedBtn = document.getElementById('ad-seed-btn');
        var resetBtn = document.getElementById('ad-reset-btn');
        if (seedBtn) {
            seedBtn.addEventListener('click', function() {
                seedBtn.disabled = true;
                seedBtn.textContent = '생성 중...';
                fetch(_backendUrl + '/api/analytics/seed-demo', {
                    method: 'POST',
                    credentials: 'include'
                }).then(function(r) {
                    if (!r.ok) throw new Error('Seed failed');
                    return r.json();
                }).then(function() {
                    if (typeof showToast === 'function') showToast('데모 데이터 생성 완료', 'success');
                    renderAnalyticsDashboard(container);
                }).catch(function(err) {
                    if (typeof showToast === 'function') showToast('오류: ' + err.message, 'error');
                    seedBtn.disabled = false;
                    seedBtn.textContent = '데모 데이터 생성';
                });
            });
        }
        if (resetBtn) {
            resetBtn.addEventListener('click', function() {
                if (!confirm('모든 Analytics 데이터를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) return;
                resetBtn.disabled = true;
                resetBtn.textContent = '초기화 중...';
                fetch(_backendUrl + '/api/analytics/reset', {
                    method: 'DELETE',
                    credentials: 'include'
                }).then(function(r) {
                    if (!r.ok) throw new Error('Reset failed');
                    return r.json();
                }).then(function() {
                    if (typeof showToast === 'function') showToast('데이터 초기화 완료', 'success');
                    renderAnalyticsDashboard(container);
                }).catch(function(err) {
                    if (typeof showToast === 'function') showToast('오류: ' + err.message, 'error');
                    resetBtn.disabled = false;
                    resetBtn.textContent = '데이터 초기화';
                });
            });
        }
    }

    // -- Chart Helpers -------------------------------------------------------

    function _summaryCard(label, value, extraClass) {
        return '<div class="ad-card">' +
            '<div class="ad-card-label">' + label + '</div>' +
            '<div class="ad-card-value ' + extraClass + '">' + (value || 0) + '</div>' +
            '</div>';
    }

    function _verticalBarChart(items, type) {
        if (!items || items.length === 0) {
            return '<div class="ad-no-data">데이터 없음</div>';
        }
        var maxVal = Math.max.apply(null, items.map(function(d) { return d.count; })) || 1;
        var html = '<div class="ad-vbar-container">';
        items.forEach(function(item, i) {
            var pct = Math.round((item.count / maxVal) * 100);
            var dayLabel = item.day ? item.day.substring(5) : '';  // MM-DD
            var barClass = type === 'chat' ? 'ad-vbar chat-bar' : 'ad-vbar';
            html += '<div class="ad-vbar-item">';
            html += '<div class="' + barClass + '" style="height:' + Math.max(pct, 2) + '%;animation-delay:' + (i * 0.04) + 's">';
            html += '<span class="ad-vbar-tooltip">' + item.count + '</span>';
            html += '</div>';
            html += '<span class="ad-vbar-label">' + dayLabel + '</span>';
            html += '</div>';
        });
        html += '</div>';
        return html;
    }

    function _miniVerticalBarChart(items) {
        if (!items || items.length === 0) return '';
        var maxVal = Math.max.apply(null, items.map(function(d) { return d.count; })) || 1;
        var html = '<div class="ad-mini-vbar-container">';
        items.forEach(function(item, i) {
            var pct = Math.round((item.count / maxVal) * 100);
            html += '<div class="ad-mini-vbar-item">';
            html += '<div class="ad-mini-vbar" style="height:' + Math.max(pct, 3) + '%;animation-delay:' + (i * 0.04) + 's" title="' + (item.day || '') + ': ' + item.count + '"></div>';
            html += '</div>';
        });
        html += '</div>';
        return html;
    }

    function _horizontalBarChart(items, type) {
        var maxVal = Math.max.apply(null, items.map(function(d) { return d.count; })) || 1;
        var html = '<div class="ad-hbar-list">';
        items.forEach(function(item, i) {
            var pct = Math.round((item.count / maxVal) * 100);
            var name = type === 'page' ? _shortenUrl(item.url || '') : (item.query || '');
            var fillClass = type === 'search' ? 'ad-hbar-fill search-bar' : 'ad-hbar-fill';
            html += '<div class="ad-hbar-row">';
            html += '<span class="ad-hbar-rank">' + (i + 1) + '</span>';
            html += '<span class="ad-hbar-name" title="' + _escHtml(name) + '">' + _escHtml(name) + '</span>';
            html += '<div class="ad-hbar-track"><div class="' + fillClass + '" style="width:' + pct + '%;animation-delay:' + (i * 0.05) + 's"></div></div>';
            html += '<span class="ad-hbar-count">' + item.count + '</span>';
            html += '</div>';
        });
        html += '</div>';
        return html;
    }

    function _shortenUrl(url) {
        // "contents/samples/FY1-DoD-FLEX-4/FY1-DoD-FLEX-4.html" -> "FY1-DoD-FLEX-4"
        var parts = url.replace(/\.html$/, '').split('/');
        return parts[parts.length - 1] || url;
    }

    function _escHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // -- Feedback Section ---------------------------------------------------

    function _renderFeedbackSection(feedback) {
        if (!feedback) return '';
        var summary = feedback.summary || { total: { positive: 0, negative: 0, rate: 0 }, by_route: {}, by_confidence: {} };
        var totalCount = (summary.total.positive || 0) + (summary.total.negative || 0);

        // Plan-43: 데이터 없으면 섹션 자체 숨김 (공간 낭비 방지)
        if (totalCount === 0) return '';

        var html = '<div class="ad-feedback-section">';
        html += '<div class="ad-section-title">챗봇 피드백 분석</div>';

        if (totalCount === 0) {
            html += '<div class="ad-no-data">아직 피드백이 없습니다</div>';
            html += '</div>';
            return html;
        }

        // Summary card row
        html += '<div class="ad-summary" style="margin-bottom:16px">';
        html += '<div class="ad-card"><div class="ad-card-label">전체 만족도</div>';
        html += '<div class="ad-card-value" style="color:var(--color-success)">' + summary.total.rate + '%</div></div>';
        html += _summaryCard('긍정', summary.total.positive, '');
        html += _summaryCard('부정', summary.total.negative, '');
        html += _summaryCard('전체 응답', totalCount, '');
        html += '</div>';

        // Route satisfaction table
        var routes = summary.by_route || {};
        var routeKeys = Object.keys(routes);
        if (routeKeys.length > 0) {
            html += '<div class="ad-feedback-table-wrap">';
            html += '<table class="ad-feedback-table">';
            html += '<thead><tr><th>경로</th><th>긍정</th><th>부정</th><th>만족도</th></tr></thead><tbody>';
            routeKeys.forEach(function(r) {
                var d = routes[r];
                var rateClass = d.rate >= 70 ? 'ad-rate-good' : (d.rate >= 40 ? 'ad-rate-mid' : 'ad-rate-low');
                html += '<tr><td>' + _escHtml(r) + '</td><td>' + (d.positive || 0) + '</td><td>' + (d.negative || 0) + '</td>';
                html += '<td><span class="' + rateClass + '">' + d.rate + '%</span></td></tr>';
            });
            html += '</tbody></table></div>';
        }

        // Daily feedback chart (stacked bar)
        var daily = feedback.daily || [];
        if (daily.length > 0) {
            html += '<div style="margin-top:16px">';
            html += '<div class="ad-section-title" style="font-size:13px">일별 피드백 추세</div>';
            var maxDay = Math.max.apply(null, daily.map(function(d) { return (d.positive || 0) + (d.negative || 0); })) || 1;
            html += '<div class="ad-vbar-container">';
            daily.forEach(function(item, i) {
                var pos = item.positive || 0;
                var neg = item.negative || 0;
                var total = pos + neg;
                var posPct = Math.round((pos / maxDay) * 100);
                var negPct = Math.round((neg / maxDay) * 100);
                var dayLabel = item.day ? item.day.substring(5) : '';
                html += '<div class="ad-vbar-item">';
                html += '<div class="ad-vbar-stacked" style="height:' + Math.max(Math.round((total / maxDay) * 100), 3) + '%;animation-delay:' + (i * 0.04) + 's">';
                if (neg > 0) html += '<div class="ad-vbar-neg" style="height:' + Math.round((neg / total) * 100) + '%"></div>';
                if (pos > 0) html += '<div class="ad-vbar-pos" style="height:' + Math.round((pos / total) * 100) + '%"></div>';
                html += '<span class="ad-vbar-tooltip">긍정 ' + pos + ' · 부정 ' + neg + '</span>';
                html += '</div>';
                html += '<span class="ad-vbar-label">' + dayLabel + '</span>';
                html += '</div>';
            });
            html += '</div></div>';
        }

        // Recent negative feedback
        var negList = feedback.recent_negative || [];
        if (negList.length > 0) {
            html += '<div style="margin-top:16px">';
            html += '<div class="ad-section-title" style="font-size:13px">최근 부정 피드백</div>';
            html += '<div class="ad-neg-list">';
            negList.forEach(function(item) {
                html += '<div class="ad-neg-item">';
                html += '<div class="ad-neg-header">';
                html += '<span class="ad-neg-time">' + _escHtml(item.timestamp || '') + '</span>';
                html += '<span class="ad-neg-route">' + _escHtml(item.route || '') + '</span>';
                if (item.confidence) html += '<span class="ad-neg-conf">' + _escHtml(item.confidence) + '</span>';
                html += '</div>';
                html += '<div class="ad-neg-question">Q: ' + _escHtml(item.question || '') + '</div>';
                if (item.answer_preview) {
                    html += '<div class="ad-neg-answer">A: ' + _escHtml(item.answer_preview) + '</div>';
                }
                html += '</div>';
            });
            html += '</div></div>';
        }

        html += '</div>';
        return html;
    }

    // -- Active Users Modal --------------------------------------------------

    function _showActiveUsersModal() {
        // Remove existing modal
        var existing = document.getElementById('ad-modal-overlay');
        if (existing) existing.remove();

        var overlay = document.createElement('div');
        overlay.id = 'ad-modal-overlay';
        overlay.className = 'ad-modal-overlay';
        overlay.innerHTML =
            '<div class="ad-modal">' +
                '<div class="ad-modal-header">' +
                    '<span class="ad-modal-title">현재 접속자</span>' +
                    '<button class="ad-modal-close">&times;</button>' +
                '</div>' +
                '<div class="ad-modal-body"><span class="ad-ip-loading">조회 중...</span></div>' +
            '</div>';
        document.body.appendChild(overlay);

        // Close handlers
        overlay.querySelector('.ad-modal-close').addEventListener('click', function() { overlay.remove(); });
        overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });

        // Fetch data
        fetch(_backendUrl + '/api/analytics/active-user-list', { credentials: 'include' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                var body = overlay.querySelector('.ad-modal-body');
                if (!body) return;
                if (!d.users || d.users.length === 0) {
                    body.innerHTML = '<div class="ad-ip-empty">현재 접속자가 없습니다.</div>';
                    return;
                }
                var html = '<table class="ad-ip-table">' +
                    '<thead><tr><th>#</th><th>사용자</th><th>IP</th><th>마지막 활동</th></tr></thead><tbody>';
                d.users.forEach(function(u, i) {
                    var ago = u.elapsed_sec < 60 ? u.elapsed_sec + '초 전' : Math.floor(u.elapsed_sec / 60) + '분 전';
                    var userDisplay = u.username ? _escHtml(u.username) : '<span style="opacity:.5">—</span>';
                    html += '<tr><td>' + (i + 1) + '</td><td class="ad-ip-user">' + userDisplay + '</td><td class="ad-ip-addr">' + _escHtml(u.ip) + '</td><td class="ad-ip-ago">' + ago + '</td></tr>';
                });
                html += '</tbody></table>';
                html += '<div class="ad-modal-footer">' + d.users.length + '명 접속 중</div>';
                body.innerHTML = html;
            })
            .catch(function() {
                var body = overlay.querySelector('.ad-modal-body');
                if (body) body.innerHTML = '<div class="ad-ip-empty">조회 실패</div>';
            });
    }

    // -- Subsystem Tiles (Plan-41) -------------------------------------------

    var _SUBSYSTEM_LABELS = {
        explorer:   { label: 'Explorer',   subtitle: '웹북 탐색' },
        translator: { label: 'Translator', subtitle: 'PDF 번역' },
        verify:     { label: 'Verify',     subtitle: '문서 비교' },
        notebook:   { label: 'Notebook',   subtitle: '지식 관리' }
    };

    function _subsystemLabel(key) {
        var s = _SUBSYSTEM_LABELS[key];
        return s ? s.label : (key || '-');
    }

    function _renderSubsystemTiles(by_subsystem) {
        var html = '<div class="ad-subsystem-grid">';
        html += '<div class="ad-section-title">서브시스템 현황</div>';
        html += '<div class="ad-tiles">';
        if (!by_subsystem) {
            html += '<div class="ad-no-data">데이터 없음</div></div></div>';
            return html;
        }
        ['explorer', 'translator', 'verify', 'notebook'].forEach(function(key) {
            var s = by_subsystem[key] || { today_sessions: 0, metrics: {}, failures_today: 0, trend: [] };
            var info = _SUBSYSTEM_LABELS[key] || { label: key, subtitle: '' };
            html += '<div class="ad-tile ad-tile-' + key + '">';
            html += '<div class="ad-tile-header">';
            html += '<div class="ad-tile-heading">';
            html += '<span class="ad-tile-title">' + info.label + '</span>';
            if (info.subtitle) {
                html += '<span class="ad-tile-subtitle">' + info.subtitle + '</span>';
            }
            html += '</div>';
            if (s.failures_today > 0) {
                html += '<span class="ad-tile-fail-badge" title="오늘 발생한 실패 이벤트">⚠ ' + s.failures_today + ' 오늘</span>';
            }
            html += '</div>';
            html += '<div class="ad-tile-sessions"><span class="ad-tile-num">' + (s.today_sessions || 0) +
                    '</span><span class="ad-tile-unit">오늘 세션</span></div>';
            // 지표 (최대 2개 — 타일 레이아웃 보호)
            html += '<div class="ad-tile-metrics">';
            var metrics = s.metrics || {};
            var metricKeys = Object.keys(metrics).slice(0, 2);
            if (metricKeys.length === 0) {
                html += '<div class="ad-tile-metrics-empty">지표 없음</div>';
            } else {
                metricKeys.forEach(function(ev) {
                    var m = metrics[ev];
                    html += '<div class="ad-tile-metric"><span class="ad-tile-metric-label">' +
                            _escHtml(m.label) + '</span><span class="ad-tile-metric-value">' +
                            (m.count || 0) + '</span></div>';
                });
            }
            html += '</div>';
            // 14일 스파크라인
            html += '<div class="ad-tile-spark">' + _sparkline(s.trend || []) + '</div>';
            html += '</div>';
        });
        html += '</div></div>';
        return html;
    }

    function _sparkline(trend) {
        if (!trend || trend.length === 0) {
            return '<span class="ad-spark-empty">추이 없음</span>';
        }
        var max = Math.max.apply(null, trend.map(function(d) { return d.count; })) || 1;
        var html = '';
        trend.forEach(function(d) {
            var pct = Math.max(Math.round((d.count / max) * 100), 3);
            html += '<span class="ad-spark-bar" style="height:' + pct + '%" title="' +
                    _escHtml(d.day || '') + ': ' + d.count + '"></span>';
        });
        return html;
    }

    // -- Top Users (Plan-41) -------------------------------------------------

    function _renderTopUsers(users) {
        var html = '<div class="ad-topusers">';
        html += '<div class="ad-section-title">활발한 사용자 TOP 10 (7일)</div>';
        if (!users || users.length === 0) {
            html += '<div class="ad-no-data">데이터 없음</div></div>';
            return html;
        }
        var max = Math.max.apply(null, users.map(function(u) { return u.count; })) || 1;
        html += '<div class="ad-hbar-list">';
        users.forEach(function(u, i) {
            var pct = Math.round((u.count / max) * 100);
            var display = u.name
                ? _escHtml(u.name) + ' <span class="ad-topuser-id">(' + _escHtml(u.username) + ')</span>'
                : _escHtml(u.username);
            html += '<div class="ad-hbar-row">';
            html += '<span class="ad-hbar-rank">' + (i + 1) + '</span>';
            html += '<span class="ad-hbar-name">' + display + '</span>';
            html += '<div class="ad-hbar-track"><div class="ad-hbar-fill" style="width:' + pct +
                    '%;animation-delay:' + (i * 0.05) + 's"></div></div>';
            html += '<span class="ad-hbar-count">' + u.count + '</span>';
            html += '</div>';
        });
        html += '</div></div>';
        return html;
    }

    // -- Recent Failures (Plan-41) -------------------------------------------

    function _renderRecentFailures(failures) {
        var list = Array.isArray(failures) ? failures : [];
        var html = '<div class="ad-failures">';
        html += '<div class="ad-section-title">최근 실패 이벤트 <span class="ad-section-hint">(최신 ' +
                list.length + '건, 기간 무관)</span></div>';
        if (list.length === 0) {
            html += '<div class="ad-no-data">기록된 실패 이벤트 없음</div></div>';
            return html;
        }
        failures = list;
        html += '<div class="ad-fail-list">';
        failures.forEach(function(f) {
            var subLabel = _subsystemLabel(f.subsystem);
            var meta = f.metadata || {};
            var detail = '';
            if (f.event_type === 'error' && meta.endpoint) {
                detail = meta.endpoint + ' · ' + (meta.exception || '');
            } else if (meta.doc_id) {
                detail = 'doc:' + meta.doc_id;
                if (meta.engine) detail += ' · ' + meta.engine;
            } else if (meta.filename) {
                detail = meta.filename;
            }
            html += '<div class="ad-fail-item">';
            html += '<div class="ad-fail-header">';
            html += '<span class="ad-fail-time">' + _escHtml(f.timestamp || '') + '</span>';
            html += '<span class="ad-fail-sub ad-tile-' + _escHtml(f.subsystem || '') + '">' +
                    _escHtml(subLabel) + '</span>';
            html += '<span class="ad-fail-event">' + _escHtml(f.event_type) + '</span>';
            if (f.username) html += '<span class="ad-fail-user">' + _escHtml(f.username) + '</span>';
            html += '</div>';
            if (detail) html += '<div class="ad-fail-detail">' + _escHtml(detail) + '</div>';
            html += '</div>';
        });
        html += '</div></div>';
        return html;
    }

    // -- System Health Badges (Plan-41) --------------------------------------

    function _renderHealthBadges(health) {
        var html = '<div class="ad-health">';
        html += '<div class="ad-section-title">시스템 건강</div>';
        if (!health || !health.checks) {
            html += '<div class="ad-no-data">상태 조회 실패</div></div>';
            return html;
        }
        var c = health.checks;
        var diskValue;
        if (c.disk === 'ok' && c.disk_free_gb != null) {
            diskValue = c.disk_free_gb + ' GB';
        } else {
            diskValue = c.disk || 'unknown';
        }
        var items = [
            { key: 'database', label: '백엔드 DB', value: c.database || 'unknown' },
            { key: 'ollama',   label: 'Ollama',   value: c.ollama || 'unknown' },
            { key: 'faiss',    label: 'FAISS',    value: c.faiss || 'unknown' },
            { key: 'disk',     label: '디스크',    value: diskValue },
        ];
        html += '<div class="ad-badges">';
        items.forEach(function(it) {
            var cls = _healthBadgeClass(it.value);
            html += '<span class="ad-badge ' + cls + '">';
            html += '<span class="ad-badge-label">' + _escHtml(it.label) + '</span>';
            html += '<span class="ad-badge-value">' + _escHtml(String(it.value)) + '</span>';
            html += '</span>';
        });
        html += '</div></div>';
        return html;
    }

    function _healthBadgeClass(value) {
        var v = String(value).toLowerCase();
        if (v === 'ok' || /^\d/.test(v)) return 'ad-badge-ok';
        if (v === 'stale' || v === 'missing' || v === 'low') return 'ad-badge-warn';
        if (v === 'error' || v === 'unreachable') return 'ad-badge-error';
        return 'ad-badge-neutral';
    }

})();
