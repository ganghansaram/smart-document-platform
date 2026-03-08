/**
 * Platform Header — 공통 헤더 컴포넌트
 *
 * initPlatformHeader({
 *     title: 'Translator',
 *     navItems: [{ id, label, href?, onClick?, className?, hidden? }],
 *     midSlot: HTMLElement | null,
 *     authRequired: true,
 *     onAuth: function(user) {},
 *     onUnauth: function() {},
 *     onLogout: function() {},        // 커스텀 로그아웃 핸들러
 *     logoClick: function() {},       // 로고 클릭 핸들러
 *     showThemeToggle: false,
 * })
 *
 * Returns: { el, nav, midSlot, usernameEl, themeToggle }
 */
function initPlatformHeader(config) {
    'use strict';

    var API = (typeof AUTH_CONFIG !== 'undefined' && AUTH_CONFIG.backendUrl)
        ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';

    var title = config.title || 'Platform';
    var navItems = config.navItems || [];
    var authRequired = config.authRequired !== false;
    var onAuth = config.onAuth || function() {};
    var onUnauth = config.onUnauth || function() {
        window.location.replace('login.html');
    };

    // ── Build DOM ──
    var header = document.createElement('header');
    header.className = 'platform-header';

    // Logo
    var logo = document.createElement('div');
    logo.className = 'platform-header-logo';
    if (config.logoClick) {
        var logoLink = document.createElement('a');
        logoLink.href = '#';
        logoLink.className = 'ph-logo-link';
        logoLink.innerHTML = '<img src="css/images/kai_logo.png" alt="KAI">';
        var h1 = document.createElement('h1');
        h1.textContent = title;
        logoLink.appendChild(h1);
        logoLink.addEventListener('click', function(e) {
            e.preventDefault();
            config.logoClick();
        });
        logo.appendChild(logoLink);
    } else {
        logo.innerHTML = '<img src="css/images/kai_logo.png" alt="KAI">';
        var h1 = document.createElement('h1');
        h1.textContent = title;
        logo.appendChild(h1);
    }
    header.appendChild(logo);

    // System switcher
    var _phUser = null; // stored for deferred admin check
    if (config.currentSystem) {
        var switcherBtn = document.createElement('button');
        switcherBtn.className = 'ph-switcher-btn';
        switcherBtn.type = 'button';
        switcherBtn.title = 'Switch system';
        switcherBtn.innerHTML =
            '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">' +
                '<circle cx="5" cy="5" r="2.2"/><circle cx="12" cy="5" r="2.2"/><circle cx="19" cy="5" r="2.2"/>' +
                '<circle cx="5" cy="12" r="2.2"/><circle cx="12" cy="12" r="2.2"/><circle cx="19" cy="12" r="2.2"/>' +
                '<circle cx="5" cy="19" r="2.2"/><circle cx="12" cy="19" r="2.2"/><circle cx="19" cy="19" r="2.2"/>' +
            '</svg>';
        logo.appendChild(switcherBtn);

        var _svgAttr = 'viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"';
        var systems = [
            { id: 'platform',   label: 'Platform',   href: 'launcher.html',
              icon: '<svg ' + _svgAttr + '><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>' },
            { id: 'explorer',   label: 'Explorer',   href: 'index.html',
              icon: '<svg ' + _svgAttr + '><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>' },
            { id: 'translator', label: 'Translator', href: 'translator.html',
              icon: '<svg ' + _svgAttr + '><path d="M5 8l6 0"/><path d="M4 14l6 0"/><path d="M2 5h12"/><path d="M7 2v3"/><path d="M11 3a13.4 13.4 0 0 1-4 9"/><path d="M5 12a13 13 0 0 0 4-9"/><path d="M14 14l4 6"/><path d="M18 14l-4 6"/><path d="M15 17h4"/></svg>' },
            { id: 'compare',    label: 'Compare',    href: '#', disabled: true, badge: '개발 예정',
              icon: '<svg ' + _svgAttr + '><rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="18" rx="1"/></svg>' },
            { id: 'settings',   label: 'Settings',   href: 'admin.html', adminOnly: true, separator: true,
              icon: '<svg ' + _svgAttr + '><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' },
        ];

        var dropdown = null;
        var _hoverOpenTimer = null;
        var _hoverCloseTimer = null;

        function closeDropdown() {
            if (!dropdown) return;
            var d = dropdown;
            dropdown = null;
            d.classList.remove('open');
            d.addEventListener('transitionend', function() { d.remove(); });
            setTimeout(function() { if (d.parentNode) d.remove(); }, 200);
            document.removeEventListener('click', onOutsideClick);
        }

        function openDropdown() {
            if (dropdown) return;
            dropdown = document.createElement('div');
            dropdown.className = 'ph-system-dropdown';

            systems.forEach(function(sys) {
                var user = _phUser || (typeof AuthState !== 'undefined' && AuthState.user);
                if (sys.adminOnly && (!user || user.role !== 'admin')) return;

                // separator
                if (sys.separator) {
                    var sep = document.createElement('div');
                    sep.className = 'ph-system-separator';
                    dropdown.appendChild(sep);
                }

                var item = document.createElement('a');
                item.href = sys.disabled ? 'javascript:void(0)' : sys.href;
                var cls = 'ph-system-item';
                if (sys.id === config.currentSystem) cls += ' current';
                if (sys.disabled) cls += ' disabled';
                item.className = cls;

                // icon
                var iconSpan = document.createElement('span');
                iconSpan.className = 'ph-system-icon';
                iconSpan.innerHTML = sys.icon;
                item.appendChild(iconSpan);

                // label
                var labelSpan = document.createElement('span');
                labelSpan.textContent = sys.label;
                item.appendChild(labelSpan);

                // badge
                if (sys.badge) {
                    var badge = document.createElement('span');
                    badge.className = 'ph-system-badge';
                    badge.textContent = sys.badge;
                    item.appendChild(badge);
                }

                if (sys.disabled) {
                    item.addEventListener('click', function(e) { e.preventDefault(); });
                }

                dropdown.appendChild(item);
            });

            var rect = switcherBtn.getBoundingClientRect();
            dropdown.style.top = (rect.bottom + 4) + 'px';
            dropdown.style.left = rect.left + 'px';
            document.body.appendChild(dropdown);

            requestAnimationFrame(function() {
                if (dropdown) dropdown.classList.add('open');
            });

            // 드롭다운 호버 유지
            dropdown.addEventListener('mouseenter', function() {
                clearTimeout(_hoverCloseTimer);
            });
            dropdown.addEventListener('mouseleave', function() {
                _hoverCloseTimer = setTimeout(closeDropdown, 300);
            });

            setTimeout(function() {
                document.addEventListener('click', onOutsideClick);
            }, 0);
        }

        function onOutsideClick(e) {
            if (dropdown && !dropdown.contains(e.target) && !switcherBtn.contains(e.target)) {
                closeDropdown();
            }
        }

        // 호버 트리거 (150ms 딜레이)
        switcherBtn.addEventListener('mouseenter', function() {
            clearTimeout(_hoverCloseTimer);
            _hoverOpenTimer = setTimeout(openDropdown, 150);
        });
        switcherBtn.addEventListener('mouseleave', function() {
            clearTimeout(_hoverOpenTimer);
            _hoverCloseTimer = setTimeout(closeDropdown, 300);
        });

        // 클릭 폴백 유지
        switcherBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            clearTimeout(_hoverOpenTimer);
            clearTimeout(_hoverCloseTimer);
            if (dropdown) { closeDropdown(); } else { openDropdown(); }
        });
    }

    // Mid slot
    var midSlotContainer = document.createElement('div');
    midSlotContainer.className = 'platform-header-mid';
    if (config.midSlot) {
        midSlotContainer.appendChild(config.midSlot);
    }
    header.appendChild(midSlotContainer);

    // Nav
    var nav = document.createElement('nav');
    nav.className = 'platform-header-nav';

    var navRefs = {};

    // Custom nav items
    navItems.forEach(function(item) {
        var el;
        if (item.href && !item.onClick) {
            el = document.createElement('a');
            el.href = item.href;
        } else {
            el = document.createElement('button');
            el.className = 'ph-link';
            el.type = 'button';
        }
        el.id = item.id || '';
        if (item.className) el.className += (el.className ? ' ' : '') + item.className;
        el.textContent = item.label;
        if (item.hidden) el.style.display = 'none';
        if (item.onClick) {
            el.addEventListener('click', function(e) {
                e.preventDefault();
                item.onClick(e);
            });
        }
        nav.appendChild(el);
        if (item.id) navRefs[item.id] = el;
    });

    // Auth group: username | Logout
    var authGroup = document.createElement('span');
    authGroup.id = 'nav-auth-userinfo';
    authGroup.className = 'ph-auth-group';
    authGroup.style.display = 'none';

    var usernameEl = document.createElement('span');
    usernameEl.id = 'auth-display-username';
    usernameEl.className = 'ph-username';
    authGroup.appendChild(usernameEl);

    var sepLogout = document.createElement('span');
    sepLogout.className = 'ph-sep';
    sepLogout.textContent = '|';
    authGroup.appendChild(sepLogout);

    var logoutBtn = document.createElement('button');
    logoutBtn.className = 'ph-link';
    logoutBtn.type = 'button';
    logoutBtn.textContent = 'Logout';
    authGroup.appendChild(logoutBtn);

    nav.appendChild(authGroup);

    // Theme toggle (showThemeToggle: true 일 때만)
    var themeToggle = null;
    if (config.showThemeToggle) {
    themeToggle = document.createElement('button');
    themeToggle.id = 'theme-toggle';
    themeToggle.className = 'theme-toggle-btn';
    themeToggle.title = 'Switch theme';
    themeToggle.innerHTML =
        '<svg class="icon-sun" viewBox="0 0 24 24" width="18" height="18">' +
            '<circle cx="12" cy="12" r="5" fill="currentColor"/>' +
            '<g stroke="currentColor" stroke-width="2" stroke-linecap="round">' +
                '<line x1="12" y1="1" x2="12" y2="3"/>' +
                '<line x1="12" y1="21" x2="12" y2="23"/>' +
                '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>' +
                '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>' +
                '<line x1="1" y1="12" x2="3" y2="12"/>' +
                '<line x1="21" y1="12" x2="23" y2="12"/>' +
                '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>' +
                '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>' +
            '</g>' +
        '</svg>' +
        '<svg class="icon-moon" viewBox="0 0 24 24" width="18" height="18">' +
            '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" fill="currentColor"/>' +
        '</svg>';
    nav.appendChild(themeToggle);
    }

    header.appendChild(nav);

    // Insert as first child of body
    document.body.insertBefore(header, document.body.firstChild);

    // ── Auth ──
    if (authRequired) {
        fetch(API + '/api/auth/me', { credentials: 'include' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d.user) { onUnauth(); return; }
                _phUser = d.user;
                usernameEl.textContent = d.user.username;
                authGroup.style.display = '';
                onAuth(d.user);
            })
            .catch(function() { onUnauth(); });
    }

    // Logout
    logoutBtn.addEventListener('click', function() {
        if (config.onLogout) {
            config.onLogout();
        } else {
            fetch(API + '/api/auth/logout', { method: 'POST', credentials: 'include' })
                .then(function() { window.location.replace('login.html'); })
                .catch(function() { window.location.replace('login.html'); });
        }
    });

    return {
        el: header,
        nav: navRefs,
        midSlot: midSlotContainer,
        usernameEl: usernameEl,
        themeToggle: themeToggle,
    };
}
