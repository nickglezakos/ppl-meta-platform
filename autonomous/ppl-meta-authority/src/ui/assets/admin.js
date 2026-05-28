const pageName = document.body.dataset.page || 'admin';
const SESSION_TOKEN_STORAGE_KEY = 'authority.sessionToken';
const toastRegionEl = document.getElementById('toastRegion');
const bodyEl = document.getElementById('dataBody');
const hierarchyViewEl = document.getElementById('hierarchyView');
const hierarchyExplainEl = document.getElementById('hierarchyExplain');
const loggedOutPanelEl = document.getElementById('loggedOutPanel');
const authenticatedShellEl = document.getElementById('authenticatedShell');
const TOAST_MAX_COUNT = 5;
const TOAST_TIMEOUT_MS = 4200;
let previousFocusedElement = null;
let sessionToken = '';
let currentUser = null;
let activeConsoleFilter = 'all';
let consoleSearchQuery = '';
let changePasswordReturnFocus = null;
let adminUsersCache = [];
let hierarchyViewModel = [];
let auditState = {
  items: [],
  rows: [],
  nextOffset: null,
  hasMore: false,
  loadedCount: 0,
  filters: {
    target_entity_type: '',
    target_entity_uuid: '',
    action: '',
    actor_role_name: '',
    limit: '',
  },
};
let consoleRowsByFilter = {
  users: [],
  hierarchy: [],
  entitlements: [],
  invitations: [],
  assignments: [],
  audit: [],
  updates: [],
  health: [],
};
const viewRoleMap = {
  session: ['platform_admin', 'distributor', 'reseller', 'owner', 'support'],
  overview: ['platform_admin', 'distributor', 'reseller', 'owner', 'support'],
  admin: ['platform_admin'],
  distributor: ['distributor'],
  reseller: ['reseller'],
  owner: ['owner', 'support'],
};

const viewTitleMap = {
  session: 'Session',
  overview: 'Overview',
  admin: 'Admin',
  distributor: 'Distributor',
  reseller: 'Reseller',
  owner: 'Owner Dashboard',
};
const searchParams = new URLSearchParams(window.location.search);
const requestedView = searchParams.get('view');
const requestedInvitationToken = searchParams.get('invitation_token');
const requestedPublicView = requestedInvitationToken ? 'invitation' : 'login';

function requestedAuditFilters() {
  return {
    target_entity_type: searchParams.get('target_entity_type') || '',
    target_entity_uuid: searchParams.get('target_entity_uuid') || '',
    action: searchParams.get('action') || '',
    actor_role_name: searchParams.get('actor_role_name') || '',
    limit: searchParams.get('limit') || '',
    loaded: searchParams.get('audit_loaded') || '',
  };
}

function currentAuditFiltersFromInputs() {
  const requested = requestedAuditFilters();
  return {
    target_entity_type: document.getElementById('audit_target_entity_type')?.value.trim() || requested.target_entity_type,
    target_entity_uuid: document.getElementById('audit_target_entity_uuid')?.value.trim() || requested.target_entity_uuid,
    action: document.getElementById('audit_action')?.value.trim() || requested.action,
    actor_role_name: document.getElementById('audit_actor_role_name')?.value.trim() || requested.actor_role_name,
    limit: document.getElementById('audit_limit')?.value.trim() || requested.limit || '100',
  };
}

function persistConsoleState() {
  if (pageName !== 'console') {
    return;
  }
  const nextSearch = new URLSearchParams(window.location.search);
  nextSearch.set('filter', activeConsoleFilter);
  const filters = auditState.filters;
  if (filters.target_entity_type) {
    nextSearch.set('target_entity_type', filters.target_entity_type);
  } else {
    nextSearch.delete('target_entity_type');
  }
  if (filters.target_entity_uuid) {
    nextSearch.set('target_entity_uuid', filters.target_entity_uuid);
  } else {
    nextSearch.delete('target_entity_uuid');
  }
  if (filters.action) {
    nextSearch.set('action', filters.action);
  } else {
    nextSearch.delete('action');
  }
  if (filters.actor_role_name) {
    nextSearch.set('actor_role_name', filters.actor_role_name);
  } else {
    nextSearch.delete('actor_role_name');
  }
  if (filters.limit) {
    nextSearch.set('limit', filters.limit);
  } else {
    nextSearch.delete('limit');
  }
  if (auditState.loadedCount > 0) {
    nextSearch.set('audit_loaded', String(auditState.loadedCount));
  } else {
    nextSearch.delete('audit_loaded');
  }
  window.history.replaceState(null, '', `${window.location.pathname}?${nextSearch.toString()}`);
}

function element(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const target = element(id);
  if (target) {
    target.textContent = value;
  }
}

function dismissToast(toastEl) {
  if (!(toastEl instanceof HTMLElement)) {
    return;
  }
  toastEl.classList.add('toast-exit');
  window.setTimeout(() => {
    toastEl.remove();
  }, 180);
}

function showToast(message, tone = 'success') {
  if (!toastRegionEl || !message) {
    return;
  }
  const toastEl = document.createElement('div');
  toastEl.className = `toast toast-${tone}`;

  const messageEl = document.createElement('div');
  messageEl.className = 'toast-message';
  messageEl.textContent = message;

  const dismissButton = document.createElement('button');
  dismissButton.type = 'button';
  dismissButton.className = 'toast-dismiss';
  dismissButton.setAttribute('aria-label', 'Dismiss notification');
  dismissButton.textContent = 'Close';
  dismissButton.addEventListener('click', () => dismissToast(toastEl));

  toastEl.append(messageEl, dismissButton);
  toastRegionEl.prepend(toastEl);

  while (toastRegionEl.childElementCount > TOAST_MAX_COUNT) {
    dismissToast(toastRegionEl.lastElementChild);
  }

  window.setTimeout(() => dismissToast(toastEl), TOAST_TIMEOUT_MS);
}

function setStatus(message, isError = false) {
  showToast(message, isError ? 'error' : 'success');
}

function setAcceptStatus(message, isError = false) {
  showToast(message, isError ? 'error' : 'success');
}

function prefillInvitationTokenFromUrl() {
  if (!requestedInvitationToken) {
    return;
  }
  const tokenField = document.getElementById('accept_invitation_token');
  if (!(tokenField instanceof HTMLInputElement)) {
    return;
  }
  tokenField.value = requestedInvitationToken;
  if (currentUser) {
    activateView(preferredViewForRole(userRole()));
  }
  setAcceptStatus('Invitation token loaded from your email link. Set your display name and password to accept the invitation.');
}

