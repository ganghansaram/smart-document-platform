/* ===================================
   인증 모듈
   - 로그인 게이트 (loginRequired)
   - 3단계 role: viewer / editor / admin
   - 세션 만료 감지 및 게이트 재표시
   - 사용자 관리 (role 드롭다운)
   =================================== */

var AuthState = {
    user: null,
    initialized: false
};

/**
 * 인증 초기화 — 현재 세션 확인
 */
async function initAuth() {
    if (typeof AUTH_CONFIG === 'undefined' || !AUTH_CONFIG.enabled) {
        AuthState.initialized = true;
        document.body.style.visibility = 'visible';
        return;
    }

    try {
        var response = await fetch(AUTH_CONFIG.backendUrl + '/api/auth/me', {
            credentials: 'include'
        });
        if (response.ok) {
            var data = await response.json();
            AuthState.user = data.user;
        }
    } catch (e) {
        // 서버 미연결 시 조용히 실패
    }

    AuthState.initialized = true;

    // loginRequired이고 미로그인이면 로그인 페이지로 이동
    if (AUTH_CONFIG.loginRequired && !AuthState.user) {
        window.location.replace('login.html');
        return;
    }

    document.body.style.visibility = 'visible';
    document.body.classList.add('fade-in');
    updateAuthUI();
}

/**
 * UI 상태 갱신 — body 클래스 + 헤더 표시
 */
function updateAuthUI() {
    var role = AuthState.user ? AuthState.user.role : null;
    var isViewer = role !== null && ['viewer', 'editor', 'admin'].indexOf(role) >= 0;
    var isEditor = role !== null && ['editor', 'admin'].indexOf(role) >= 0;
    var isAdmin  = role === 'admin';

    // body 클래스 토글
    document.body.classList.toggle('auth-logged-in', isViewer);
    document.body.classList.toggle('auth-editor', isEditor);
    document.body.classList.toggle('auth-admin', isAdmin);

    // 헤더 인증 영역
    var loginItem  = document.getElementById('nav-auth-login');
    var usersItem  = document.getElementById('nav-auth-users');
    var userInfo   = document.getElementById('nav-auth-userinfo');

    if (loginItem) loginItem.style.display  = isViewer ? 'none' : '';
    if (usersItem) usersItem.style.display  = isAdmin  ? '' : 'none';
    if (userInfo)  userInfo.style.display   = isViewer ? '' : 'none';

    // 사용자명 표시
    var usernameEl = document.getElementById('auth-display-username');
    if (usernameEl && AuthState.user) {
        usernameEl.textContent = AuthState.user.username;
    }
}

/**
 * 401 응답 전역 핸들러 — ai-chat.js, analytics.js 등에서 호출 가능
 */
window.handleApiUnauthorized = function() {
    AuthState.user = null;
    updateAuthUI();
    if (typeof AUTH_CONFIG !== 'undefined' && AUTH_CONFIG.loginRequired) {
        window.location.replace('login.html');
    }
};

/**
 * 관리자 권한 게이트 — admin이면 콜백 실행, 아니면 로그인 모달
 */
function requireAdmin(callback) {
    if (AuthState.user && AuthState.user.role === 'admin') {
        callback();
        return;
    }
    showLoginModal(function() {
        if (AuthState.user && AuthState.user.role === 'admin') {
            callback();
        }
    });
}

/* ── 로그인 게이트 (loginRequired) ─────── */

