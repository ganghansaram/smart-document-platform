/* ===================================
   Analytics — heartbeat, page tracking, dashboard
   =================================== */

(function() {
    var _backendUrl = (typeof AUTH_CONFIG !== 'undefined' && AUTH_CONFIG.backendUrl)
        ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';
    var _heartbeatInterval = null;
    var _activeUsersPollInterval = null;

    // -- Init ----------------------------------------------------------------

    /**
     * Initialize analytics: start heartbeat + active users poll
     */
    window.initAnalytics = function() {
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
            body: JSON.stringify({ username: username }),
            credentials: 'include'
        }).catch(function() { /* silent */ });
    }

    // -- Page View Tracking --------------------------------------------------

    /**
     * Track a page view event
     * @param {string} url - The content URL being viewed
     */
    window.trackPageView = function(url) {
        if (!url || url === 'contents/home.html') return;
        fetch(_backendUrl + '/api/analytics/page-view', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url }),
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

    /**
     * Render the analytics dashboard into #main-content
     */
    /**
     * @param {string|HTMLElement} [container] - container element or ID (default: '#main-content')
     */
    window.renderAnalyticsDashboard = function(container) {
        var target = (typeof container === 'string')
            ? document.getElementById(container)
            : (container || document.getElementById('main-content'));
        if (!target) return;

        target.innerHTML = '<div class="analytics-dashboard"><div class="ad-loading">Loading dashboard...</div></div>';
        if (typeof updateSectionNav === 'function') updateSectionNav();

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
                _renderDashboardHTML(target, data);
            })
            .catch(function(err) {
                target.innerHTML = '<div class="analytics-dashboard">' +
                    '<div class="ad-no-data">' + err.message + '</div></div>';
            });
    };

    function _renderDashboardHTML(container, data) {
        var html = '<div class="analytics-dashboard">';

        // Summary cards
        html += '<div class="ad-summary">';
        html += '<div class="ad-card ad-card-clickable" id="ad-active-card" title="클릭하여 접속자 IP 확인">';
        html += '<div class="ad-card-label">현재 접속</div>';
        html += '<div class="ad-card-value active">' + (data.active_users || 0) + '</div>';
        html += '</div>';
        html += _summaryCard('오늘 방문', data.today_visitors, '');
        html += _summaryCard('이번 주', data.week_visitors, '');
        html += _summaryCard('누적 방문', data.total_visitors, '');
        html += '</div>';

        // Daily visitors chart
        html += '<div class="ad-vbar-chart">';
        html += '<div class="ad-section-title">접속 추이 (최근 14일)</div>';
        html += _verticalBarChart(data.daily_visitors, 'visitor');
        html += '</div>';

        // Top pages
        html += '<div class="ad-hbar-chart">';
        html += '<div class="ad-section-title">인기 문서 TOP 10</div>';
        if (data.top_pages && data.top_pages.length > 0) {
            html += _horizontalBarChart(data.top_pages, 'page');
        } else {
            html += '<div class="ad-no-data">데이터 없음</div>';
        }
        html += '</div>';

        // Top searches
        html += '<div class="ad-hbar-chart">';
        html += '<div class="ad-section-title">검색 키워드 TOP 10</div>';
        if (data.top_searches && data.top_searches.length > 0) {
            html += _horizontalBarChart(data.top_searches, 'search');
        } else {
            html += '<div class="ad-no-data">데이터 없음</div>';
        }
        html += '</div>';

        // Chat stats
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

        // Feedback stats
        html += _renderFeedbackSection(data.feedback);

        // Action buttons
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

})();