function authHeaders() {
  const token = sessionToken;
  if (!token) {
    throw new Error('Log in first.');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
}

function persistedSessionToken() {
  try {
    return window.localStorage.getItem(SESSION_TOKEN_STORAGE_KEY) || '';
  } catch (error) {
    return '';
  }
}

function storeSessionToken(token) {
  try {
    if (token) {
      window.localStorage.setItem(SESSION_TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
    }
  } catch (error) {
    // Ignore storage failures and continue with in-memory auth only.
  }
}

function updateAuthView() {
  const isAuthenticated = Boolean(currentUser);
  if (loggedOutPanelEl) {
    loggedOutPanelEl.classList.toggle('hidden', isAuthenticated || requestedPublicView !== 'login');
  }
  if (authenticatedShellEl) {
    authenticatedShellEl.classList.toggle('hidden', !isAuthenticated);
  }
  document.querySelectorAll('[data-public-view]').forEach((node) => {
    const shouldShow = !isAuthenticated && node.dataset.publicView === requestedPublicView;
    node.classList.toggle('hidden', !shouldShow);
  });
  document.querySelectorAll('[data-auth-visibility]').forEach((node) => {
    const visibility = node.dataset.authVisibility;
    const shouldShow = visibility === 'authenticated' ? isAuthenticated : !isAuthenticated;
    node.classList.toggle('hidden', !shouldShow);
  });
}

function setSession(user, token = '') {
  currentUser = user;
  sessionToken = token || sessionToken || persistedSessionToken();
  if (user) {
    storeSessionToken(sessionToken);
  } else {
    storeSessionToken('');
  }
  setText('currentRole', user ? user.role_name : 'Unauthenticated');
  setText('currentEmail', user ? user.email : '-');
  setText('currentDistributorScope', user && user.distributor_uuid ? user.distributor_uuid : '-');
  setText('currentResellerScope', user && user.reseller_uuid ? user.reseller_uuid : '-');
  setText('metricRole', user ? user.role_name : '-');
  setText('metricDistributorScope', user && user.distributor_uuid ? user.distributor_uuid : '-');
  setText('metricScope', user && user.reseller_uuid ? user.reseller_uuid : '-');
  setText('sessionViewRole', user ? user.role_name : '-');
  setText('sessionViewEmail', user ? user.email : '-');
  setText('sessionViewDistributor', user && user.distributor_uuid ? user.distributor_uuid : '-');
  setText('sessionViewReseller', user && user.reseller_uuid ? user.reseller_uuid : '-');
  setMetricValue('metricPendingInvitations', 0);
  setMetricValue('metricRecentAssignments', 0);
  if (!user) {
    setMetricValue('metricOwnerCount', 0);
    setMetricValue('metricResellerCount', 0);
    renderSummaryCards('adminSummaryCards', []);
    renderSummaryCards('distributorSummaryCards', []);
    renderSummaryCards('resellerSummaryCards', []);
    renderSummaryCards('ownerSummaryCards', []);
    renderActivityList('adminRecentInvitations', [], 'No invitation activity yet.');
    renderActivityList('adminRecentAssignments', [], 'No assignment activity yet.');
    renderActivityList('adminRecentHealth', [], 'No health activity yet.');
    renderActivityList('distributorRecentAssignments', [], 'No distributor assignment activity yet.');
    renderActivityList('distributorRecentHealth', [], 'No distributor health activity yet.');
    renderActivityList('resellerRecentAssignments', [], 'No reseller assignment activity yet.');
    renderActivityList('ownerRecentUpdates', [], 'No lifecycle activity yet.');
    renderActivityList('resellerRecentHealth', [], 'No reseller health activity yet.');
    renderActivityList('ownerRecentHealth', [], 'No owner health activity yet.');
    resetConsoleRows();
  }
  updateAuthView();
  syncRoleVisibility();
  renderConsoleFilter();
}

function userRole() {
  return currentUser ? currentUser.role_name : null;
}

function isRoleAllowed(allowedRoles) {
  const role = userRole();
  return role ? allowedRoles.includes(role) : false;
}

function syncRoleVisibility() {
  document.querySelectorAll('.role-section').forEach((section) => {
    const allowedRoles = (section.dataset.roleScope || '').split(',').map((value) => value.trim()).filter(Boolean);
    if (!allowedRoles.length) {
      section.classList.remove('hidden');
      return;
    }
    section.classList.toggle('hidden', !isRoleAllowed(allowedRoles));
  });

  document.querySelectorAll('.view-link[data-view]').forEach((button) => {
    const allowedRoles = viewRoleMap[button.dataset.view] || [];
    const shouldHide = allowedRoles.length ? !isRoleAllowed(allowedRoles) : false;
    button.classList.toggle('hidden', shouldHide);
    if (button.classList.contains('active') && shouldHide) {
      activateView(preferredViewForRole(userRole()));
    }
  });

}

function navigationFocusableElements() {
  const nav = element('viewNavigation');
  if (!nav) {
    return [];
  }
  return Array.from(nav.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')).filter((node) => !node.classList.contains('hidden'));
}

function syncDistributorInviteForm() {
  const roleSelect = document.getElementById('distributor_invite_role_name');
  const emailLabel = document.getElementById('distributorInviteEmailLabel');
  const emailInput = document.getElementById('distributor_invite_email');
  const hint = document.getElementById('distributorInviteHint');
  if (!(roleSelect instanceof HTMLSelectElement)) {
    return;
  }

  const invitingRole = roleSelect.value;
  if (emailLabel) {
    emailLabel.textContent = invitingRole === 'owner' ? 'Owner email' : 'Invite email';
  }
  if (emailInput instanceof HTMLInputElement) {
    emailInput.placeholder = invitingRole === 'owner' ? 'owner@example.com' : 'reseller@example.com';
  }
  if (hint) {
    hint.textContent = invitingRole === 'owner'
      ? 'Owner onboarding now creates the entitlement automatically after invitation acceptance.'
      : 'Reseller invitations only create the scoped user identity. Entitlement creation still happens later when owners are onboarded.';
  }
}

function invitationCreatedMessage(invitation, defaultLabel) {
  if (invitation.role_name === 'owner') {
    return `${defaultLabel} Entitlement creation will be handled automatically when the owner accepts.`;
  }
  return defaultLabel;
}

function setNavigationOpen(isOpen) {
  const navShell = element('viewShell');
  const toggle = element('viewMenuToggle');
  const overlay = element('viewDrawerOverlay');
  const closeButton = element('viewDrawerClose');
  const nav = element('viewNavigation');
  if (!navShell || !toggle) {
    return;
  }
  if (isOpen && !navShell.classList.contains('nav-open')) {
    previousFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  }
  navShell.classList.toggle('nav-open', isOpen);
  toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  toggle.setAttribute('aria-label', isOpen ? 'Close navigation menu' : 'Open navigation menu');
  if (overlay) {
    overlay.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
  }
  if (nav) {
    nav.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
  }
  if (isOpen) {
    toggle.blur();
    window.setTimeout(() => {
      const focusTarget = closeButton || navigationFocusableElements()[0] || nav;
      if (focusTarget instanceof HTMLElement) {
        focusTarget.focus();
      }
    }, 30);
  } else {
    const restoreTarget = previousFocusedElement && document.contains(previousFocusedElement)
      ? previousFocusedElement
      : toggle;
    restoreTarget.focus();
    previousFocusedElement = null;
  }
}

function setChangePasswordModalOpen(isOpen) {
  const modal = element('changePasswordModal');
  const currentInput = element('change_password_current');
  if (!(modal instanceof HTMLElement)) {
    return;
  }
  if (isOpen) {
    changePasswordReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => {
      if (currentInput instanceof HTMLElement) {
        currentInput.focus();
      }
    }, 30);
    return;
  }
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
  const form = element('changePasswordForm');
  if (form instanceof HTMLFormElement) {
    form.reset();
  }
  const restoreTarget = changePasswordReturnFocus && document.contains(changePasswordReturnFocus)
    ? changePasswordReturnFocus
    : element('openChangePasswordButton');
  if (restoreTarget instanceof HTMLElement) {
    restoreTarget.focus();
  }
  changePasswordReturnFocus = null;
}

function activateView(viewId) {
  if (!document.querySelectorAll('.view-link[data-view]').length) {
    return;
  }
  document.querySelectorAll('.view-link[data-view]').forEach((button) => {
    button.classList.toggle('active', button.dataset.view === viewId);
  });
  document.querySelectorAll('.view-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === viewId);
  });
  setText('currentViewTitle', viewTitleMap[viewId] || 'Session');
  if (pageName === 'admin') {
    const nextSearch = new URLSearchParams(window.location.search);
    nextSearch.set('view', viewId);
    window.history.replaceState(null, '', `${window.location.pathname}?${nextSearch.toString()}`);
  }
  setNavigationOpen(false);
  if (pageName === 'admin' && currentUser) {
    loadViewData(viewId).catch((error) => setStatus(error.message, true));
  }
}

async function loadViewData(viewId) {
  const roleName = userRole();
  if (!roleName) {
    return;
  }
  if (viewId === 'overview') {
    if (roleName === 'platform_admin') {
      await Promise.all([loadAdminSummary(), loadResellerSummary(), loadOwnerSummary()]);
      return;
    }
    if (roleName === 'distributor') {
      await loadDistributorSummary();
      return;
    }
    if (roleName === 'reseller') {
      await Promise.all([loadResellerSummary(), loadOwnerSummary()]);
      return;
    }
    if (roleName === 'owner' || roleName === 'support') {
      await loadOwnerSummary();
    }
    return;
  }
  if (viewId === 'admin' && roleName === 'platform_admin') {
    await loadAdminSummary();
    return;
  }
  if (viewId === 'distributor' && roleName === 'distributor') {
    await loadDistributorSummary();
    return;
  }
  if (viewId === 'reseller' && roleName === 'reseller') {
    await loadResellerSummary();
    return;
  }
  if (viewId === 'owner' && (roleName === 'owner' || roleName === 'support' || roleName === 'platform_admin')) {
    await loadOwnerSummary();
  }
}

function resolvedRequestedView(roleName) {
  if (!requestedView || !Object.prototype.hasOwnProperty.call(viewTitleMap, requestedView)) {
    return preferredViewForRole(roleName);
  }
  const allowedRoles = viewRoleMap[requestedView] || [];
  if (allowedRoles.length && !allowedRoles.includes(roleName)) {
    return preferredViewForRole(roleName);
  }
  return requestedView;
}

function preferredViewForRole(roleName) {
  if (roleName === 'platform_admin') {
    return 'overview';
  }
  if (roleName === 'distributor') {
    return 'distributor';
  }
  if (roleName === 'reseller') {
    return 'reseller';
  }
  if (roleName === 'owner' || roleName === 'support') {
    return 'owner';
  }
  return 'overview';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function badgeClassForStatus(status) {
  if (status === 'accepted' || status === 'active') {
    return 'badge-accepted';
  }
  if (status === 'expired' || status === 'revoked' || status === 'failed') {
    return 'badge-expired';
  }
  return 'badge-pending';
}

function formatLifecycleTimestamp(label, value) {
  if (!value) {
    return `<span class="small">${label}: -</span>`;
  }
  return `<span class="small">${label}: ${escapeHtml(value)}</span>`;
}

function setMetricValue(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = String(value);
  }
}

function renderSummaryCards(containerId, cards) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }
  container.innerHTML = cards.map((card) => `
    <div class="metric">
      <div class="label">${escapeHtml(card.label)}</div>
      <div class="value">${escapeHtml(card.value)}</div>
    </div>
  `).join('');
}

function renderActivityList(containerId, items, emptyMessage) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }
  if (!items.length) {
    container.className = 'activity-list empty-list';
    container.textContent = emptyMessage;
    return;
  }
  container.className = 'activity-list';
  container.innerHTML = items.map((item) => `
    <div class="activity-item ${item.consoleFilter ? 'console-link' : ''}" ${item.consoleFilter ? `data-console-jump="${escapeHtml(item.consoleFilter)}"` : ''}>
      <div class="activity-title">${item.title}</div>
      ${item.badges ? `<div class="activity-badges">${item.badges}</div>` : ''}
      <div class="activity-meta">${item.meta}</div>
      ${item.actions ? `<div class="activity-actions">${item.actions}</div>` : ''}
    </div>
  `).join('');

  container.querySelectorAll('[data-console-jump]').forEach((element) => {
    element.addEventListener('click', () => {
      const nextFilter = element.dataset.consoleJump || 'all';
      if (pageName === 'console') {
        activeConsoleFilter = nextFilter;
        renderConsoleFilter();
        return;
      }
      window.location.href = `/admin/console?filter=${encodeURIComponent(nextFilter)}`;
    });
  });

  bindUserLifecycleActions(container);
  bindAuditJumpActions(container);
}

function bindUserLifecycleActions(root) {
  root.querySelectorAll('[data-user-quick-status]').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      const userUuid = button.dataset.userUuid || '';
      const status = button.dataset.userQuickStatus || '';
      const statusPath = button.dataset.userStatusPath || `/api/v1/admin/users/${encodeURIComponent(userUuid)}/status`;
      const reasonCode = button.dataset.userStatusReasonCode || 'ui_quick_action';
      if (!userUuid || !status) {
        return;
      }
      try {
        await api(statusPath, {
          method: 'PATCH',
          headers: authHeaders(),
          body: JSON.stringify({
            status,
            reason_code: reasonCode,
          }),
        });
        setStatus(`Updated user status to ${status}.`);
        await loadConsoleLandingData(userRole());
        await loadAuditEvents();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
  });

  root.querySelectorAll('[data-prepare-reassign]').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      document.getElementById('reassign_user_uuid').value = button.dataset.userUuid || '';
      document.getElementById('reassign_distributor_uuid').value = button.dataset.distributorUuid || '';
      document.getElementById('reassign_reseller_uuid').value = button.dataset.resellerUuid || '';
      document.getElementById('reassign_reason_code').value = 'manual_reassignment';
      setStatus('User copied into reassignment form.');
    });
  });

  root.querySelectorAll('[data-support-reinstate-user]').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      const userUuid = button.dataset.supportReinstateUser || '';
      if (!userUuid) {
        return;
      }
      try {
        const user = await api(`/api/v1/support/users/${encodeURIComponent(userUuid)}/reinstate`, {
          method: 'PATCH',
          headers: authHeaders(),
          body: JSON.stringify({
            reason_code: 'ui_support_emergency_reinstate',
          }),
        });
        setStatus(`Emergency reinstated ${user.email}.`);
        await loadConsoleLandingData(userRole());
        await loadAuditEvents();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
  });
}

function renderRows(rows) {
  if (!bodyEl) {
    return;
  }
  const columns = consoleColumnsForFilter(activeConsoleFilter);
  if (!rows.length) {
    bodyEl.innerHTML = `<tr><td colspan="${columns.length}" class="small">No rows returned.</td></tr>`;
    renderConsoleHeader(columns);
    return;
  }

  renderConsoleHeader(columns);

  bodyEl.innerHTML = rows.map((row) => `
    <tr>
      ${columns.map(([label, key]) => `<td data-label="${escapeHtml(label)}" class="${key === 'actions' ? 'console-actions-cell' : ''}">${row[key] || noConsoleActionsMarkup()}</td>`).join('')}
    </tr>
  `).join('');

  bindConsoleActions();
}

function consoleColumnsForFilter(filterName) {
  const keyColumnLabelByFilter = {
    all: 'Licence / Reference',
    entitlements: 'Licence Key',
    invitations: 'Invitation Role',
    assignments: 'Entitlement Ref',
    audit: 'Audit Action',
    updates: 'Release Version',
    health: 'Release Version',
  };

  const baseColumns = [
    ['Type', 'type'],
    ['Record', 'primary'],
    ['Scope / Status', 'scope'],
    ['Owner / User', 'owner'],
  ];

  if (filterName !== 'users' && filterName !== 'hierarchy') {
    baseColumns.push([keyColumnLabelByFilter[filterName] || 'Reference', 'keyInfo']);
  }

  baseColumns.push(['Details', 'details']);
  baseColumns.push(['Actions', 'actions']);
  return baseColumns;
}

function renderConsoleHeader(columns) {
  const headerRow = document.getElementById('consoleHeaderRow');
  if (!headerRow) {
    return;
  }
  headerRow.innerHTML = columns.map(([label]) => `<th>${escapeHtml(label)}</th>`).join('');
}

function hierarchySearchMatches(item, query) {
  if (!query) {
    return true;
  }
  return stripHtml(item.searchText || '').toLowerCase().includes(query);
}

function renderHierarchyUserCard(user) {
  return `
    <article class="hierarchy-user-card">
      <div class="hierarchy-user-card-header">
        <div>
          <div class="hierarchy-user-title">${escapeHtml(user.displayName || user.email || 'Unknown user')}</div>
          <div class="hierarchy-user-subtitle"><code class="inline">${escapeHtml(user.email || user.userUuid || '-')}</code></div>
        </div>
        <div class="hierarchy-user-badges">${statusBadgeMarkup(user.status || 'unknown')} <span class="pill">${escapeHtml(user.roleName || 'user')}</span></div>
      </div>
      <div class="hierarchy-user-meta">
        <span>Distributor: ${escapeHtml(user.distributorUuid || 'unscoped')}</span>
        <span>Reseller: ${escapeHtml(user.resellerUuid || 'unassigned')}</span>
        <span>User UUID: <code class="inline">${escapeHtml(user.userUuid || '-')}</code></span>
      </div>
      <div class="hierarchy-user-actions">${user.actions || noConsoleActionsMarkup()}</div>
    </article>
  `;
}