function showLoginGate() {
    var gate = document.getElementById('login-gate');
    if (!gate) return;

    gate.classList.add('active');
    document.body.style.overflow = 'hidden';

    var usernameInput = document.getElementById('gate-username');
    var passwordInput = document.getElementById('gate-password');
    var errorEl       = document.getElementById('gate-error');
    var submitBtn     = document.getElementById('gate-submit');

    if (!usernameInput) return;

    // 이전 이벤트 리스너 클리어 (cloneNode 방식)
    var newSubmit = submitBtn.cloneNode(true);
    submitBtn.parentNode.replaceChild(newSubmit, submitBtn);
    submitBtn = newSubmit;

    var newPw = passwordInput.cloneNode(true);
    passwordInput.parentNode.replaceChild(newPw, passwordInput);
    passwordInput = newPw;

    var newUser = usernameInput.cloneNode(true);
    usernameInput.parentNode.replaceChild(newUser, usernameInput);
    usernameInput = newUser;

    // 포커스
    setTimeout(function() { usernameInput.focus(); }, 100);

    async function doGateLogin() {
        var username = usernameInput.value.trim();
        var password = passwordInput.value;

        if (!username || !password) {
            errorEl.textContent = 'Username and password required';
            errorEl.classList.add('visible');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = '...';
        if (errorEl) errorEl.classList.remove('visible');

        try {
            var response = await fetch(AUTH_CONFIG.backendUrl + '/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username: username, password: password })
            });

            if (response.ok) {
                var data = await response.json();
                AuthState.user = data.user;
                hideLoginGate();
                updateAuthUI();
            } else {
                var err = await response.json();
                errorEl.textContent = err.detail || 'Login failed';
                errorEl.classList.add('visible');
                submitBtn.disabled = false;
                submitBtn.textContent = '로그인';
            }
        } catch (e) {
            errorEl.textContent = 'Cannot connect to server';
            errorEl.classList.add('visible');
            submitBtn.disabled = false;
            submitBtn.textContent = '로그인';
        }
    }

    submitBtn.addEventListener('click', doGateLogin);
    passwordInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') doGateLogin();
    });
    usernameInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') passwordInput.focus();
    });

    // ESC 막기
    gate.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') e.preventDefault();
    });
}

function hideLoginGate() {
    var gate = document.getElementById('login-gate');
    if (!gate) return;
    gate.classList.remove('active');
    document.body.style.overflow = '';
    // 입력값 초기화
    var u = document.getElementById('gate-username');
    var p = document.getElementById('gate-password');
    var err = document.getElementById('gate-error');
    if (u) u.value = '';
    if (p) p.value = '';
    if (err) err.classList.remove('visible');
}

/* ── 로그인 모달 (권한 게이트용 — 닫기 가능) ── */

function showLoginModal(onSuccess) {
    // 기존 모달 제거
    var existing = document.getElementById('auth-login-modal');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'auth-login-modal';
    overlay.className = 'auth-modal-overlay active';

    overlay.innerHTML =
        '<div class="auth-modal">' +
            '<h3>Login</h3>' +
            '<div class="form-group">' +
                '<label for="auth-username">Username</label>' +
                '<input type="text" id="auth-username" autocomplete="username">' +
            '</div>' +
            '<div class="form-group">' +
                '<label for="auth-password">Password</label>' +
                '<input type="password" id="auth-password" autocomplete="current-password">' +
            '</div>' +
            '<div class="error-msg" id="auth-error"></div>' +
            '<div class="auth-modal-actions">' +
                '<button class="auth-btn-secondary" id="auth-cancel">Cancel</button>' +
                '<button class="auth-btn-primary" id="auth-submit">Login</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(overlay);

    var usernameInput = document.getElementById('auth-username');
    var passwordInput = document.getElementById('auth-password');
    var errorEl = document.getElementById('auth-error');
    var submitBtn = document.getElementById('auth-submit');

    setTimeout(function() { usernameInput.focus(); }, 100);

    async function doLogin() {
        var username = usernameInput.value.trim();
        var password = passwordInput.value;
        if (!username || !password) {
            errorEl.textContent = 'Username and password required';
            errorEl.classList.add('visible');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = '...';
        errorEl.classList.remove('visible');

        try {
            var response = await fetch(AUTH_CONFIG.backendUrl + '/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username: username, password: password })
            });

            if (response.ok) {
                var data = await response.json();
                AuthState.user = data.user;
                updateAuthUI();
                closeModal();
                if (onSuccess) onSuccess();
            } else {
                var err = await response.json();
                errorEl.textContent = err.detail || 'Login failed';
                errorEl.classList.add('visible');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Login';
            }
        } catch (e) {
            errorEl.textContent = 'Cannot connect to server';
            errorEl.classList.add('visible');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Login';
        }
    }

    function closeModal() {
        overlay.remove();
    }

    submitBtn.addEventListener('click', doLogin);
    document.getElementById('auth-cancel').addEventListener('click', closeModal);
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) closeModal();
    });

    overlay.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
    });

    passwordInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') doLogin();
    });
    usernameInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') passwordInput.focus();
    });
}

