/**
 * Platform Header — 공통 헤더 컴포넌트
 *
 * initPlatformHeader({
 *     title: 'Reader',
 *     navItems: [{ id, label, href?, hidden? }],
 *     midSlot: HTMLElement | null,
 *     authRequired: true,
 *     onAuth: function(user) {},
 *     onUnauth: function() {},
 * })
 *
 * Returns: { el, nav, midSlot, usernameEl }
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
    logo.innerHTML = '<img src="css/images/kai_logo.png" alt="KAI">';
    var h1 = document.createElement('h1');
    h1.textContent = title;
    logo.appendChild(h1);
    header.appendChild(logo);

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
        if (item.href) {
            el = document.createElement('a');
            el.href = item.href;
        } else {
            el = document.createElement('button');
            el.className = 'ph-link';
            el.type = 'button';
        }
        el.id = item.id || '';
        el.textContent = item.label;
        if (item.hidden) el.style.display = 'none';
        nav.appendChild(el);
        if (item.id) navRefs[item.id] = el;
    });

    // Auth group: username | Logout (Explorer 패턴)
    var authGroup = document.createElement('span');
    authGroup.className = 'ph-auth-group';
    authGroup.style.display = 'none';

    var usernameEl = document.createElement('span');
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

    // Theme toggle (Explorer 우측 끝 동일 위치, showThemeToggle: true 일 때만)
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
                usernameEl.textContent = d.user.username;
                authGroup.style.display = '';
                onAuth(d.user);
            })
            .catch(function() { onUnauth(); });
    }

    // Logout
    logoutBtn.addEventListener('click', function() {
        fetch(API + '/api/auth/logout', { method: 'POST', credentials: 'include' })
            .then(function() { window.location.replace('login.html'); })
            .catch(function() { window.location.replace('login.html'); });
    });

    return {
        el: header,
        nav: navRefs,
        midSlot: midSlotContainer,
        usernameEl: usernameEl,
        themeToggle: themeToggle,
    };
}