function renderHierarchyView(model) {
  if (!hierarchyViewEl) {
    return;
  }
  const query = consoleSearchQuery;
  const filteredGroups = (model || []).map((group) => ({
    ...group,
    branches: (group.branches || []).map((branch) => ({
      ...branch,
      users: (branch.users || []).filter((user) => hierarchySearchMatches(user, query)),
    })).filter((branch) => hierarchySearchMatches(branch, query) || branch.users.length),
  })).filter((group) => hierarchySearchMatches(group, query) || group.branches.length);

  if (!filteredGroups.length) {
    hierarchyViewEl.innerHTML = '<div class="small hierarchy-empty">No hierarchy relationships matched the current data.</div>';
    bindConsoleActions();
    return;
  }

  hierarchyViewEl.innerHTML = filteredGroups.map((group) => `
    <details class="hierarchy-group" open>
      <summary class="hierarchy-group-header">
        <div>
          <div class="hierarchy-group-title">${escapeHtml(group.title)}</div>
          <div class="hierarchy-group-subtitle">${escapeHtml(group.subtitle || '')}</div>
        </div>
        <div class="hierarchy-group-count">${escapeHtml(String(group.userCount || 0))} users</div>
      </summary>
      <div class="hierarchy-branches">
        ${(group.branches || []).map((branch) => `
          <details class="hierarchy-branch" open>
            <summary class="hierarchy-branch-header">
              <div>
                <div class="hierarchy-branch-title">${escapeHtml(branch.title)}</div>
                <div class="hierarchy-branch-subtitle">${escapeHtml(branch.subtitle || '')}</div>
              </div>
              <div class="hierarchy-branch-count">${escapeHtml(String((branch.users || []).length))}</div>
            </summary>
            <div class="hierarchy-user-list">
              ${(branch.users || []).map((user) => renderHierarchyUserCard(user)).join('') || '<div class="small hierarchy-empty">No users in this branch.</div>'}
            </div>
          </details>
        `).join('')}
      </div>
    </details>
  `).join('');

  bindConsoleActions();
}

function noConsoleActionsMarkup() {
  return '<span class="small">No direct actions</span>';
}

function consoleActionMenu(label, actionsMarkup) {
  if (!actionsMarkup) {
    return noConsoleActionsMarkup();
  }
  return `
    <details class="console-action-menu">
      <summary>${escapeHtml(label)}</summary>
      <div class="console-action-menu-panel">${actionsMarkup}</div>
    </details>
  `;
}

function viewerCanManageEntitlements() {
  return userRole() === 'platform_admin';
}

function viewerCanPrepareReassign() {
  return userRole() === 'platform_admin';
}

function viewerCanUpdateUserStatus(targetRoleName) {
  return userRole() === 'platform_admin' && targetRoleName !== 'platform_admin';
}

function viewerCanDistributorManageUser(targetRoleName) {
  return userRole() === 'distributor' && targetRoleName === 'reseller';
}

function viewerCanResellerManageUser(targetRoleName) {
  return userRole() === 'reseller' && targetRoleName === 'owner';
}

function viewerCanEmergencyReinstate(targetRoleName, targetStatus) {
  return userRole() === 'support'
    && targetStatus === 'suspended'
    && (targetRoleName === 'owner' || targetRoleName === 'reseller');
}

function buildUserConsoleActions(record) {
  const actions = [];
  if (viewerCanUpdateUserStatus(record.role_name)) {
    const nextStatus = record.status === 'suspended' ? 'active' : 'suspended';
    const nextLabel = record.status === 'suspended' ? 'Reinstate' : 'Suspend';
    actions.push(`<button type="button" class="secondary mini-button" data-user-quick-status="${escapeHtml(nextStatus)}" data-user-uuid="${escapeHtml(record.user_uuid)}" data-user-status-path="/api/v1/admin/users/${escapeHtml(record.user_uuid)}/status" data-user-status-reason-code="ui_quick_action">${escapeHtml(nextLabel)}</button>`);
  }
  if (viewerCanDistributorManageUser(record.role_name)) {
    const nextStatus = record.status === 'suspended' ? 'active' : 'suspended';
    const nextLabel = record.status === 'suspended' ? 'Reinstate' : 'Suspend';
    actions.push(`<button type="button" class="secondary mini-button" data-user-quick-status="${escapeHtml(nextStatus)}" data-user-uuid="${escapeHtml(record.user_uuid)}" data-user-status-path="/api/v1/distributor/users/${escapeHtml(record.user_uuid)}/status" data-user-status-reason-code="ui_distributor_scope_action">${escapeHtml(nextLabel)}</button>`);
  }
  if (viewerCanResellerManageUser(record.role_name)) {
    const nextStatus = record.status === 'suspended' ? 'active' : 'suspended';
    const nextLabel = record.status === 'suspended' ? 'Reinstate' : 'Suspend';
    actions.push(`<button type="button" class="secondary mini-button" data-user-quick-status="${escapeHtml(nextStatus)}" data-user-uuid="${escapeHtml(record.user_uuid)}" data-user-status-path="/api/v1/reseller/users/${escapeHtml(record.user_uuid)}/status" data-user-status-reason-code="ui_reseller_scope_action">${escapeHtml(nextLabel)}</button>`);
  }
  if (viewerCanEmergencyReinstate(record.role_name, record.status)) {
    actions.push(`<button type="button" class="secondary mini-button" data-support-reinstate-user="${escapeHtml(record.user_uuid)}">Emergency reinstate</button>`);
  }
  if (viewerCanPrepareReassign()) {
    actions.push(`<button type="button" class="secondary mini-button" data-prepare-reassign="true" data-user-uuid="${escapeHtml(record.user_uuid)}" data-distributor-uuid="${escapeHtml(record.distributor_uuid || '')}" data-reseller-uuid="${escapeHtml(record.reseller_uuid || '')}">Prepare reassign</button>`);
  }
  actions.push(`<button type="button" class="secondary mini-button" data-open-audit="true" data-audit-target-entity-type="authority_user" data-audit-target-entity-uuid="${escapeHtml(record.user_uuid)}">Audit</button>`);
  return consoleActionMenu('Actions', actions.join(''));
}

function buildEntitlementConsoleActions(record) {
  const actions = [];
  if (viewerCanManageEntitlements()) {
    actions.push(`<button type="button" class="mini-button secondary" data-entitlement-status="active" data-entitlement-uuid="${escapeHtml(record.entitlement_uuid)}">Activate</button>`);
    actions.push(`<button type="button" class="mini-button secondary" data-entitlement-status="suspended" data-entitlement-uuid="${escapeHtml(record.entitlement_uuid)}">Suspend</button>`);
    actions.push(`<button type="button" class="mini-button secondary" data-entitlement-status="revoked" data-entitlement-uuid="${escapeHtml(record.entitlement_uuid)}">Revoke</button>`);
  }
  actions.push(`<button type="button" class="mini-button secondary" data-open-audit="true" data-audit-target-entity-type="entitlement" data-audit-target-entity-uuid="${escapeHtml(record.entitlement_uuid)}">Audit</button>`);
  return consoleActionMenu('Actions', actions.join(''));
}

function stripHtml(value) {
  return String(value || '').replace(/<[^>]*>/g, ' ');
}

function rowSearchText(row) {
  return [row.type, row.primary, row.scope, row.owner, row.keyInfo, row.details, row.actions]
    .map((value) => stripHtml(value).toLowerCase())
    .join(' ');
}

function allConsoleRows() {
  return [
    ...consoleRowsByFilter.users,
    ...consoleRowsByFilter.entitlements,
    ...consoleRowsByFilter.hierarchy,
    ...consoleRowsByFilter.invitations,
    ...consoleRowsByFilter.assignments,
    ...consoleRowsByFilter.audit,
    ...consoleRowsByFilter.updates,
    ...consoleRowsByFilter.health,
  ];
}

function rowsForActiveFilter() {
  const sourceRows = activeConsoleFilter === 'all'
    ? allConsoleRows()
    : (consoleRowsByFilter[activeConsoleFilter] || []);
  if (!consoleSearchQuery) {
    return sourceRows;
  }
  return sourceRows.filter((row) => rowSearchText(row).includes(consoleSearchQuery));
}

function renderConsoleFilter() {
  const counts = {
    all: allConsoleRows().length,
    users: consoleRowsByFilter.users.length,
    hierarchy: consoleRowsByFilter.hierarchy.length,
    entitlements: consoleRowsByFilter.entitlements.length,
    invitations: consoleRowsByFilter.invitations.length,
    assignments: consoleRowsByFilter.assignments.length,
    audit: consoleRowsByFilter.audit.length,
    updates: consoleRowsByFilter.updates.length,
    health: consoleRowsByFilter.health.length,
  };
  document.querySelectorAll('.console-filter').forEach((button) => {
    button.classList.toggle('active', button.dataset.consoleFilter === activeConsoleFilter);
  });
  document.querySelectorAll('[data-filter-count]').forEach((element) => {
    const filterName = element.dataset.filterCount || 'all';
    element.textContent = String(counts[filterName] || 0);
  });
  const tableWrapEl = document.querySelector('.table-wrap');
  const showHierarchyView = activeConsoleFilter === 'hierarchy';
  if (hierarchyViewEl) {
    hierarchyViewEl.classList.toggle('hidden', !showHierarchyView);
  }
  if (hierarchyExplainEl) {
    hierarchyExplainEl.classList.toggle('hidden', !showHierarchyView);
  }
  if (tableWrapEl) {
    tableWrapEl.classList.toggle('hidden', showHierarchyView);
  }
  if (showHierarchyView) {
    renderHierarchyView(hierarchyViewModel);
  } else if (bodyEl) {
    renderRows(rowsForActiveFilter());
  }
}

function setConsoleRows(filterName, rows) {
  consoleRowsByFilter[filterName] = rows;
}

function resetConsoleRows() {
  consoleRowsByFilter = {
    users: [],
    entitlements: [],
    hierarchy: [],
    invitations: [],
    assignments: [],
    audit: [],
    updates: [],
    health: [],
  };
  activeConsoleFilter = 'all';
  consoleSearchQuery = '';
  adminUsersCache = [];
  auditState = {
    items: [],
    rows: [],
    nextOffset: null,
    hasMore: false,
    loadedCount: 0,
    filters: {
      target_entity_type: '',
      target_entity_uuid: '',
      action: '',
      actor_role_name: '',
      limit: '',
    },
  };
  hierarchyViewModel = [];
}

function updateEventRows(records) {
  return records.map((record) => ({
    type: `<span class="pill ${badgeClassForStatus(record.status)}">Update</span>`,
    primary: `${escapeHtml(record.tenant_name || record.approved_owner_email || 'Unknown installation')}<br><span class="small"><code class="inline">${escapeHtml(record.installation_uuid)}</code></span>`,
    scope: `${escapeHtml(record.status)}<br><span class="small">${escapeHtml(record.created_at)}</span>`,
    owner: escapeHtml(record.approved_owner_email || '-'),
    keyInfo: `${escapeHtml(record.from_release_version || 'unknown')} -> <code class="inline">${escapeHtml(record.to_release_version)}</code>`,
    details: `${escapeHtml(record.tenant_name || record.application_key || 'Unknown tenant')}<br><span class="small">${escapeHtml(record.failure_reason || 'no failure')}</span>`,
  }));
}