/* ── 로그아웃 ──────────────────────────── */

async function handleLogout() {
    try {
        await fetch(AUTH_CONFIG.backendUrl + '/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (e) {
        // ignore
    }
    AuthState.user = null;
    updateAuthUI();

    if (typeof AUTH_CONFIG !== 'undefined' && AUTH_CONFIG.loginRequired) {
        window.location.replace('login.html');
    }
}

/* ── 사용자 관리 모달 ──────────────────── */

function showUsersModal() {
    var existing = document.getElementById('auth-users-modal');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'auth-users-modal';
    overlay.className = 'users-modal-overlay active';

    overlay.innerHTML =
        '<div class="users-modal">' +
            '<h3>User Management</h3>' +
            '<table class="users-table">' +
                '<thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Actions</th></tr></thead>' +
                '<tbody id="users-tbody"></tbody>' +
            '</table>' +
            '<div class="users-add-form">' +
                '<h4>Add User</h4>' +
                '<div class="form-row">' +
                    '<input type="text" id="new-user-name" placeholder="Username">' +
                    '<input type="password" id="new-user-pw" placeholder="Password">' +
                    '<select id="new-user-role" class="users-role-select">' +
                        '<option value="viewer">viewer</option>' +
                        '<option value="editor">editor</option>' +
                        '<option value="admin">admin</option>' +
                    '</select>' +
                '</div>' +
            '</div>' +
            '<div class="users-modal-footer">' +
                '<button class="auth-btn-secondary" id="close-users-modal">Close</button>' +
                '<button class="auth-btn-primary" id="add-user-btn">Add</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(overlay);

    loadUsersList();

    document.getElementById('close-users-modal').addEventListener('click', function() { overlay.remove(); });
    overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });

    document.getElementById('add-user-btn').addEventListener('click', addNewUser);
    document.getElementById('new-user-pw').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') addNewUser();
    });
}