function stateReportRows(records) {
  return records.map((record) => ({
    type: '<span class="pill">Health</span>',
    primary: `${escapeHtml(record.tenant_name || record.approved_owner_email || 'Unknown installation')}<br><span class="small"><code class="inline">${escapeHtml(record.installation_uuid)}</code></span>`,
    scope: `${escapeHtml(record.health_state || 'unknown')}<br><span class="small">${escapeHtml(record.reported_at)}</span>`,
    owner: escapeHtml(record.approved_owner_email || '-'),
    keyInfo: `<code class="inline">${escapeHtml(record.current_release_version)}</code><br><span class="small">${escapeHtml(record.deployment_mode || 'unknown mode')}</span>`,
    details: `${escapeHtml(record.tenant_name || record.application_key || 'Unknown tenant')}<br><span class="small">${escapeHtml(record.activation_status)} / ${escapeHtml(record.licence_status)}</span>`,
  }));
}

function entitlementRows(records) {
  return records.map((record) => ({
    type: '<span class="pill">Entitlement</span>',
    primary: `${escapeHtml(record.tenant_name || record.approved_owner_email || 'Unassigned entitlement')}<br><span class="small"><code class="inline">${escapeHtml(record.entitlement_uuid)}</code></span>`,
    scope: `${statusBadgeMarkup(record.activation_status)}<br><span class="small">${record.tenant_name || 'No tenant'}</span>`,
    owner: record.approved_owner_email,
    keyInfo: `<code class="inline">${record.application_key}</code><br><span class="small">${record.licence_status}</span>`,
    details: `${record.installation_uuid || 'unbound'}<br><span class="small">grace ${record.offline_grace_days}d</span>`,
    actions: buildEntitlementConsoleActions(record),
  }));
}

function invitationRows(records) {
  return records.map((record) => ({
    type: `<span class="pill ${badgeClassForStatus(record.effective_status || record.status)}">Invitation</span>`,
    primary: `${escapeHtml(record.email)}<br><span class="small"><code class="inline">${escapeHtml(record.invitation_uuid)}</code></span>`,
    scope: `<span class="pill ${badgeClassForStatus(record.effective_status || record.status)}">${escapeHtml(record.effective_status || record.status)}</span><br><span class="small">${escapeHtml(record.reseller_uuid || 'no reseller scope')}</span>`,
    owner: escapeHtml(record.email),
    keyInfo: `<code class="inline">${escapeHtml(record.role_name)}</code>`,
    details: `<code class="inline">${escapeHtml(record.invitation_token)}</code><br>${escapeHtml(record.email_delivery_message || 'Email delivery status unavailable.')}<br>${formatLifecycleTimestamp('created', record.created_at)}<br>${formatLifecycleTimestamp('expires', record.expires_at)}<br>${formatLifecycleTimestamp('accepted', record.accepted_at)}`,
    actions: consoleActionMenu('Actions', `<button type="button" class="mini-button" data-copy-token="${escapeHtml(record.invitation_token)}">Copy token</button><button type="button" class="mini-button" data-fill-token="${escapeHtml(record.invitation_token)}">Use token</button>`),
  }));
}

function invitationDeliveryStatusMessage(invitation, createdLabel) {
  if (invitation.email_delivered) {
    return `${createdLabel} Email delivery succeeded.`;
  }
  if (invitation.email_delivery_attempted) {
    return `${createdLabel} Email delivery was attempted but did not succeed. Use the token fallback.`;
  }
  return `${createdLabel} Email delivery was skipped. Configure MAIL_* settings and the authority base URL, or share the token manually.`;
}

function bindConsoleActions() {
  document.querySelectorAll('[data-copy-token]').forEach((button) => {
    button.addEventListener('click', async () => {
      const token = button.dataset.copyToken || '';
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(token);
          setStatus('Invitation token copied to clipboard.');
        } else {
          throw new Error('Clipboard API unavailable');
        }
      } catch (error) {
        setStatus(`Copy failed: ${error.message}`, true);
      }
    });
  });

  document.querySelectorAll('[data-fill-token]').forEach((button) => {
    button.addEventListener('click', () => {
      const token = button.dataset.fillToken || '';
      document.getElementById('accept_invitation_token').value = token;
      setAcceptStatus('Invitation token copied into the acceptance form.');
    });
  });

  document.querySelectorAll('[data-entitlement-status]').forEach((button) => {
    button.addEventListener('click', async () => {
      const entitlementUuid = button.dataset.entitlementUuid || '';
      const activationStatus = button.dataset.entitlementStatus || '';
      if (!entitlementUuid || !activationStatus) {
        return;
      }
      try {
        await api(`/api/v1/admin/installations/${encodeURIComponent(entitlementUuid)}/activation-status`, {
          method: 'PATCH',
          headers: authHeaders(),
          body: JSON.stringify({
            activation_status: activationStatus,
            reason_code: 'ui_inline_action',
          }),
        });
        setStatus(`Updated entitlement to ${activationStatus}.`);
        await loadInstallations();
        await loadAuditEvents();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
  });

  bindUserLifecycleActions(document);
  bindAuditJumpActions(document);
}

function bindAuditJumpActions(root) {
  root.querySelectorAll('[data-open-audit]').forEach((button) => {
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      const nextSearch = new URLSearchParams();
      nextSearch.set('filter', 'audit');
      const targetEntityType = button.dataset.auditTargetEntityType || '';
      const targetEntityUuid = button.dataset.auditTargetEntityUuid || '';
      const action = button.dataset.auditAction || '';
      const actorRoleName = button.dataset.auditActorRoleName || '';
      if (targetEntityType) {
        nextSearch.set('target_entity_type', targetEntityType);
      }
      if (targetEntityUuid) {
        nextSearch.set('target_entity_uuid', targetEntityUuid);
      }
      if (action) {
        nextSearch.set('action', action);
      }
      if (actorRoleName) {
        nextSearch.set('actor_role_name', actorRoleName);
      }
      window.location.href = `/admin/console?${nextSearch.toString()}`;
    });
  });
}

function resellerSummaryRows(summary) {
  setMetricValue('metricResellerCount', summary.installation_count || 0);
  return summary.installations.map((record) => ({
    type: '<span class="pill">Reseller Installation</span>',
    primary: `${escapeHtml(record.tenant_name || record.approved_owner_email || 'Reseller installation')}<br><span class="small"><code class="inline">${escapeHtml(record.entitlement_uuid)}</code></span>`,
    scope: `${summary.reseller_uuid}<br><span class="small">${statusBadgeMarkup(record.activation_status)}</span>`,
    owner: record.approved_owner_email,
    keyInfo: `<code class="inline">${record.application_key}</code>`,
    details: `${record.tenant_name || 'No tenant'}<br><span class="small">${record.licence_status}</span>`,
    actions: buildEntitlementConsoleActions(record),
  }));
}

function distributorSummaryRows(summary) {
  setMetricValue('metricResellerCount', summary.installation_count || 0);
  return summary.installations.map((record) => ({
    type: '<span class="pill">Distributor Installation</span>',
    primary: `${escapeHtml(record.tenant_name || record.approved_owner_email || 'Distributor installation')}<br><span class="small"><code class="inline">${escapeHtml(record.entitlement_uuid)}</code></span>`,
    scope: `${summary.distributor_uuid}<br><span class="small">${statusBadgeMarkup(record.activation_status)}</span>`,
    owner: record.approved_owner_email,
    keyInfo: `<code class="inline">${record.application_key}</code>`,
    details: `${record.tenant_name || 'No tenant'}<br><span class="small">${record.licence_status}</span>`,
    actions: buildEntitlementConsoleActions(record),
  }));
}

function userReferenceMarkup(record, fallbackLabel = 'User Record') {
  if (record.role_name) {
    return `<span class="pill">${escapeHtml(record.role_name)}</span>`;
  }
  return `<span class="small">${escapeHtml(fallbackLabel)}</span>`;
}

function userDetailsMarkup(record, secondaryText) {
  return `${statusBadgeMarkup(record.status)}<br><span class="small">${escapeHtml(secondaryText)}</span><br><span class="small">UUID ${escapeHtml(record.user_uuid || '-')}</span>`;
}

function userRows(records) {
  return records.map((record) => ({
    type: `<span class="pill ${badgeClassForStatus(record.status)}">${escapeHtml(record.role_name)}</span>`,
    primary: `<code class="inline">${escapeHtml(record.email)}</code>`,
    scope: `${escapeHtml(record.distributor_uuid || 'no distributor')}<br><span class="small">${escapeHtml(record.reseller_uuid || 'no reseller')}</span>`,
    owner: escapeHtml(record.display_name || '-'),
    keyInfo: userReferenceMarkup(record, 'User record'),
    details: userDetailsMarkup(record, `updated ${record.updated_at || record.created_at || '-'}`),
    actions: buildUserConsoleActions(record),
  }));
}

function hierarchyRowsFromUsers(records) {
  return records.map((record) => ({
    type: `<span class="pill">${escapeHtml(record.role_name)}</span>`,
    primary: `<code class="inline">${escapeHtml(record.email)}</code>`,
    scope: `${escapeHtml(record.distributor_uuid || 'no distributor')}<br><span class="small">${escapeHtml(record.reseller_uuid || 'no reseller')}</span>`,
    owner: escapeHtml(record.display_name || '-'),
    keyInfo: userReferenceMarkup(record, 'Hierarchy record'),
    details: userDetailsMarkup(record, `joined ${record.created_at || '-'}`),
    actions: buildUserConsoleActions(record),
  }));
}

function normalizeHierarchyUser(record, roleNameOverride = null) {
  return {
    userUuid: record.user_uuid,
    email: record.email,
    displayName: record.display_name || '',
    roleName: roleNameOverride || record.role_name || 'user',
    status: record.status || 'unknown',
    distributorUuid: record.distributor_uuid || '',
    resellerUuid: record.reseller_uuid || '',
    actions: buildUserConsoleActions(record),
    searchText: [
      record.email,
      record.display_name,
      roleNameOverride || record.role_name,
      record.status,
      record.distributor_uuid,
      record.reseller_uuid,
      record.user_uuid,
    ].join(' '),
  };
}

function hierarchyBranch(title, subtitle, users) {
  return {
    title,
    subtitle,
    users,
    searchText: [title, subtitle, ...users.map((user) => user.searchText)].join(' '),
  };
}

function buildHierarchyModelFromUsers(records) {
  const distributorGroups = new Map();
  const unscopedUsers = [];

  records.forEach((record) => {
    const user = normalizeHierarchyUser(record);
    const distributorKey = record.distributor_uuid || '__unscoped__';
    if (!record.distributor_uuid) {
      unscopedUsers.push(user);
      return;
    }
    if (!distributorGroups.has(distributorKey)) {
      distributorGroups.set(distributorKey, {
        title: `Distributor ${record.distributor_uuid}`,
        subtitle: 'Tenant root for reseller and owner scope',
        resellerManagers: [],
        resellers: new Map(),
        directOwners: [],
      });
    }
    const group = distributorGroups.get(distributorKey);
    if (record.role_name === 'distributor') {
      group.resellerManagers.push(user);
      return;
    }
    if (record.role_name === 'reseller') {
      const resellerKey = record.reseller_uuid || `__reseller__${record.user_uuid}`;
      const resellerBranch = group.resellers.get(resellerKey) || {
        title: `Reseller ${record.reseller_uuid || 'pending scope'}`,
        subtitle: 'Reseller account and its owner users',
        users: [],
      };
      resellerBranch.users.unshift(user);
      group.resellers.set(resellerKey, resellerBranch);
      return;
    }
    if (record.role_name === 'owner') {
      if (record.reseller_uuid) {
        const resellerKey = record.reseller_uuid;
        const resellerBranch = group.resellers.get(resellerKey) || {
          title: `Reseller ${record.reseller_uuid}`,
          subtitle: 'Scoped owner accounts',
          users: [],
        };
        resellerBranch.users.push(user);
        group.resellers.set(resellerKey, resellerBranch);
      } else {
        group.directOwners.push(user);
      }
      return;
    }
    group.directOwners.push(user);
  });

  const models = Array.from(distributorGroups.values()).map((group) => {
    const branches = [];
    if (group.resellerManagers.length) {
      branches.push(hierarchyBranch('Distributor managers', 'Accounts invited at the distributor level', group.resellerManagers));
    }
    Array.from(group.resellers.values()).forEach((resellerBranch) => {
      branches.push(hierarchyBranch(resellerBranch.title, resellerBranch.subtitle, resellerBranch.users));
    });
    if (group.directOwners.length) {
      branches.push(hierarchyBranch('Direct distributor users', 'Users scoped to the distributor without a reseller branch', group.directOwners));
    }
    return {
      title: group.title,
      subtitle: group.subtitle,
      branches,
      userCount: branches.reduce((total, branch) => total + branch.users.length, 0),
      searchText: [group.title, group.subtitle, ...branches.map((branch) => branch.searchText)].join(' '),
    };
  });

  if (unscopedUsers.length) {
    const unscopedBranch = hierarchyBranch('Unscoped accounts', 'Users not yet attached to a distributor or reseller branch', unscopedUsers);
    models.push({
      title: 'Unscoped hierarchy',
      subtitle: 'Accounts that exist but are not attached to a tenant branch',
      branches: [unscopedBranch],
      userCount: unscopedUsers.length,
      searchText: `Unscoped hierarchy ${unscopedBranch.searchText}`,
    });
  }

  return models;
}

function buildHierarchyModelFromDistributorSummary(summary) {
  const resellerBranches = (summary.resellers || []).map((record) => {
    const resellerUser = normalizeHierarchyUser(record, 'reseller');
    const ownerUsers = (summary.owners || [])
      .filter((owner) => owner.reseller_uuid === record.reseller_uuid)
      .map((owner) => normalizeHierarchyUser(owner, 'owner'));
    return hierarchyBranch(
      `Reseller ${record.reseller_uuid || record.email}`,
      `${record.owner_count || ownerUsers.length} owners in scope`,
      [resellerUser, ...ownerUsers],
    );
  });

  const unassignedOwners = (summary.owners || [])
    .filter((owner) => !(summary.resellers || []).some((reseller) => reseller.reseller_uuid === owner.reseller_uuid))
    .map((owner) => normalizeHierarchyUser(owner, 'owner'));
  if (unassignedOwners.length) {
    resellerBranches.push(hierarchyBranch('Unassigned owners', 'Owner accounts without a matching reseller branch', unassignedOwners));
  }

  return [{
    title: `Distributor ${summary.distributor_uuid}`,
    subtitle: 'Resellers and owners grouped by delegated scope',
    branches: resellerBranches,
    userCount: resellerBranches.reduce((total, branch) => total + branch.users.length, 0),
    searchText: [`Distributor ${summary.distributor_uuid}`, ...resellerBranches.map((branch) => branch.searchText)].join(' '),
  }];
}

function buildHierarchyModelFromResellerSummary(summary) {
  const ownerUsers = (summary.owners || []).map((record) => normalizeHierarchyUser(record, 'owner'));
  const ownerBranch = hierarchyBranch('Owner accounts', 'Users invited into this reseller scope', ownerUsers);
  return [{
    title: `Reseller ${summary.reseller_uuid}`,
    subtitle: `Distributor ${currentUser?.distributor_uuid || 'unscoped distributor'}`,
    branches: [ownerBranch],
    userCount: ownerUsers.length,
    searchText: [`Reseller ${summary.reseller_uuid}`, ownerBranch.searchText].join(' '),
  }];
}

function hierarchyRowsFromDistributorSummary(summary) {
  const resellerRows = (summary.resellers || []).map((record) => ({
    type: '<span class="pill">reseller</span>',
    primary: `<code class="inline">${escapeHtml(record.email)}</code>`,
    scope: `${escapeHtml(summary.distributor_uuid)}<br><span class="small">${escapeHtml(record.reseller_uuid || 'no reseller')}</span>`,
    owner: escapeHtml(record.display_name || '-'),
    keyInfo: '<span class="pill">Reseller Branch</span>',
    details: userDetailsMarkup(record, `${String(record.owner_count)} owners in branch`),
    actions: buildUserConsoleActions(record),
  }));
  const ownerRows = (summary.owners || []).map((record) => ({
    type: '<span class="pill">owner</span>',
    primary: `<code class="inline">${escapeHtml(record.email)}</code>`,
    scope: `${escapeHtml(summary.distributor_uuid)}<br><span class="small">${escapeHtml(record.reseller_uuid || 'no reseller')}</span>`,
    owner: escapeHtml(record.display_name || '-'),
    keyInfo: '<span class="pill">Owner Account</span>',
    details: userDetailsMarkup(record, `${String(record.installation_count)} installations`),
    actions: buildUserConsoleActions(record),
  }));
  return [...resellerRows, ...ownerRows];
}

function hierarchyRowsFromResellerSummary(summary) {
  return (summary.owners || []).map((record) => ({
    type: '<span class="pill">owner</span>',
    primary: `<code class="inline">${escapeHtml(record.email)}</code>`,
    scope: `${escapeHtml(currentUser?.distributor_uuid || 'no distributor')}<br><span class="small">${escapeHtml(summary.reseller_uuid)}</span>`,
    owner: escapeHtml(record.display_name || '-'),
    keyInfo: '<span class="pill">Owner Account</span>',
    details: userDetailsMarkup(record, `${String(record.installation_count)} installations`),
    actions: buildUserConsoleActions(record),
  }));
}

function ownerRows(records) {
  setMetricValue('metricOwnerCount', records.length);
  return entitlementRows(records);
}

function assignmentActivityItems(records) {
  return records.map((record) => ({
    title: `${escapeHtml(record.owner_email)} · ${escapeHtml(record.tenant_name || record.application_key)}`,
    meta: `${escapeHtml(record.activation_status)} · ${escapeHtml(record.created_at)}`,
    consoleFilter: 'assignments',
  }));
}

function invitationActivityItems(records) {
  return records.map((record) => ({
    title: `${escapeHtml(record.email)} · ${escapeHtml(record.role_name)}`,
    meta: `${escapeHtml(record.effective_status)} · expires ${escapeHtml(record.expires_at)}`,
    consoleFilter: 'invitations',
  }));
}

function ownerUpdateActivityItems(records) {
  return records.map((record) => ({
    title: `${escapeHtml(record.tenant_name || record.application_key)} · ${escapeHtml(record.status)}`,
    meta: `${escapeHtml(record.from_release_version || 'unknown')} -> ${escapeHtml(record.to_release_version)} · ${escapeHtml(record.created_at)}`,
    consoleFilter: 'updates',
  }));
}

function stateReportActivityItems(records) {
  return records.map((record) => ({
    title: `${escapeHtml(record.tenant_name || record.application_key)} · ${escapeHtml(record.health_state || 'unknown')}`,
    meta: `${escapeHtml(record.current_release_version)} · ${escapeHtml(record.reported_at)}`,
    consoleFilter: 'health',
  }));
}

function scopedUserActivityItems(records, emptyScopeLabel) {
  if (!records.length) {
    return [];
  }
  return records.map((record) => ({
    title: `${escapeHtml(record.email)} · ${escapeHtml(record.role_name)}`,
    badges: `${statusBadgeMarkup(record.status)} ${record.status === 'orphaned' ? '<span class="pill badge-pending">needs reassignment</span>' : ''}`,
    meta: `${escapeHtml(record.distributor_uuid || 'no distributor')} · ${escapeHtml(record.reseller_uuid || emptyScopeLabel)}`,
    actions: `<button type="button" class="secondary mini-button" data-open-audit="true" data-audit-target-entity-type="authority_user" data-audit-target-entity-uuid="${escapeHtml(record.user_uuid)}">Audit</button>`,
    consoleFilter: 'hierarchy',
  }));
}

function auditEventActivityItems(records) {
  return records.map((record) => ({
    title: `${escapeHtml(record.action)} · ${escapeHtml(record.target_entity_type)}`,
    meta: `${escapeHtml(record.reason_code || 'no reason')} · ${escapeHtml(record.created_at || '-')}`,
    actions: `<button type="button" class="secondary mini-button" data-open-audit="true" data-audit-target-entity-type="${escapeHtml(record.target_entity_type)}" data-audit-target-entity-uuid="${escapeHtml(record.target_entity_uuid)}">Focus entity</button>`,
    consoleFilter: 'audit',
  }));
}

function formatAuditStateBlock(label, payload) {
  if (!payload || !Object.keys(payload).length) {
    return `<span class="small">${escapeHtml(label)}: -</span>`;
  }
  const entries = Object.entries(payload).map(([key, value]) => `${escapeHtml(key)}=${escapeHtml(JSON.stringify(value))}`);
  return `<div class="audit-state-block"><span class="small audit-state-label">${escapeHtml(label)}</span><code class="inline">${entries.join(', ')}</code></div>`;
}

function auditTransitionSummary(record) {
  if (record.action === 'user_scope_reassigned') {
    const before = record.scope_before || {};
    const after = record.scope_after || {};
    return `<div class="audit-transition">scope: ${escapeHtml(before.distributor_uuid || before.reseller_uuid || 'unscoped')} -> ${escapeHtml(after.distributor_uuid || after.reseller_uuid || 'unscoped')}</div>`;
  }
  if (record.action === 'user_orphaned') {
    return '<div class="audit-transition">scope removed and user marked orphaned</div>';
  }
  if (record.action === 'user_status_changed') {
    const previousStatus = record.previous_state?.status || '-';
    const nextStatus = record.new_state?.status || '-';
    return `<div class="audit-transition">status: ${escapeHtml(String(previousStatus))} -> ${escapeHtml(String(nextStatus))}</div>`;
  }
  if (record.action === 'entitlement_status_changed') {
    const previousStatus = record.previous_state?.activation_status || '-';
    const nextStatus = record.new_state?.activation_status || '-';
    return `<div class="audit-transition">activation: ${escapeHtml(String(previousStatus))} -> ${escapeHtml(String(nextStatus))}</div>`;
  }
  const previousState = record.previous_state || {};
  const newState = record.new_state || {};
  const transitionKey = Object.keys(newState).find((key) => Object.prototype.hasOwnProperty.call(previousState, key))
    || Object.keys(newState)[0]
    || Object.keys(previousState)[0];
  if (!transitionKey) {
    return '';
  }
  const previousValue = Object.prototype.hasOwnProperty.call(previousState, transitionKey) ? previousState[transitionKey] : '-';
  const nextValue = Object.prototype.hasOwnProperty.call(newState, transitionKey) ? newState[transitionKey] : '-';
  return `<div class="audit-transition">${escapeHtml(transitionKey)}: ${escapeHtml(String(previousValue))} -> ${escapeHtml(String(nextValue))}</div>`;
}

function auditEventRows(records) {
  return records.map((record) => ({
    type: '<span class="pill">Audit</span>',
    primary: `${escapeHtml(record.target_email || record.target_entity_type || 'Audit event')}<br><span class="small"><code class="inline">${escapeHtml(record.target_entity_uuid)}</code></span>`,
    scope: `${escapeHtml(record.target_entity_type)}<br><span class="small">${escapeHtml(record.created_at || '-')}</span>`,
    owner: escapeHtml(record.target_email || '-'),
    keyInfo: `<code class="inline">${escapeHtml(record.action)}</code>`,
    details: `${escapeHtml(record.reason_code || 'no reason')}<br><span class="small">${escapeHtml(record.actor_email || record.actor_role_name || 'unknown actor')}</span>${auditTransitionSummary(record)}${formatAuditStateBlock('previous', record.previous_state)}${formatAuditStateBlock('new', record.new_state)}${formatAuditStateBlock('scope before', record.scope_before)}${formatAuditStateBlock('scope after', record.scope_after)}`,
    actions: consoleActionMenu('Actions', `<button type="button" class="mini-button secondary" data-open-audit="true" data-audit-target-entity-type="${escapeHtml(record.target_entity_type)}" data-audit-target-entity-uuid="${escapeHtml(record.target_entity_uuid)}">Focus entity</button>`),
  }));
}