async function loadUsersList() {
    var tbody = document.getElementById('users-tbody');
    if (!tbody) return;

    try {
        var response = await fetch(AUTH_CONFIG.backendUrl + '/api/auth/users', {
            credentials: 'include'
        });
        if (!response.ok) throw new Error('Failed');
        var data = await response.json();

        tbody.innerHTML = '';
        data.users.forEach(function(u) {
            var tr = document.createElement('tr');
            var isSelf = AuthState.user && AuthState.user.id === u.id;
            tr.innerHTML =
                '<td>' + u.id + '</td>' +
                '<td>' + u.username + (isSelf ? ' <em>(me)</em>' : '') + '</td>' +
                '<td><span class="users-role-badge role-' + u.role + '">' + u.role + '</span></td>' +
                '<td class="action-btns">' +
                    '<button class="btn-edit" data-id="' + u.id + '" data-name="' + u.username + '" data-role="' + u.role + '">Edit</button>' +
                    (isSelf ? '' : '<button class="btn-delete" data-id="' + u.id + '" data-name="' + u.username + '">Delete</button>') +
                '</td>';
            tbody.appendChild(tr);
        });

        // 이벤트 바인딩
        tbody.querySelectorAll('.btn-edit').forEach(function(btn) {
            btn.addEventListener('click', function() {
                editUser(this.dataset.id, this.dataset.name, this.dataset.role);
            });
        });
        tbody.querySelectorAll('.btn-delete').forEach(function(btn) {
            btn.addEventListener('click', function() { deleteUserConfirm(this.dataset.id, this.dataset.name); });
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4">Failed to load users</td></tr>';
    }
}

async function addNewUser() {
    var nameInput = document.getElementById('new-user-name');
    var pwInput   = document.getElementById('new-user-pw');
    var roleInput = document.getElementById('new-user-role');
    var username  = nameInput.value.trim();
    var password  = pwInput.value;
    var role      = roleInput ? roleInput.value : 'viewer';

    if (!username || !password) {
        showToast('Username and password required', 'error');
        return;
    }

    try {
        var response = await fetch(AUTH_CONFIG.backendUrl + '/api/auth/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username: username, password: password, role: role })
        });

        if (response.ok) {
            nameInput.value = '';
            pwInput.value = '';
            loadUsersList();
            showToast('User added', 'success');
        } else {
            var err = await response.json();
            showToast(err.detail || 'Failed to add user', 'error');
        }
    } catch (e) {
        showToast('Server error', 'error');
    }
}

function editUser(userId, currentName, currentRole) {
    // 기존 편집 모달 제거
    var existing = document.getElementById('auth-edit-modal');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'auth-edit-modal';
    overlay.className = 'auth-modal-overlay active';

    overlay.innerHTML =
        '<div class="auth-modal">' +
            '<h3>Edit User: ' + currentName + '</h3>' +
            '<div class="form-group">' +
                '<label for="edit-user-pw">New Password <span style="font-weight:normal;opacity:.6">(leave empty to keep)</span></label>' +
                '<input type="password" id="edit-user-pw" autocomplete="new-password">' +
            '</div>' +
            '<div class="form-group">' +
                '<label for="edit-user-role">Role</label>' +
                '<select id="edit-user-role" class="users-role-select" style="width:100%;padding:8px 10px;border:1px solid var(--border-color,#ddd);border-radius:4px;font-size:14px;background:var(--bg-primary,#fff);color:var(--text-primary,#333);">' +
                    '<option value="viewer"' + (currentRole === 'viewer' ? ' selected' : '') + '>viewer</option>' +
                    '<option value="editor"' + (currentRole === 'editor' ? ' selected' : '') + '>editor</option>' +
                    '<option value="admin"'  + (currentRole === 'admin'  ? ' selected' : '') + '>admin</option>' +
                '</select>' +
            '</div>' +
            '<div class="auth-modal-actions">' +
                '<button class="auth-btn-secondary" id="edit-cancel">Cancel</button>' +
                '<button class="auth-btn-primary" id="edit-submit">Save</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(overlay);

    function closeEdit() { overlay.remove(); }

    document.getElementById('edit-cancel').addEventListener('click', closeEdit);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) closeEdit(); });
    overlay.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeEdit(); });

    document.getElementById('edit-submit').addEventListener('click', function() {
        var newPassword = document.getElementById('edit-user-pw').value;
        var newRole = document.getElementById('edit-user-role').value;

        var body = {};
        if (newPassword) body.password = newPassword;
        if (newRole !== currentRole) body.role = newRole;

        if (Object.keys(body).length === 0) {
            closeEdit();
            return;
        }

        fetch(AUTH_CONFIG.backendUrl + '/api/auth/users/' + userId, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
        }).then(function(r) {
            if (r.ok) {
                loadUsersList();
                showToast('User updated', 'success');
                closeEdit();
            } else {
                r.json().then(function(err) { showToast(err.detail || 'Failed', 'error'); });
            }
        }).catch(function() { showToast('Server error', 'error'); });
    });
}

function deleteUserConfirm(userId, name) {
    if (!confirm('Delete user "' + name + '"?')) return;

    fetch(AUTH_CONFIG.backendUrl + '/api/auth/users/' + userId, {
        method: 'DELETE',
        credentials: 'include'
    }).then(function(r) {
        if (r.ok) {
            loadUsersList();
            showToast('User deleted', 'success');
        } else {
            r.json().then(function(err) { showToast(err.detail || 'Failed', 'error'); });
        }
    }).catch(function() { showToast('Server error', 'error'); });
}