function statusBadgeMarkup(status) {
  return `<span class="pill ${badgeClassForStatus(status)}">${escapeHtml(status)}</span>`;
}

function adminUserActivityItems(records) {
  return records.map((record) => {
    const nextQuickAction = record.status === 'suspended' ? 'active' : 'suspended';
    const nextQuickLabel = record.status === 'suspended' ? 'Reinstate' : 'Suspend';
    return {
      title: `${escapeHtml(record.email)} · ${escapeHtml(record.role_name)}`,
      badges: `${statusBadgeMarkup(record.status)} ${record.status === 'orphaned' ? '<span class="pill badge-pending">needs reassignment</span>' : ''}`,
      meta: `${escapeHtml(record.distributor_uuid || 'no distributor')} · ${escapeHtml(record.reseller_uuid || 'no reseller')}`,
      actions: `
        <button type="button" class="secondary mini-button" data-user-quick-status="${escapeHtml(nextQuickAction)}" data-user-uuid="${escapeHtml(record.user_uuid)}">${escapeHtml(nextQuickLabel)}</button>
        <button type="button" class="secondary mini-button" data-prepare-reassign="true" data-user-uuid="${escapeHtml(record.user_uuid)}" data-distributor-uuid="${escapeHtml(record.distributor_uuid || '')}" data-reseller-uuid="${escapeHtml(record.reseller_uuid || '')}">Prepare reassign</button>
        <button type="button" class="secondary mini-button" data-open-audit="true" data-audit-target-entity-type="authority_user" data-audit-target-entity-uuid="${escapeHtml(record.user_uuid)}">Audit</button>
      `,
    };
  });
}

function matchingUsers(query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return adminUsersCache.slice(0, 8);
  }
  return adminUsersCache.filter((record) => [
    record.email,
    record.user_uuid,
    record.display_name,
    record.role_name,
    record.status,
    record.distributor_uuid,
    record.reseller_uuid,
  ].some((value) => String(value || '').toLowerCase().includes(normalized))).slice(0, 8);
}

function lookupActivityItems(records, target) {
  return records.map((record) => ({
    title: `${escapeHtml(record.email)} · ${escapeHtml(record.role_name)}`,
    badges: `${statusBadgeMarkup(record.status)}`,
    meta: `${escapeHtml(record.user_uuid)} · ${escapeHtml(record.distributor_uuid || 'no distributor')} · ${escapeHtml(record.reseller_uuid || 'no reseller')}`,
    actions: `<button type="button" class="secondary mini-button" data-select-user-lookup="${escapeHtml(target)}" data-user-uuid="${escapeHtml(record.user_uuid)}" data-distributor-uuid="${escapeHtml(record.distributor_uuid || '')}" data-reseller-uuid="${escapeHtml(record.reseller_uuid || '')}">Use user</button>`,
  }));
}

function bindUserLookupActions(root) {
  root.querySelectorAll('[data-select-user-lookup]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.dataset.selectUserLookup || '';
      const userUuid = button.dataset.userUuid || '';
      const distributorUuid = button.dataset.distributorUuid || '';
      const resellerUuid = button.dataset.resellerUuid || '';
      if (target === 'lifecycle') {
        const userField = document.getElementById('admin_user_uuid');
        if (userField instanceof HTMLInputElement) {
          userField.value = userUuid;
        }
        setStatus('Lifecycle user field populated.');
        return;
      }
      if (target === 'reassign') {
        const userField = document.getElementById('reassign_user_uuid');
        const distributorField = document.getElementById('reassign_distributor_uuid');
        const resellerField = document.getElementById('reassign_reseller_uuid');
        if (userField instanceof HTMLInputElement) {
          userField.value = userUuid;
        }
        if (distributorField instanceof HTMLInputElement) {
          distributorField.value = distributorUuid;
        }
        if (resellerField instanceof HTMLInputElement) {
          resellerField.value = resellerUuid;
        }
        setStatus('Reassignment fields populated.');
      }
    });
  });
}

function renderUserLookupResults(inputId, containerId, target) {
  const input = document.getElementById(inputId);
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  const matches = matchingUsers(input.value);
  renderActivityList(containerId, lookupActivityItems(matches, target), 'No matching users found.');
  const container = document.getElementById(containerId);
  if (container instanceof HTMLElement) {
    bindUserLookupActions(container);
  }
}

function applyAuditFiltersToInputs() {
  const requested = requestedAuditFilters();
  const mapping = {
    audit_target_entity_type: requested.target_entity_type,
    audit_target_entity_uuid: requested.target_entity_uuid,
    audit_action: requested.action,
    audit_actor_role_name: requested.actor_role_name,
    audit_limit: requested.limit,
  };
  Object.entries(mapping).forEach(([id, value]) => {
    const node = element(id);
    if (node instanceof HTMLInputElement && value) {
      node.value = value;
    }
  });
}

function setAuditState(payload, filters, mode = 'replace') {
  const nextItems = mode === 'append' ? [...auditState.items, ...payload.items] : payload.items.slice();
  auditState = {
    items: nextItems,
    rows: auditEventRows(nextItems),
    nextOffset: payload.next_offset,
    hasMore: payload.has_more,
    loadedCount: nextItems.length,
    filters: { ...filters },
  };
  setConsoleRows('audit', auditState.rows);
  renderActivityList('adminAuditEvents', auditEventActivityItems(auditState.items), 'No audit events loaded yet.');
  const loadMoreButton = document.getElementById('loadMoreAuditEventsButton');
  if (loadMoreButton instanceof HTMLButtonElement) {
    loadMoreButton.disabled = !auditState.hasMore;
  }
  persistConsoleState();
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(payload && payload.detail ? payload.detail : text || `Request failed: ${response.status}`);
  }
  return payload;
}

async function loadSession() {
  if (!sessionToken) {
    sessionToken = persistedSessionToken();
  }
  const me = await api('/api/v1/auth/me', { headers: authHeaders() });
  setSession(me);
  return me;
}

async function handleLogin() {
  try {
    const payload = await api('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('login_email').value.trim(),
        password: document.getElementById('login_password').value,
      }),
    });
    setSession(payload.user, payload.session_token);
    if (pageName === 'console') {
      await loadConsoleLandingData(payload.user.role_name);
    } else {
      const nextView = resolvedRequestedView(payload.user.role_name);
      const loginLandingView = nextView === 'session' ? 'overview' : nextView;
      activateView(loginLandingView);
    }
    if (pageName !== 'console' && payload.user.role_name === 'platform_admin') {
      await loadAdminSummary();
      await loadOwnerSummary();
      await loadInstallations();
    } else if (pageName !== 'console' && payload.user.role_name === 'distributor') {
      await loadDistributorSummary();
    } else if (pageName !== 'console' && payload.user.role_name === 'reseller') {
      await loadResellerSummary();
    } else if (pageName !== 'console' && (payload.user.role_name === 'owner' || payload.user.role_name === 'support')) {
      await loadOwnerSummary();
      await loadOwnerInstallations();
    }
    setStatus(`Signed in as ${payload.user.email} (${payload.user.role_name})`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function handleAcceptInvitation() {
  try {
    const payload = await api('/api/v1/auth/accept-invitation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        invitation_token: document.getElementById('accept_invitation_token').value.trim(),
        display_name: document.getElementById('accept_display_name').value.trim() || null,
        password: document.getElementById('accept_password').value,
      }),
    });
    setAcceptStatus(`Invitation accepted for ${payload.email}. You can now log in.`);
    window.location.href = `/admin?login_email=${encodeURIComponent(payload.email)}`;
  } catch (error) {
    setAcceptStatus(error.message, true);
  }
}

async function handleLogout() {
  try {
    await api('/api/v1/auth/logout', { method: 'POST', headers: authHeaders() });
    sessionToken = '';
    currentUser = null;
    setSession(null, '');
    renderRows([]);
    window.location.href = '/admin';
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function handleChangePassword() {
  const currentPassword = document.getElementById('change_password_current')?.value || '';
  const newPassword = document.getElementById('change_password_new')?.value || '';
  const confirmPassword = document.getElementById('change_password_confirm')?.value || '';

  if (newPassword.length < 8) {
    setStatus('New password must be at least 8 characters long.', true);
    return;
  }
  if (newPassword !== confirmPassword) {
    setStatus('New password confirmation does not match.', true);
    return;
  }

  try {
    await api('/api/v1/auth/change-password', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    setChangePasswordModalOpen(false);
    setStatus('Password updated successfully.');
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadInstallations() {
  try {
    const records = await api('/api/v1/admin/installations', { headers: authHeaders() });
    setConsoleRows('entitlements', entitlementRows(records));
    renderConsoleFilter();
    setStatus(`Loaded ${records.length} entitlements.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadAdminUsers() {
  try {
    const users = await api('/api/v1/admin/users', { headers: authHeaders() });
    adminUsersCache = users;
    setConsoleRows('users', userRows(users));
    setConsoleRows('hierarchy', hierarchyRowsFromUsers(users));
    hierarchyViewModel = buildHierarchyModelFromUsers(users);
    renderActivityList('adminUserDirectory', adminUserActivityItems(users), 'No users loaded yet.');
    renderUserLookupResults('admin_user_lookup', 'adminUserLookupResults', 'lifecycle');
    renderUserLookupResults('reassign_user_lookup', 'reassignUserLookupResults', 'reassign');
    renderConsoleFilter();
    setStatus(`Loaded ${users.length} users.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadAuditEvents() {
  try {
    const query = new URLSearchParams();
    const offset = 0;
    const filters = currentAuditFiltersFromInputs();
    query.set('offset', String(offset));
    if (filters.target_entity_type) {
      query.set('target_entity_type', filters.target_entity_type);
    }
    if (filters.target_entity_uuid) {
      query.set('target_entity_uuid', filters.target_entity_uuid);
    }
    if (filters.action) {
      query.set('action', filters.action);
    }
    if (filters.actor_role_name) {
      query.set('actor_role_name', filters.actor_role_name);
    }
    if (filters.limit) {
      query.set('limit', filters.limit);
    }
    const querySuffix = query.toString() ? `?${query.toString()}` : '';
    const payload = await api(`/api/v1/admin/audit-events${querySuffix}`, { headers: authHeaders() });
    setAuditState(payload, filters, 'replace');
    renderConsoleFilter();
    setStatus(`Loaded ${payload.items.length} audit events.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadMoreAuditEvents() {
  if (auditState.nextOffset === null) {
    return;
  }
  try {
    const query = new URLSearchParams();
    const filters = auditState.filters;
    query.set('offset', String(auditState.nextOffset));
    if (filters.target_entity_type) {
      query.set('target_entity_type', filters.target_entity_type);
    }
    if (filters.target_entity_uuid) {
      query.set('target_entity_uuid', filters.target_entity_uuid);
    }
    if (filters.action) {
      query.set('action', filters.action);
    }
    if (filters.actor_role_name) {
      query.set('actor_role_name', filters.actor_role_name);
    }
    if (filters.limit) {
      query.set('limit', filters.limit);
    }
    const payload = await api(`/api/v1/admin/audit-events?${query.toString()}`, { headers: authHeaders() });
    setAuditState(payload, filters, 'append');
    renderConsoleFilter();
    setStatus(`Loaded ${payload.items.length} more audit events.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function updateUserStatus() {
  try {
    const userUuid = document.getElementById('admin_user_uuid').value.trim();
    const user = await api(`/api/v1/admin/users/${encodeURIComponent(userUuid)}/status`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({
        status: document.getElementById('admin_user_status').value,
        reason_code: document.getElementById('admin_user_reason_code').value.trim(),
        operator_note: document.getElementById('admin_user_operator_note').value.trim() || null,
      }),
    });
    setStatus(`Updated ${user.email} to ${user.status}.`);
    await loadAdminUsers();
    await loadAuditEvents();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function reassignUserScope() {
  try {
    const userUuid = document.getElementById('reassign_user_uuid').value.trim();
    const user = await api(`/api/v1/admin/users/${encodeURIComponent(userUuid)}/scope`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({
        distributor_uuid: document.getElementById('reassign_distributor_uuid').value.trim() || null,
        reseller_uuid: document.getElementById('reassign_reseller_uuid').value.trim() || null,
        reason_code: document.getElementById('reassign_reason_code').value.trim(),
        operator_note: document.getElementById('reassign_operator_note').value.trim() || null,
      }),
    });
    setStatus(`Reassigned ${user.email} and restored status ${user.status}.`);
    await loadAdminUsers();
    await loadAuditEvents();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function updateEntitlementStatus() {
  try {
    const entitlementUuid = document.getElementById('admin_entitlement_uuid').value.trim();
    const entitlement = await api(`/api/v1/admin/installations/${encodeURIComponent(entitlementUuid)}/activation-status`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({
        activation_status: document.getElementById('admin_entitlement_status').value,
        reason_code: document.getElementById('admin_entitlement_reason_code').value.trim(),
        operator_note: document.getElementById('admin_entitlement_operator_note').value.trim() || null,
      }),
    });
    setStatus(`Updated entitlement ${entitlement.entitlement_uuid} to ${entitlement.activation_status}.`);
    await loadInstallations();
    await loadAuditEvents();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function supportReinstateUser() {
  try {
    const userUuid = document.getElementById('support_user_uuid').value.trim();
    const user = await api(`/api/v1/support/users/${encodeURIComponent(userUuid)}/reinstate`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({
        reason_code: document.getElementById('support_reason_code').value.trim(),
        operator_note: document.getElementById('support_operator_note').value.trim() || null,
      }),
    });
    setStatus(`Emergency reinstated ${user.email}.`);
    if (userRole() === 'support') {
      await loadOwnerSummary();
    }
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function saveInstallation() {
  try {
    const payload = {
      application_key: document.getElementById('application_key').value.trim() || null,
      installation_uuid: document.getElementById('installation_uuid').value.trim() || null,
      approved_owner_email: document.getElementById('approved_owner_email').value.trim(),
      owner_enabled: document.getElementById('owner_enabled').value === 'true',
      licence_status: document.getElementById('licence_status').value,
      offline_grace_days: Number(document.getElementById('offline_grace_days').value || 0),
      tenant_name: document.getElementById('tenant_name').value.trim() || null,
      notes: document.getElementById('notes').value.trim() || null,
    };
    const record = await api('/api/v1/admin/installations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    setConsoleRows('entitlements', entitlementRows([record]));
    renderConsoleFilter();
    document.getElementById('assignment_entitlement_uuid').value = record.entitlement_uuid;
    document.getElementById('reseller_assignment_entitlement_uuid').value = record.entitlement_uuid;
    setStatus(`Saved entitlement ${record.entitlement_uuid}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function startOwnerOnboarding() {
  try {
    const email = document.getElementById('owner_onboarding_email').value.trim();
    const distributorUuid = document.getElementById('owner_onboarding_distributor_uuid').value.trim() || null;
    const resellerUuid = document.getElementById('owner_onboarding_reseller_uuid').value.trim() || null;
    const expiresInDays = Number(document.getElementById('owner_onboarding_expires_in_days').value || 7);
    const displayName = document.getElementById('owner_onboarding_display_name').value.trim();

    if (!email) {
      setStatus('Owner onboarding requires an email address.', true);
      return;
    }

    const invitation = await api('/api/v1/admin/invitations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        email,
        role_name: 'owner',
        distributor_uuid: distributorUuid,
        reseller_uuid: resellerUuid,
        expires_in_days: expiresInDays,
      }),
    });
    setConsoleRows('invitations', invitationRows([invitation]));
    renderConsoleFilter();

    document.getElementById('invite_email').value = email;
    document.getElementById('invite_role_name').value = 'owner';
    document.getElementById('invite_distributor_uuid').value = distributorUuid || '';
    document.getElementById('invite_reseller_uuid').value = resellerUuid || '';
    document.getElementById('invite_expires_in_days').value = String(expiresInDays);
    document.getElementById('approved_owner_email').value = email;
    if (displayName) {
      document.getElementById('tenant_name').value = displayName;
    }

    setStatus(
      invitationDeliveryStatusMessage(
        invitation,
        `Owner onboarding started for ${invitation.email}. The entitlement will be created automatically after acceptance.`
      ),
      !invitation.email_delivered,
    );
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function createInvitation() {
  try {
    const roleName = document.getElementById('invite_role_name').value;
    const distributorUuid = document.getElementById('invite_distributor_uuid').value.trim() || null;
    if (roleName === 'distributor' && !distributorUuid) {
      setStatus('Distributor invitations require a distributor UUID.', true);
      return;
    }

    const invitation = await api('/api/v1/admin/invitations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        email: document.getElementById('invite_email').value.trim(),
        role_name: roleName,
        distributor_uuid: distributorUuid,
        reseller_uuid: document.getElementById('invite_reseller_uuid').value.trim() || null,
        expires_in_days: Number(document.getElementById('invite_expires_in_days').value || 7),
      }),
    });
    setConsoleRows('invitations', invitationRows([invitation]));
    renderConsoleFilter();
    setStatus(invitationDeliveryStatusMessage(invitation, invitationCreatedMessage(invitation, `Created invitation for ${invitation.email}.`)), !invitation.email_delivered);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadInvitations() {
  try {
    const invitations = await api('/api/v1/admin/invitations', { headers: authHeaders() });
    setConsoleRows('invitations', invitationRows(invitations));
    renderConsoleFilter();
    setStatus(`Loaded ${invitations.length} invitations.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function assignInstallation(path, entitlementFieldId, userFieldId) {
  const assignment = await api(path, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      entitlement_uuid: document.getElementById(entitlementFieldId).value.trim(),
      user_email: document.getElementById(userFieldId).value.trim(),
    }),
  });
  setConsoleRows('assignments', [{
    type: '<span class="pill">Assignment</span>',
    primary: `<code class="inline">${assignment.assignment_uuid}</code>`,
    scope: `${assignment.created_at}`,
    owner: assignment.user_uuid,
    keyInfo: `<code class="inline">${assignment.entitlement_uuid}</code>`,
    details: assignment.assigned_by_user_uuid || 'system',
  }]);
  renderConsoleFilter();
  setStatus(`Assigned entitlement ${assignment.entitlement_uuid}.`);
}

async function loadOwnerInstallations() {
  try {
    const records = await api('/api/v1/dashboard/owner/installations', { headers: authHeaders() });
    setConsoleRows('entitlements', ownerRows(records));
    renderConsoleFilter();
    setStatus(`Loaded ${records.length} owner installations.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadOwnerSummary() {
  try {
    const summary = await api('/api/v1/dashboard/owner/summary', { headers: authHeaders() });
    setMetricValue('metricOwnerCount', summary.installation_count || 0);
    renderSummaryCards('ownerSummaryCards', [
      { label: 'Installations', value: summary.installation_count },
      { label: 'Active Licences', value: summary.active_installation_count },
      { label: 'Grace Licences', value: summary.grace_installation_count },
      { label: 'Pending Activation', value: summary.pending_activation_count },
      { label: 'Suspended', value: summary.suspended_installation_count },
      { label: 'Orphaned', value: summary.orphaned_installation_count },
    ]);
    renderActivityList('ownerRecentUpdates', ownerUpdateActivityItems(summary.recent_updates || []), 'No lifecycle activity yet.');
    renderActivityList('ownerRecentHealth', stateReportActivityItems(summary.recent_health_reports || []), 'No owner health activity yet.');
    setConsoleRows('updates', updateEventRows(summary.recent_updates || []));
    setConsoleRows('health', stateReportRows(summary.recent_health_reports || []));
    renderConsoleFilter();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadAdminSummary() {
  try {
    const summary = await api('/api/v1/dashboard/admin/summary', { headers: authHeaders() });
    setMetricValue('metricPendingInvitations', summary.pending_invitation_count || 0);
    setMetricValue('metricRecentAssignments', (summary.recent_assignments || []).length);
    renderSummaryCards('adminSummaryCards', [
      { label: 'Entitlements', value: summary.entitlement_count },
      { label: 'Active', value: summary.active_entitlement_count },
      { label: 'Pending Activation', value: summary.pending_activation_count },
      { label: 'Pending Invitations', value: summary.pending_invitation_count },
      { label: 'Suspended Users', value: summary.suspended_user_count },
      { label: 'Orphaned Users', value: summary.orphaned_user_count },
    ]);
    renderActivityList('adminRecentInvitations', invitationActivityItems(summary.recent_invitations || []), 'No invitation activity yet.');
    renderActivityList('adminRecentAssignments', assignmentActivityItems(summary.recent_assignments || []), 'No assignment activity yet.');
    renderActivityList('adminRecentHealth', stateReportActivityItems(summary.recent_health_reports || []), 'No health activity yet.');
    setConsoleRows('invitations', invitationRows(summary.recent_invitations || []));
    setConsoleRows('assignments', summary.recent_assignments.map((record) => ({
      type: '<span class="pill">Assignment</span>',
      primary: `<code class="inline">${escapeHtml(record.assignment_uuid)}</code>`,
      scope: `${escapeHtml(record.created_at)}`,
      owner: escapeHtml(record.owner_email),
      keyInfo: `<code class="inline">${escapeHtml(record.entitlement_uuid)}</code>`,
      details: `${escapeHtml(record.tenant_name || record.application_key)}`,
    })));
    setConsoleRows('health', stateReportRows(summary.recent_health_reports || []));
    renderConsoleFilter();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadResellerSummary() {
  try {
    const summary = await api('/api/v1/dashboard/reseller/summary', { headers: authHeaders() });
    setMetricValue('metricPendingInvitations', summary.pending_invitation_count || 0);
    setMetricValue('metricRecentAssignments', (summary.recent_assignments || []).length);
    renderSummaryCards('resellerSummaryCards', [
      { label: 'Owners', value: summary.owner_count },
      { label: 'Installations', value: summary.installation_count },
      { label: 'Active', value: summary.active_installation_count },
      { label: 'Pending Invitations', value: summary.pending_invitation_count },
      { label: 'Suspended Owners', value: summary.suspended_owner_count },
      { label: 'Orphaned Owners', value: summary.orphaned_owner_count },
    ]);
    renderActivityList('resellerRecentAssignments', assignmentActivityItems(summary.recent_assignments || []), 'No reseller assignment activity yet.');
    renderActivityList('resellerRecentHealth', stateReportActivityItems(summary.recent_health_reports || []), 'No reseller health activity yet.');
    setConsoleRows('entitlements', resellerSummaryRows(summary));
    setConsoleRows('users', userRows(summary.owners || []));
    setConsoleRows('hierarchy', hierarchyRowsFromResellerSummary(summary));
    hierarchyViewModel = buildHierarchyModelFromResellerSummary(summary);
    setConsoleRows('health', stateReportRows(summary.recent_health_reports || []));
    renderConsoleFilter();
    setStatus(`Loaded reseller summary for ${summary.reseller_uuid}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadDistributorSummary() {
  try {
    const summary = await api('/api/v1/dashboard/distributor/summary', { headers: authHeaders() });
    setMetricValue('metricPendingInvitations', summary.pending_invitation_count || 0);
    setMetricValue('metricRecentAssignments', (summary.recent_assignments || []).length);
    renderSummaryCards('distributorSummaryCards', [
      { label: 'Resellers', value: summary.reseller_count },
      { label: 'Owners', value: summary.owner_count },
      { label: 'Installations', value: summary.installation_count },
      { label: 'Pending Invitations', value: summary.pending_invitation_count },
      { label: 'Suspended Resellers', value: summary.suspended_reseller_count },
      { label: 'Orphaned Resellers', value: summary.orphaned_reseller_count },
      { label: 'Suspended Owners', value: summary.suspended_owner_count },
      { label: 'Orphaned Owners', value: summary.orphaned_owner_count },
    ]);
    renderActivityList('distributorRecentAssignments', assignmentActivityItems(summary.recent_assignments || []), 'No distributor assignment activity yet.');
    renderActivityList('distributorRecentHealth', stateReportActivityItems(summary.recent_health_reports || []), 'No distributor health activity yet.');
    setConsoleRows('entitlements', distributorSummaryRows(summary));
    setConsoleRows('users', userRows([...(summary.resellers || []), ...(summary.owners || [])]));
    setConsoleRows('hierarchy', hierarchyRowsFromDistributorSummary(summary));
    hierarchyViewModel = buildHierarchyModelFromDistributorSummary(summary);
    setConsoleRows('assignments', (summary.recent_assignments || []).map((record) => ({
      type: '<span class="pill">Assignment</span>',
      primary: `<code class="inline">${escapeHtml(record.assignment_uuid)}</code>`,
      scope: `${escapeHtml(record.distributor_uuid || '-')}`,
      owner: escapeHtml(record.owner_email),
      keyInfo: `<code class="inline">${escapeHtml(record.entitlement_uuid)}</code>`,
      details: `${escapeHtml(record.tenant_name || record.application_key)}`,
    })));
    setConsoleRows('health', stateReportRows(summary.recent_health_reports || []));
    renderConsoleFilter();
    setStatus(`Loaded distributor summary for ${summary.distributor_uuid}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadDistributorScopedUsers(path, targetId, emptyMessage, emptyScopeLabel) {
  try {
    const records = await api(path, { headers: authHeaders() });
    renderActivityList(targetId, scopedUserActivityItems(records, emptyScopeLabel), emptyMessage);
    setConsoleRows('users', userRows(records));
    setConsoleRows('hierarchy', hierarchyRowsFromUsers(records));
    hierarchyViewModel = buildHierarchyModelFromUsers(records);
    renderConsoleFilter();
    setStatus(`Loaded ${records.length} scoped users.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function loadConsoleLandingData(roleName) {
  if (roleName === 'platform_admin') {
    await loadInstallations();
    await loadAdminUsers();
    if (activeConsoleFilter === 'audit' || requestedAuditFilters().target_entity_uuid || requestedAuditFilters().target_entity_type) {
      await loadAuditEvents();
      const requestedLoaded = Number(requestedAuditFilters().loaded || '0');
      while (auditState.hasMore && auditState.loadedCount < requestedLoaded) {
        await loadMoreAuditEvents();
      }
    } else {
      await loadAuditEvents();
    }
    await loadAdminSummary();
    return;
  }
  if (roleName === 'distributor') {
    await loadDistributorSummary();
    return;
  }
  if (roleName === 'reseller') {
    await loadResellerSummary();
    return;
  }
  if (roleName === 'owner' || roleName === 'support') {
    await loadOwnerSummary();
    await loadOwnerInstallations();
  }
}

function bindClick(id, handler) {
  const node = element(id);
  if (node) {
    node.addEventListener('click', handler);
  }
}

function bindChange(id, handler) {
  const node = element(id);
  if (node) {
    node.addEventListener('change', handler);
  }
}

function bindFormSubmit(id, handler) {
  const node = element(id);
  if (!(node instanceof HTMLFormElement)) {
    return;
  }
  node.addEventListener('submit', (event) => {
    event.preventDefault();
    handler();
  });
}

function bindPasswordVisibility(toggleId, inputId) {
  const toggle = element(toggleId);
  const input = element(inputId);
  if (!(toggle instanceof HTMLInputElement) || !(input instanceof HTMLInputElement)) {
    return;
  }
  toggle.addEventListener('change', () => {
    input.type = toggle.checked ? 'text' : 'password';
  });
}

document.querySelectorAll('.view-link[data-view]').forEach((button) => {
  button.addEventListener('click', () => activateView(button.dataset.view));
});

bindClick('viewMenuToggle', () => {
  const navShell = element('viewShell');
  if (!navShell) {
    return;
  }
  const isOpen = !navShell.classList.contains('nav-open');
  setNavigationOpen(isOpen);
});
bindClick('viewDrawerClose', () => setNavigationOpen(false));
bindClick('viewDrawerOverlay', () => setNavigationOpen(false));
document.addEventListener('keydown', (event) => {
  const changePasswordModal = element('changePasswordModal');
  if (event.key === 'Escape' && changePasswordModal instanceof HTMLElement && !changePasswordModal.classList.contains('hidden')) {
    setChangePasswordModalOpen(false);
    return;
  }
  const navShell = element('viewShell');
  if (!navShell?.classList.contains('nav-open')) {
    return;
  }
  if (event.key === 'Escape') {
    setNavigationOpen(false);
    return;
  }
  if (event.key !== 'Tab') {
    return;
  }
  const focusable = navigationFocusableElements();
  if (!focusable.length) {
    return;
  }
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
    return;
  }
  if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
});

document.querySelectorAll('.console-filter').forEach((button) => {
  button.addEventListener('click', () => {
    activeConsoleFilter = button.dataset.consoleFilter || 'all';
    persistConsoleState();
    renderConsoleFilter();
  });
});

bindChange('consoleSearchInput', (event) => {
  const target = event.target;
  if (!(target instanceof HTMLInputElement)) {
    return;
  }
  consoleSearchQuery = target.value.trim().toLowerCase();
  renderConsoleFilter();
});

bindChange('admin_user_lookup', () => renderUserLookupResults('admin_user_lookup', 'adminUserLookupResults', 'lifecycle'));
bindChange('reassign_user_lookup', () => renderUserLookupResults('reassign_user_lookup', 'reassignUserLookupResults', 'reassign'));

bindFormSubmit('loginForm', handleLogin);
bindClick('logoutButton', handleLogout);
bindClick('openChangePasswordButton', () => setChangePasswordModalOpen(true));
bindFormSubmit('acceptInvitationForm', handleAcceptInvitation);
bindClick('backToLoginButton', () => { window.location.href = '/admin'; });
bindFormSubmit('changePasswordForm', handleChangePassword);
bindClick('closeChangePasswordButton', () => setChangePasswordModalOpen(false));
bindClick('cancelChangePasswordButton', () => setChangePasswordModalOpen(false));
bindClick('changePasswordBackdrop', () => setChangePasswordModalOpen(false));
bindPasswordVisibility('show_login_password', 'login_password');
bindPasswordVisibility('show_accept_password', 'accept_password');
bindClick('loadSessionButton', async () => {
  try {
    const me = await loadSession();
    setStatus(`Session refreshed for ${me.email}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
});
bindClick('loadInstallations', loadInstallations);
bindClick('saveInstallation', saveInstallation);
bindClick('startOwnerOnboardingButton', startOwnerOnboarding);
bindClick('createInvitation', createInvitation);
bindClick('loadInvitations', loadInvitations);
bindClick('loadAdminUsersButton', loadAdminUsers);
bindClick('updateUserStatusButton', updateUserStatus);
bindClick('reassignUserScopeButton', reassignUserScope);
bindClick('updateEntitlementStatusButton', updateEntitlementStatus);
bindClick('loadAuditEventsButton', loadAuditEvents);
bindClick('loadMoreAuditEventsButton', () => loadMoreAuditEvents().catch((error) => setStatus(error.message, true)));
bindClick('assignInstallation', () => assignInstallation('/api/v1/admin/installation-assignments', 'assignment_entitlement_uuid', 'assignment_user_email').catch((error) => setStatus(error.message, true)));
bindClick('resellerInviteButton', async () => {
  try {
    const invitation = await api('/api/v1/reseller/invitations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        email: document.getElementById('reseller_invite_email').value.trim(),
        expires_in_days: Number(document.getElementById('reseller_invite_expires').value || 7),
      }),
    });
    setConsoleRows('invitations', invitationRows([invitation]));
    renderConsoleFilter();
    setStatus(invitationDeliveryStatusMessage(invitation, invitationCreatedMessage(invitation, `Reseller invitation created for ${invitation.email}.`)), !invitation.email_delivered);
  } catch (error) {
    setStatus(error.message, true);
  }
});
bindClick('resellerAssignButton', () => assignInstallation('/api/v1/reseller/installation-assignments', 'reseller_assignment_entitlement_uuid', 'reseller_assignment_user_email').catch((error) => setStatus(error.message, true)));
bindClick('loadOwnerInstallations', loadOwnerInstallations);
bindClick('loadResellerSummary', loadResellerSummary);
bindClick('loadDistributorSummary', loadDistributorSummary);
bindClick('loadDistributorSummaryTab', loadDistributorSummary);
bindClick('loadAdminSummary', loadAdminSummary);
bindClick('loadOverviewResellerSummary', loadResellerSummary);
bindClick('loadOwnerSummary', loadOwnerSummary);
bindClick('supportReinstateUserButton', supportReinstateUser);
bindClick('sessionOpenConsoleButton', () => { window.location.href = '/admin/console'; });
bindChange('distributor_invite_role_name', syncDistributorInviteForm);
bindClick('distributorInviteButton', async () => {
  try {
    const invitedRole = document.getElementById('distributor_invite_role_name').value;
    const invitation = await api('/api/v1/distributor/invitations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        email: document.getElementById('distributor_invite_email').value.trim(),
        role_name: invitedRole,
      }),
    });
    setConsoleRows('invitations', invitationRows([invitation]));
    renderConsoleFilter();
    setStatus(invitationDeliveryStatusMessage(invitation, invitationCreatedMessage(invitation, `Invitation created for ${invitation.email}.`)), !invitation.email_delivered);
  } catch (error) {
    setStatus(error.message, true);
  }
});
syncDistributorInviteForm();
bindClick('loadDistributorResellersButton', () => loadDistributorScopedUsers('/api/v1/distributor/resellers', 'distributorResellerList', 'No reseller users loaded yet.', 'no reseller'));
bindClick('loadDistributorOwnersButton', () => loadDistributorScopedUsers('/api/v1/distributor/owners', 'distributorOwnerList', 'No owner users loaded yet.', 'no reseller'));
prefillInvitationTokenFromUrl();
applyAuditFiltersToInputs();
bindClick('distributorAssignButton', () => assignInstallation('/api/v1/distributor/installation-assignments', 'distributor_assignment_entitlement_uuid', 'distributor_assignment_user_email').catch((error) => setStatus(error.message, true)));

const requestedLoginEmail = searchParams.get('login_email');
if (requestedLoginEmail) {
  const loginEmailField = document.getElementById('login_email');
  if (loginEmailField instanceof HTMLInputElement) {
    loginEmailField.value = requestedLoginEmail;
  }
}

const requestedFilter = new URLSearchParams(window.location.search).get('filter');
if (requestedFilter && (requestedFilter === 'all' || Object.prototype.hasOwnProperty.call(consoleRowsByFilter, requestedFilter))) {
  activeConsoleFilter = requestedFilter;
}
renderConsoleFilter();
updateAuthView();
syncRoleVisibility();

async function restoreSessionOnLoad() {
  if (pageName === 'admin' && requestedInvitationToken) {
    return;
  }
  const storedToken = persistedSessionToken();
  if (!storedToken) {
    return;
  }
  sessionToken = storedToken;
  try {
    const me = await loadSession();
    if (pageName === 'console') {
      await loadConsoleLandingData(me.role_name);
    } else {
      const nextView = resolvedRequestedView(me.role_name);
      activateView(nextView);
    }
  } catch (error) {
    sessionToken = '';
    currentUser = null;
    storeSessionToken('');
    updateAuthView();
  }
}

restoreSessionOnLoad();
