const SESSION_TOKEN_STORAGE_KEY = 'authority.sessionToken';
const TOAST_MAX_COUNT = 5;
const TOAST_TIMEOUT_MS = 4200;

const searchParams = new URLSearchParams(window.location.search);
const requestedInvitationToken = searchParams.get('invitation_token');
const requestedTab = searchParams.get('tab') || searchParams.get('view');
const requestedEditEntitlementUuid = searchParams.get('edit_entitlement_uuid');
const loginEmailHint = searchParams.get('login_email');

let sessionToken = '';
let currentUser = null;
let activeTab = 'home';
let peopleStatusFilter = '';
let licenceStatusFilter = '';
let peopleSearchQuery = '';
let licenceSearchQuery = '';
let usersCache = [];
let licencesCache = [];
let selectedPersonUuid = '';
let selectedLicenceUuid = '';
let changePasswordReturnFocus = null;
let entityPickerReturnFocus = null;
let entityPickerState = { targetInputId: '', kind: '' };
let auditState = {
  items: [],
  nextOffset: null,
  hasMore: false,
  filters: {},
};

const TAB_ROLES = {
  home: ['platform_admin', 'distributor', 'reseller', 'owner', 'support'],
  people: ['platform_admin', 'distributor', 'reseller', 'support'],
  licences: ['platform_admin', 'distributor', 'reseller', 'owner'],
  me: ['platform_admin', 'distributor', 'reseller', 'owner', 'support'],
};

const INVITE_ROLES_BY_ACTOR = {
  platform_admin: ['distributor', 'reseller', 'owner', 'support'],
  distributor: ['reseller', 'owner'],
  reseller: ['owner'],
  support: [],
  owner: [],
};

function element(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function authHeaders(extra = {}) {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${sessionToken}`,
    ...extra,
  };
}

function persistedSessionToken() {
  try {
    return localStorage.getItem(SESSION_TOKEN_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

function persistSessionToken(token) {
  try {
    if (token) {
      localStorage.setItem(SESSION_TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
    }
  } catch {
    /* ignore */
  }
}

function showToast(message, tone = 'info') {
  const region = element('toastRegion');
  if (!(region instanceof HTMLElement)) {
    return;
  }
  const toast = document.createElement('div');
  toast.className = `toast ${tone === 'error' ? 'error' : tone === 'success' ? 'success' : ''}`.trim();
  toast.textContent = message;
  region.prepend(toast);
  while (region.children.length > TOAST_MAX_COUNT) {
    region.lastElementChild?.remove();
  }
  window.setTimeout(() => toast.remove(), TOAST_TIMEOUT_MS);
}

function setStatus(message, isError = false) {
  const bar = element('statusBar');
  if (bar instanceof HTMLElement) {
    bar.textContent = message || '';
    bar.classList.toggle('visible', Boolean(message));
  }
  if (message) {
    showToast(message, isError ? 'error' : 'info');
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }
  if (!response.ok) {
    const detail = payload && typeof payload === 'object' ? payload.detail : payload;
    throw new Error(detail || text || `Request failed: ${response.status}`);
  }
  return payload;
}

function userRole() {
  return currentUser?.role_name || null;
}

function roleAllowsTab(tabId) {
  const role = userRole();
  return role ? (TAB_ROLES[tabId] || []).includes(role) : false;
}

function statusBadgeMarkup(status) {
  const safe = escapeHtml(status || 'unknown');
  return `<span class="pill ${safe}">${safe}</span>`;
}

function setSession(user, token = sessionToken) {
  currentUser = user;
  sessionToken = token || '';
  persistSessionToken(sessionToken);

  const loggedOut = !user;
  element('loggedOutPanel')?.classList.toggle('hidden', !loggedOut || Boolean(requestedInvitationToken && !user));
  element('acceptInvitationCard')?.classList.toggle('hidden', !(requestedInvitationToken && loggedOut));
  element('authenticatedShell')?.classList.toggle('hidden', loggedOut);
  document.querySelectorAll('[data-auth-visibility="logged-out"]').forEach((node) => {
    node.classList.toggle('hidden', !loggedOut);
  });

  const email = user?.email || '-';
  const role = user?.role_name || 'Unauthenticated';
  ['currentEmail', 'meEmail'].forEach((id) => {
    const node = element(id);
    if (node) node.textContent = email;
  });
  ['currentRole', 'meRole'].forEach((id) => {
    const node = element(id);
    if (node) node.textContent = role;
  });

  syncTabVisibility();
  syncInviteRoleOptions();
  syncToolsVisibility();
}

function syncTabVisibility() {
  document.querySelectorAll('#bottomTabs .tab-button').forEach((button) => {
    const tabId = button.dataset.tab;
    const allowed = roleAllowsTab(tabId);
    button.classList.toggle('tab-hidden', !allowed);
    if (!allowed && button.classList.contains('active')) {
      button.classList.remove('active');
    }
  });
  const issueFab = element('openLicenceWizardButton');
  if (issueFab) {
    const canIssue = ['platform_admin', 'distributor', 'reseller'].includes(userRole() || '');
    issueFab.classList.toggle('hidden', !canIssue);
  }
  const inviteFab = element('openInviteSheetButton');
  if (inviteFab) {
    const canInvite = (INVITE_ROLES_BY_ACTOR[userRole()] || []).length > 0;
    inviteFab.classList.toggle('hidden', !canInvite);
  }
}

function syncToolsVisibility() {
  const tools = element('toolsSection');
  if (!(tools instanceof HTMLElement)) return;
  const role = userRole();
  const show = role === 'platform_admin' || role === 'support';
  tools.classList.toggle('hidden', !show);
  tools.querySelectorAll('[data-tool]').forEach((block) => {
    const tool = block.dataset.tool;
    let visible = show;
    if (tool === 'vpn' || tool === 'audit') {
      visible = role === 'platform_admin';
    }
    if (tool === 'emergency') {
      visible = role === 'platform_admin' || role === 'support';
    }
    block.classList.toggle('hidden', !visible);
  });
}

function syncInviteRoleOptions() {
  const select = element('invite_role_name');
  if (!(select instanceof HTMLSelectElement)) return;
  const allowed = INVITE_ROLES_BY_ACTOR[userRole()] || [];
  select.innerHTML = allowed.map((role) => `<option value="${role}">${role}</option>`).join('');
  syncInviteScopeFields();
}

function syncInviteScopeFields() {
  const role = element('invite_role_name')?.value;
  const actor = userRole();
  const distributorField = element('inviteDistributorField');
  const resellerField = element('inviteResellerField');
  if (distributorField) {
    const showDistributor = actor === 'platform_admin' && (role === 'distributor' || role === 'reseller' || role === 'owner');
    distributorField.classList.toggle('hidden', !showDistributor);
  }
  if (resellerField) {
    const showReseller = (actor === 'platform_admin' || actor === 'distributor') && role === 'owner';
    resellerField.classList.toggle('hidden', !showReseller);
  }
}

function persistTabState(tabId) {
  const next = new URLSearchParams(window.location.search);
  next.delete('view');
  next.set('tab', tabId);
  if (selectedPersonUuid && tabId === 'person') {
    next.set('person', selectedPersonUuid);
  } else {
    next.delete('person');
  }
  if (selectedLicenceUuid && tabId === 'licence') {
    next.set('licence', selectedLicenceUuid);
  } else {
    next.delete('licence');
  }
  const query = next.toString();
  window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
}

function activateTab(tabId, options = {}) {
  const { skipLoad = false } = options;
  let nextTab = tabId;
  if (nextTab === 'admin' || nextTab === 'overview' || nextTab === 'session' || nextTab === 'distributor' || nextTab === 'reseller') {
    nextTab = 'home';
  }
  if (nextTab === 'owner') {
    nextTab = roleAllowsTab('licences') ? 'licences' : 'home';
  }
  if (!['home', 'people', 'person', 'licences', 'licence', 'me'].includes(nextTab)) {
    nextTab = preferredTabForRole(userRole());
  }
  if (['home', 'people', 'licences', 'me'].includes(nextTab) && !roleAllowsTab(nextTab)) {
    nextTab = preferredTabForRole(userRole());
  }

  activeTab = nextTab;
  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `view-${nextTab}`);
  });
  document.querySelectorAll('#bottomTabs .tab-button').forEach((button) => {
    const tab = button.dataset.tab;
    const isDetailParent = (nextTab === 'person' && tab === 'people') || (nextTab === 'licence' && tab === 'licences');
    button.classList.toggle('active', tab === nextTab || isDetailParent);
  });
  persistTabState(nextTab);
  setOverflowOpen(false);
  if (!skipLoad) {
    loadTabData(nextTab).catch((error) => setStatus(error.message, true));
  }
}

function preferredTabForRole(roleName) {
  if (roleName === 'owner') return 'home';
  if (roleName === 'support') return 'home';
  if (roleName === 'distributor' || roleName === 'reseller') return 'home';
  return 'home';
}

function setOverflowOpen(isOpen) {
  const shell = element('authenticatedShell');
  const toggle = element('overflowMenuToggle');
  if (!(shell instanceof HTMLElement)) return;
  shell.classList.toggle('nav-open', isOpen);
  if (toggle) toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

function setSheetOpen(sheetId, isOpen) {
  const sheet = element(sheetId);
  if (!(sheet instanceof HTMLElement)) return;
  sheet.classList.toggle('hidden', !isOpen);
  sheet.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
}

function setChangePasswordModalOpen(isOpen) {
  const modal = element('changePasswordModal');
  if (!(modal instanceof HTMLElement)) return;
  if (isOpen) {
    changePasswordReturnFocus = document.activeElement;
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    element('change_password_current')?.focus();
  } else {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    element('changePasswordForm')?.reset();
    if (changePasswordReturnFocus instanceof HTMLElement) {
      changePasswordReturnFocus.focus();
    }
  }
}

function setEntityPickerOpen(isOpen) {
  const modal = element('entityPickerModal');
  if (!(modal instanceof HTMLElement)) return;
  if (isOpen) {
    entityPickerReturnFocus = document.activeElement;
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    element('entityPickerSearchInput')?.focus();
  } else {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    if (entityPickerReturnFocus instanceof HTMLElement) {
      entityPickerReturnFocus.focus();
    }
  }
}

function renderEmpty(containerId, message) {
  const node = element(containerId);
  if (!(node instanceof HTMLElement)) return;
  node.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function renderListRows(containerId, rows, emptyMessage) {
  const node = element(containerId);
  if (!(node instanceof HTMLElement)) return;
  if (!rows.length) {
    renderEmpty(containerId, emptyMessage);
    return;
  }
  node.innerHTML = rows.join('');
}

/* ---------------- data loading ---------------- */

async function loadUsersForRole() {
  const role = userRole();
  if (role === 'platform_admin') {
    usersCache = await api('/api/v1/admin/users', { headers: authHeaders() });
    return usersCache;
  }
  if (role === 'distributor') {
    const [resellers, owners] = await Promise.all([
      api('/api/v1/distributor/resellers', { headers: authHeaders() }),
      api('/api/v1/distributor/owners', { headers: authHeaders() }),
    ]);
    usersCache = [...resellers, ...owners];
    return usersCache;
  }
  if (role === 'reseller') {
    const summary = await api('/api/v1/dashboard/reseller/summary', { headers: authHeaders() });
    usersCache = (summary.owners || []).map((owner) => ({
      user_uuid: owner.user_uuid,
      email: owner.email,
      display_name: owner.display_name,
      role_name: owner.role_name || 'owner',
      status: owner.status,
      reseller_uuid: currentUser?.reseller_uuid || null,
      distributor_uuid: currentUser?.distributor_uuid || null,
      installation_count: owner.installation_count,
    }));
    return usersCache;
  }
  if (role === 'support') {
    try {
      usersCache = await api('/api/v1/admin/users', { headers: authHeaders() });
    } catch {
      usersCache = [];
    }
    usersCache = usersCache.filter((user) => user.role_name === 'owner');
    return usersCache;
  }
  usersCache = [];
  return usersCache;
}

async function loadLicencesForRole() {
  const role = userRole();
  if (role === 'platform_admin') {
    licencesCache = await api('/api/v1/admin/installations', { headers: authHeaders() });
    return licencesCache;
  }
  if (role === 'distributor') {
    const summary = await api('/api/v1/dashboard/distributor/summary', { headers: authHeaders() });
    licencesCache = summary.installations || [];
    return licencesCache;
  }
  if (role === 'reseller') {
    const summary = await api('/api/v1/dashboard/reseller/summary', { headers: authHeaders() });
    licencesCache = summary.installations || [];
    return licencesCache;
  }
  if (role === 'owner' || role === 'support') {
    licencesCache = await api('/api/v1/dashboard/owner/installations', { headers: authHeaders() });
    return licencesCache;
  }
  licencesCache = [];
  return licencesCache;
}

async function loadHome() {
  const role = userRole();
  const pulse = element('homePulse');
  const recent = element('homeRecent');
  const cta = element('homePrimaryCta');
  const sub = element('homeSub');
  if (sub) sub.textContent = `${currentUser?.email || ''} · ${role || ''}`;

  let metrics = [];
  let recentRows = [];
  let ctaLabel = 'Continue';
  let ctaAction = () => activateTab('me');

  if (role === 'platform_admin') {
    const summary = await api('/api/v1/dashboard/admin/summary', { headers: authHeaders() });
    metrics = [
      { label: 'Pending invites', value: summary.pending_invitation_count },
      { label: 'Active licences', value: summary.active_entitlement_count },
      { label: 'Suspended users', value: summary.suspended_user_count },
      { label: 'Pending activation', value: summary.pending_activation_count },
    ];
    recentRows = (summary.recent_invitations || []).slice(0, 5).map((item) => (
      `<div class="activity-item"><div class="activity-title">${escapeHtml(item.email)}</div><div class="activity-meta">${statusBadgeMarkup(item.effective_status || item.status)} <span>${escapeHtml(item.role_name)}</span></div></div>`
    ));
    ctaLabel = 'Invite person';
    ctaAction = () => {
      activateTab('people');
      setSheetOpen('inviteSheet', true);
    };
  } else if (role === 'distributor') {
    const summary = await api('/api/v1/dashboard/distributor/summary', { headers: authHeaders() });
    metrics = [
      { label: 'Resellers', value: summary.reseller_count },
      { label: 'Owners', value: summary.owner_count },
      { label: 'Licences', value: summary.installation_count },
      { label: 'Pending invites', value: summary.pending_invitation_count },
    ];
    recentRows = (summary.recent_assignments || []).slice(0, 5).map((item) => (
      `<div class="activity-item"><div class="activity-title">${escapeHtml(item.owner_email)}</div><div class="activity-meta">${statusBadgeMarkup(item.activation_status)} <span>${escapeHtml(item.tenant_name || item.application_key)}</span></div></div>`
    ));
    ctaLabel = 'Invite or assign';
    ctaAction = () => {
      activateTab('people');
      setSheetOpen('inviteSheet', true);
    };
  } else if (role === 'reseller') {
    const summary = await api('/api/v1/dashboard/reseller/summary', { headers: authHeaders() });
    metrics = [
      { label: 'Owners', value: summary.owner_count },
      { label: 'Licences', value: summary.installation_count },
      { label: 'Active', value: summary.active_installation_count },
      { label: 'Pending invites', value: summary.pending_invitation_count },
    ];
    recentRows = (summary.owners || []).slice(0, 5).map((item) => (
      `<div class="activity-item"><div class="activity-title">${escapeHtml(item.email)}</div><div class="activity-meta">${statusBadgeMarkup(item.status)} <span>${escapeHtml(String(item.installation_count || 0))} licences</span></div></div>`
    ));
    ctaLabel = 'Invite owner';
    ctaAction = () => {
      activateTab('people');
      setSheetOpen('inviteSheet', true);
    };
  } else if (role === 'owner') {
    const summary = await api('/api/v1/dashboard/owner/summary', { headers: authHeaders() });
    metrics = [
      { label: 'Installations', value: summary.installation_count },
      { label: 'Active', value: summary.active_installation_count },
      { label: 'Grace', value: summary.grace_installation_count },
      { label: 'Suspended', value: summary.suspended_installation_count },
    ];
    recentRows = (summary.recent_updates || []).slice(0, 5).map((item) => (
      `<div class="activity-item"><div class="activity-title">${escapeHtml(item.event_type || item.update_channel || 'Update')}</div><div class="activity-meta"><span>${escapeHtml(item.created_at || '')}</span></div></div>`
    ));
    ctaLabel = 'My installations';
    ctaAction = () => activateTab('licences');
  } else if (role === 'support') {
    metrics = [
      { label: 'Role', value: 'support' },
      { label: 'Focus', value: 'owners' },
    ];
    recentRows = [];
    ctaLabel = 'Find owner';
    ctaAction = () => activateTab('people');
  }

  if (pulse) {
    pulse.innerHTML = metrics.map((item) => (
      `<div class="pulse-card"><div class="pulse-value">${escapeHtml(String(item.value ?? 0))}</div><div class="pulse-label">${escapeHtml(item.label)}</div></div>`
    )).join('');
  }
  renderListRows('homeRecent', recentRows, 'No recent activity.');
  if (cta) {
    cta.textContent = ctaLabel;
    cta.onclick = ctaAction;
  }
}

function filteredPeople() {
  const query = peopleSearchQuery.trim().toLowerCase();
  return usersCache.filter((user) => {
    if (peopleStatusFilter && String(user.status || '').toLowerCase() !== peopleStatusFilter) {
      return false;
    }
    if (!query) return true;
    const hay = [user.email, user.display_name, user.role_name, user.user_uuid, user.status]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(query);
  });
}

function renderPeopleList() {
  const rows = filteredPeople().map((user) => `
    <button type="button" class="list-row" data-open-person="${escapeHtml(user.user_uuid)}">
      <div class="list-row-title">${escapeHtml(user.display_name || user.email)}</div>
      <div class="list-row-meta">
        ${statusBadgeMarkup(user.status)}
        <span class="pill">${escapeHtml(user.role_name)}</span>
        <span>${escapeHtml(user.email)}</span>
      </div>
    </button>
  `);
  renderListRows('peopleList', rows, 'No people in scope.');
  element('peopleList')?.querySelectorAll('[data-open-person]').forEach((button) => {
    button.addEventListener('click', () => openPerson(button.dataset.openPerson));
  });
}

async function loadPeople() {
  await loadUsersForRole();
  renderPeopleList();
}

function openPerson(userUuid) {
  selectedPersonUuid = userUuid;
  activateTab('person');
}

function findUser(userUuid) {
  return usersCache.find((user) => user.user_uuid === userUuid) || null;
}

function findLicence(entitlementUuid) {
  return licencesCache.find((item) => item.entitlement_uuid === entitlementUuid) || null;
}

function userStatusPath(user) {
  const role = userRole();
  if (role === 'platform_admin') {
    return `/api/v1/admin/users/${encodeURIComponent(user.user_uuid)}/status`;
  }
  if (role === 'distributor' && user.role_name === 'reseller') {
    return `/api/v1/distributor/users/${encodeURIComponent(user.user_uuid)}/status`;
  }
  if (role === 'reseller' && user.role_name === 'owner') {
    return `/api/v1/reseller/users/${encodeURIComponent(user.user_uuid)}/status`;
  }
  return null;
}

async function renderPerson() {
  const user = findUser(selectedPersonUuid);
  if (!user) {
    await loadUsersForRole();
  }
  const record = findUser(selectedPersonUuid);
  if (!record) {
    setStatus('Person not found in scope.', true);
    activateTab('people');
    return;
  }

  element('personTitle').textContent = record.display_name || record.email;
  element('personSub').textContent = record.email;
  element('personMeta').innerHTML = `
    <div><span class="muted">Role</span><div>${escapeHtml(record.role_name)} ${statusBadgeMarkup(record.status)}</div></div>
    <div><span class="muted">User UUID</span><div><code class="inline">${escapeHtml(record.user_uuid)}</code></div></div>
    <div><span class="muted">Distributor</span><div><code class="inline">${escapeHtml(record.distributor_uuid || '—')}</code></div></div>
    <div><span class="muted">Reseller</span><div><code class="inline">${escapeHtml(record.reseller_uuid || '—')}</code></div></div>
  `;

  const actions = [];
  const statusPath = userStatusPath(record);
  if (statusPath && (record.status === 'active' || record.status === 'suspended')) {
    const nextStatus = record.status === 'active' ? 'suspended' : 'active';
    const label = nextStatus === 'suspended' ? 'Suspend' : 'Activate';
    actions.push(`<button type="button" class="secondary mini-button" data-person-status="${nextStatus}">${label}</button>`);
  }
  if ((userRole() === 'support' || userRole() === 'platform_admin') && record.status === 'suspended' && record.role_name === 'owner') {
    actions.push('<button type="button" class="mini-button" data-person-reinstate="1">Emergency reinstate</button>');
  }
  if (userRole() === 'platform_admin') {
    actions.push('<button type="button" class="secondary mini-button" data-person-reassign="1">Reassign scope</button>');
  }
  element('personActions').innerHTML = actions.join('');

  const reassignCard = element('personReassignCard');
  reassignCard?.classList.add('hidden');
  element('reassign_distributor_uuid').value = record.distributor_uuid || '';
  element('reassign_reseller_uuid').value = record.reseller_uuid || '';

  element('personActions').querySelector('[data-person-status]')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    try {
      await api(statusPath, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify({
          status: button.dataset.personStatus,
          reason_code: 'ui_quick_action',
          operator_note: null,
        }),
      });
      setStatus(`Updated ${record.email}.`);
      await loadPeople();
      await renderPerson();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  element('personActions').querySelector('[data-person-reinstate]')?.addEventListener('click', async () => {
    try {
      await api(`/api/v1/support/users/${encodeURIComponent(record.user_uuid)}/reinstate`, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify({ reason_code: 'ui_emergency_reinstate', operator_note: null }),
      });
      setStatus(`Reinstated ${record.email}.`, false);
      showToast(`Emergency reinstated ${record.email}.`, 'success');
      await loadPeople();
      await renderPerson();
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  element('personActions').querySelector('[data-person-reassign]')?.addEventListener('click', () => {
    reassignCard?.classList.remove('hidden');
  });

  if (!licencesCache.length && roleAllowsTab('licences')) {
    try { await loadLicencesForRole(); } catch { /* ignore */ }
  }
  const linked = licencesCache.filter((item) =>
    String(item.approved_owner_email || '').toLowerCase() === String(record.email || '').toLowerCase()
  );
  const licenceRows = linked.map((item) => `
    <button type="button" class="list-row" data-open-licence="${escapeHtml(item.entitlement_uuid)}">
      <div class="list-row-title">${escapeHtml(item.tenant_name || item.licence_name || item.application_key)}</div>
      <div class="list-row-meta">${statusBadgeMarkup(item.activation_status || item.licence_status)}</div>
    </button>
  `);
  renderListRows('personLicences', licenceRows, 'No linked licences.');
  element('personLicences')?.querySelectorAll('[data-open-licence]').forEach((button) => {
    button.addEventListener('click', () => openLicence(button.dataset.openLicence));
  });
}

function filteredLicences() {
  const query = licenceSearchQuery.trim().toLowerCase();
  return licencesCache.filter((item) => {
    const status = item.activation_status || item.licence_status || '';
    if (licenceStatusFilter && status !== licenceStatusFilter) return false;
    if (!query) return true;
    const hay = [item.tenant_name, item.licence_name, item.application_key, item.approved_owner_email, item.entitlement_uuid, item.installation_uuid]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(query);
  });
}

function renderLicencesList() {
  const role = userRole();
  const readOnly = role === 'owner';
  if (element('licencesSub')) {
    element('licencesSub').textContent = readOnly ? 'Your installations' : 'Issue, assign, and review';
  }
  const rows = filteredLicences().map((item) => `
    <button type="button" class="list-row" data-open-licence="${escapeHtml(item.entitlement_uuid)}">
      <div class="list-row-title">${escapeHtml(item.tenant_name || item.licence_name || item.application_key || 'Licence')}</div>
      <div class="list-row-meta">
        ${statusBadgeMarkup(item.activation_status || item.licence_status)}
        <span>${escapeHtml(item.approved_owner_email || '')}</span>
      </div>
    </button>
  `);
  renderListRows('licencesList', rows, readOnly ? 'No installations yet.' : 'No licences in scope.');
  element('licencesList')?.querySelectorAll('[data-open-licence]').forEach((button) => {
    button.addEventListener('click', () => openLicence(button.dataset.openLicence));
  });
}

async function loadLicences() {
  await loadLicencesForRole();
  renderLicencesList();
}

function openLicence(entitlementUuid) {
  selectedLicenceUuid = entitlementUuid;
  activateTab('licence');
}

async function renderLicence() {
  if (!licencesCache.length) {
    await loadLicencesForRole();
  }
  const record = findLicence(selectedLicenceUuid);
  if (!record) {
    setStatus('Licence not found.', true);
    activateTab('licences');
    return;
  }

  element('licenceTitle').textContent = record.tenant_name || record.licence_name || record.application_key || 'Licence';
  element('licenceSub').textContent = record.approved_owner_email || '';
  element('licenceMeta').innerHTML = `
    <div><span class="muted">Status</span><div>${statusBadgeMarkup(record.activation_status || record.licence_status)}</div></div>
    <div><span class="muted">Entitlement</span><div><code class="inline">${escapeHtml(record.entitlement_uuid)}</code></div></div>
    <div><span class="muted">Installation</span><div><code class="inline">${escapeHtml(record.installation_uuid || '—')}</code></div></div>
    <div><span class="muted">Application key</span><div><code class="inline">${escapeHtml(record.application_key || '—')}</code></div></div>
    <div><span class="muted">Matrix</span><div><code class="inline">${escapeHtml(record.matrix_group_id || '—')}</code></div></div>
  `;

  const canManage = userRole() === 'platform_admin';
  const actions = [];
  if (canManage) {
    const status = record.activation_status;
    if (status === 'active') {
      actions.push('<button type="button" class="secondary mini-button" data-licence-status="suspended">Suspend</button>');
    } else if (status === 'suspended' || status === 'pending_activation') {
      actions.push('<button type="button" class="mini-button" data-licence-status="active">Activate</button>');
    }
  }
  element('licenceActions').innerHTML = actions.join('');
  element('licenceEditCard')?.classList.toggle('hidden', !canManage);

  if (canManage) {
    element('edit_entitlement_uuid').value = record.entitlement_uuid;
    element('edit_approved_owner_email').value = record.approved_owner_email || '';
    element('edit_licence_status').value = record.licence_status || 'active';
    element('edit_owner_enabled').value = record.owner_enabled ? 'true' : 'false';
    element('edit_warning_period_days').value = String(record.warning_period_days ?? 0);
    element('edit_offline_grace_days').value = String(record.offline_grace_days ?? 0);
    element('edit_tenant_name').value = record.tenant_name || record.licence_name || '';
    element('edit_notes').value = record.notes || '';
  }

  element('licenceActions').querySelector('[data-licence-status]')?.addEventListener('click', async (event) => {
    try {
      await api(`/api/v1/admin/installations/${encodeURIComponent(record.entitlement_uuid)}/activation-status`, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify({
          activation_status: event.currentTarget.dataset.licenceStatus,
          reason_code: 'ui_licence_action',
          operator_note: null,
        }),
      });
      setStatus('Licence status updated.');
      await loadLicences();
      await renderLicence();
    } catch (error) {
      setStatus(error.message, true);
    }
  });
}

async function loadMe() {
  /* account fields already synced via setSession */
}

async function loadTabData(tabId) {
  if (tabId === 'home') return loadHome();
  if (tabId === 'people') return loadPeople();
  if (tabId === 'person') return renderPerson();
  if (tabId === 'licences') return loadLicences();
  if (tabId === 'licence') return renderLicence();
  if (tabId === 'me') return loadMe();
}

/* ---------------- auth ---------------- */

async function loadSession() {
  if (!sessionToken) {
    sessionToken = persistedSessionToken();
  }
  if (!sessionToken) {
    setSession(null, '');
    return null;
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
        email: element('login_email').value.trim(),
        password: element('login_password').value,
      }),
    });
    setSession(payload.user, payload.session_token);
    const landing = requestedTab && roleAllowsTab(requestedTab === 'owner' ? 'licences' : requestedTab)
      ? (requestedTab === 'owner' ? 'licences' : requestedTab)
      : preferredTabForRole(payload.user.role_name);
    activateTab(landing);
    if (requestedEditEntitlementUuid && payload.user.role_name === 'platform_admin') {
      selectedLicenceUuid = requestedEditEntitlementUuid;
      activateTab('licence');
    }
    setStatus(`Signed in as ${payload.user.email}`);
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
        invitation_token: element('accept_invitation_token').value.trim(),
        display_name: element('accept_display_name').value.trim() || null,
        password: element('accept_password').value,
      }),
    });
    showToast(`Invitation accepted for ${payload.email}.`, 'success');
    window.location.href = `/admin?login_email=${encodeURIComponent(payload.email)}`;
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function handleLogout() {
  try {
    if (sessionToken) {
      await api('/api/v1/auth/logout', { method: 'POST', headers: authHeaders() });
    }
  } catch {
    /* still clear local session */
  }
  sessionToken = '';
  currentUser = null;
  setSession(null, '');
  window.location.href = '/admin';
}

async function handleChangePassword() {
  const currentPassword = element('change_password_current')?.value || '';
  const newPassword = element('change_password_new')?.value || '';
  const confirmPassword = element('change_password_confirm')?.value || '';
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

async function handleBootstrap() {
  try {
    const user = await api('/api/v1/auth/bootstrap-admin', { method: 'POST' });
    element('login_email').value = user.email || 'admin@authority.local';
    setStatus('Bootstrap admin ready. Sign in with the bootstrap password.');
  } catch (error) {
    setStatus(error.message, true);
  }
}

/* ---------------- invite / licence wizard ---------------- */

function invitationDeliveryMessage(invitation, fallback) {
  if (invitation.email_delivered) {
    return fallback;
  }
  if (invitation.email_delivery_message) {
    return `${fallback} Email not delivered: ${invitation.email_delivery_message}`;
  }
  return `${fallback} Email delivery was not confirmed.`;
}

async function submitInvite(event) {
  event.preventDefault();
  const role = userRole();
  const inviteRole = element('invite_role_name').value;
  const email = element('invite_email').value.trim();
  const expires = Number(element('invite_expires_in_days').value || 7);
  const distributorUuid = element('invite_distributor_uuid').value.trim() || null;
  const resellerUuid = element('invite_reseller_uuid').value.trim() || null;

  try {
    let invitation;
    if (role === 'platform_admin') {
      if (inviteRole === 'distributor' && !distributorUuid) {
        setStatus('Distributor invitations require a distributor UUID.', true);
        return;
      }
      if (inviteRole === 'owner' && !distributorUuid && !resellerUuid) {
        setStatus('Owner invites need a distributor or reseller scope.', true);
        return;
      }
      invitation = await api('/api/v1/admin/invitations', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          email,
          role_name: inviteRole,
          distributor_uuid: distributorUuid,
          reseller_uuid: resellerUuid,
          expires_in_days: expires,
        }),
      });
    } else if (role === 'distributor') {
      invitation = await api('/api/v1/distributor/invitations', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          email,
          role_name: inviteRole,
          reseller_uuid: inviteRole === 'owner' ? resellerUuid : null,
          expires_in_days: expires,
        }),
      });
    } else if (role === 'reseller') {
      invitation = await api('/api/v1/reseller/invitations', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          email,
          role_name: 'owner',
          expires_in_days: expires,
        }),
      });
    } else {
      setStatus('Invites are not available for this role.', true);
      return;
    }

    setSheetOpen('inviteSheet', false);
    element('inviteForm')?.reset();
    syncInviteRoleOptions();
    setStatus(invitationDeliveryMessage(invitation, `Invite sent to ${invitation.email}.`), !invitation.email_delivered);
    await loadPeople();
    activateTab('people');
  } catch (error) {
    setStatus(error.message, true);
  }
}

function syncLicenceWizardMode() {
  const mode = element('licence_wizard_mode')?.value;
  element('licenceWizardIssueFields')?.classList.toggle('hidden', mode !== 'issue');
  element('licenceWizardAssignFields')?.classList.toggle('hidden', mode !== 'assign');
  updateLicenceWizardSummary();
}

function updateLicenceWizardSummary() {
  const summary = element('licenceWizardSummary');
  if (!summary) return;
  const email = element('licence_wizard_owner_email')?.value.trim() || '—';
  const mode = element('licence_wizard_mode')?.value;
  summary.textContent = mode === 'assign'
    ? `Assign existing entitlement to ${email}.`
    : `Issue a new licence for ${email}.`;
}

async function confirmLicenceWizard() {
  const role = userRole();
  const email = element('licence_wizard_owner_email').value.trim();
  const mode = element('licence_wizard_mode').value;
  if (!email) {
    setStatus('Owner email is required.', true);
    return;
  }

  try {
    if (mode === 'issue') {
      if (role !== 'platform_admin') {
        setStatus('Only platform admin can issue new licences. Use Assign for channel roles.', true);
        return;
      }
      const record = await api('/api/v1/admin/installations', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          application_key: element('licence_wizard_application_key').value.trim() || null,
          approved_owner_email: email,
          owner_enabled: true,
          licence_status: 'active',
          warning_period_days: Number(element('licence_wizard_warning_days').value || 0),
          offline_grace_days: Number(element('licence_wizard_grace_days').value || 0),
          tenant_name: element('licence_wizard_tenant_name').value.trim() || null,
          licence_name: element('licence_wizard_tenant_name').value.trim() || null,
          installation_name: element('licence_wizard_installation_name').value.trim() || null,
          notes: element('licence_wizard_notes').value.trim() || null,
        }),
      });
      await api('/api/v1/admin/installation-assignments', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          entitlement_uuid: record.entitlement_uuid,
          user_email: email,
        }),
      }).catch(() => null);
      setStatus(`Issued licence ${record.entitlement_uuid}.`);
      selectedLicenceUuid = record.entitlement_uuid;
    } else {
      const entitlementUuid = element('licence_wizard_entitlement_uuid').value.trim();
      if (!entitlementUuid) {
        setStatus('Entitlement UUID is required to assign.', true);
        return;
      }
      let path = '/api/v1/admin/installation-assignments';
      if (role === 'distributor') path = '/api/v1/distributor/installation-assignments';
      if (role === 'reseller') path = '/api/v1/reseller/installation-assignments';
      await api(path, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          entitlement_uuid: entitlementUuid,
          user_email: email,
        }),
      });
      setStatus(`Assigned entitlement ${entitlementUuid}.`);
      selectedLicenceUuid = entitlementUuid;
    }
    setSheetOpen('licenceWizard', false);
    await loadLicences();
    activateTab('licence');
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function updateEntitlementDetails() {
  try {
    const entitlementUuid = element('edit_entitlement_uuid').value.trim();
    const currentRecord = await api(`/api/v1/admin/installations/${encodeURIComponent(entitlementUuid)}`, {
      headers: authHeaders(),
    });
    const record = await api('/api/v1/admin/installations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        entitlement_uuid: entitlementUuid,
        application_key: currentRecord.application_key,
        installation_uuid: currentRecord.installation_uuid,
        approved_owner_email: element('edit_approved_owner_email').value.trim(),
        owner_enabled: element('edit_owner_enabled').value === 'true',
        licence_status: element('edit_licence_status').value,
        warning_period_days: Number(element('edit_warning_period_days').value || 0),
        offline_grace_days: Number(element('edit_offline_grace_days').value || 0),
        tenant_name: element('edit_tenant_name').value.trim() || null,
        licence_name: element('edit_tenant_name').value.trim() || null,
        notes: element('edit_notes').value.trim() || null,
      }),
    });
    setStatus(`Updated licence details for ${record.entitlement_uuid}.`);
    await loadLicences();
    await renderLicence();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function reassignUserScope() {
  try {
    const user = await api(`/api/v1/admin/users/${encodeURIComponent(selectedPersonUuid)}/scope`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({
        distributor_uuid: element('reassign_distributor_uuid').value.trim() || null,
        reseller_uuid: element('reassign_reseller_uuid').value.trim() || null,
        reason_code: element('reassign_reason_code').value.trim() || 'ui_reassign',
        operator_note: null,
      }),
    });
    setStatus(`Reassigned ${user.email}.`);
    await loadPeople();
    await renderPerson();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function supportReinstateUser() {
  try {
    const userUuid = element('support_user_uuid').value.trim();
    const user = await api(`/api/v1/support/users/${encodeURIComponent(userUuid)}/reinstate`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify({
        reason_code: element('support_reason_code').value.trim() || 'ui_emergency_reinstate',
        operator_note: element('support_operator_note').value.trim() || null,
      }),
    });
    setStatus(`Emergency reinstated ${user.email}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function vpnEnroll() {
  try {
    const entitlementUuid = element('vpn_entitlement_uuid').value.trim();
    const payload = await api('/api/v1/vpn/enroll-installation', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ entitlement_uuid: entitlementUuid }),
    });
    element('vpnResult').innerHTML = `<div class="activity-item"><div class="activity-title">Enrolled</div><div class="activity-meta"><code class="inline">${escapeHtml(JSON.stringify(payload))}</code></div></div>`;
    setStatus('VPN enrollment requested.');
  } catch (error) {
    setStatus(error.message, true);
  }
}

function currentAuditFiltersFromInputs() {
  return {
    target_entity_type: element('audit_target_entity_type')?.value.trim() || '',
    target_entity_uuid: element('audit_target_entity_uuid')?.value.trim() || '',
    action: element('audit_action')?.value.trim() || '',
    actor_role_name: element('audit_actor_role_name')?.value.trim() || '',
    limit: element('audit_limit')?.value.trim() || '50',
  };
}

function renderAuditEvents() {
  const rows = auditState.items.map((item) => `
    <div class="activity-item">
      <div class="activity-title">${escapeHtml(item.action)} · ${escapeHtml(item.target_entity_type)}</div>
      <div class="activity-meta">
        <span>${escapeHtml(item.target_email || item.target_entity_uuid)}</span>
        <span>${escapeHtml(item.actor_email || item.actor_role_name || 'system')}</span>
        <span>${escapeHtml(item.created_at || '')}</span>
      </div>
    </div>
  `);
  renderListRows('adminAuditEvents', rows, 'No audit events loaded yet.');
  const more = element('loadMoreAuditEventsButton');
  if (more instanceof HTMLButtonElement) {
    more.disabled = !auditState.hasMore;
  }
}

async function loadAuditEvents() {
  const filters = currentAuditFiltersFromInputs();
  const query = new URLSearchParams();
  query.set('offset', '0');
  Object.entries(filters).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const payload = await api(`/api/v1/admin/audit-events?${query.toString()}`, { headers: authHeaders() });
  auditState = {
    items: payload.items || [],
    nextOffset: payload.next_offset,
    hasMore: payload.has_more,
    filters,
  };
  renderAuditEvents();
  setStatus(`Loaded ${auditState.items.length} audit events.`);
}

async function loadMoreAuditEvents() {
  if (auditState.nextOffset === null) return;
  const filters = auditState.filters;
  const query = new URLSearchParams();
  query.set('offset', String(auditState.nextOffset));
  Object.entries(filters).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const payload = await api(`/api/v1/admin/audit-events?${query.toString()}`, { headers: authHeaders() });
  auditState = {
    ...auditState,
    items: [...auditState.items, ...(payload.items || [])],
    nextOffset: payload.next_offset,
    hasMore: payload.has_more,
  };
  renderAuditEvents();
}

/* ---------------- entity picker ---------------- */

function matchingUsers(query) {
  const q = query.trim().toLowerCase();
  return usersCache.filter((user) => {
    if (!q) return true;
    return [user.email, user.display_name, user.role_name, user.user_uuid, user.distributor_uuid, user.reseller_uuid]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(q);
  }).slice(0, 20);
}

function matchingEntitlements(query) {
  const q = query.trim().toLowerCase();
  return licencesCache.filter((item) => {
    if (!q) return true;
    return [item.entitlement_uuid, item.application_key, item.approved_owner_email, item.tenant_name, item.licence_name]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(q);
  }).slice(0, 20);
}

function matchingScopedUuid(kind, query) {
  const q = query.trim().toLowerCase();
  const values = new Map();
  usersCache.forEach((user) => {
    const uuid = kind === 'distributor' ? user.distributor_uuid : user.reseller_uuid;
    if (!uuid) return;
    if (q && !`${uuid} ${user.email}`.toLowerCase().includes(q)) return;
    if (!values.has(uuid)) {
      values.set(uuid, user);
    }
  });
  return Array.from(values.entries()).slice(0, 20).map(([uuid, user]) => ({ uuid, user }));
}

function openEntityPickerForInput(input) {
  const kind = input.dataset.uuidPickerKind;
  if (!kind) return;
  entityPickerState = { targetInputId: input.id, kind };
  const title = element('entityPickerTitle');
  const hint = element('entityPickerHint');
  if (title) title.textContent = `Search ${kind}`;
  if (hint) hint.textContent = 'Tap a result to fill the field.';
  element('entityPickerSearchInput').value = '';
  setEntityPickerOpen(true);
  renderEntityPickerResults();
}

function renderEntityPickerResults() {
  const query = element('entityPickerSearchInput')?.value || '';
  const kind = entityPickerState.kind;
  let rows = [];
  if (kind === 'user') {
    rows = matchingUsers(query).map((user) => `
      <button type="button" class="list-row" data-picker-value="${escapeHtml(user.user_uuid)}">
        <div class="list-row-title">${escapeHtml(user.email)}</div>
        <div class="list-row-meta">${statusBadgeMarkup(user.status)} <span class="pill">${escapeHtml(user.role_name)}</span></div>
      </button>
    `);
  } else if (kind === 'entitlement') {
    rows = matchingEntitlements(query).map((item) => `
      <button type="button" class="list-row" data-picker-value="${escapeHtml(item.entitlement_uuid)}">
        <div class="list-row-title">${escapeHtml(item.tenant_name || item.application_key || item.entitlement_uuid)}</div>
        <div class="list-row-meta">${statusBadgeMarkup(item.activation_status || item.licence_status)} <span>${escapeHtml(item.approved_owner_email || '')}</span></div>
      </button>
    `);
  } else if (kind === 'distributor' || kind === 'reseller') {
    rows = matchingScopedUuid(kind, query).map(({ uuid, user }) => `
      <button type="button" class="list-row" data-picker-value="${escapeHtml(uuid)}">
        <div class="list-row-title"><code class="inline">${escapeHtml(uuid)}</code></div>
        <div class="list-row-meta"><span>${escapeHtml(user.email)}</span></div>
      </button>
    `);
  }
  renderListRows('entityPickerResults', rows, 'No matches.');
  element('entityPickerResults')?.querySelectorAll('[data-picker-value]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = element(entityPickerState.targetInputId);
      if (input instanceof HTMLInputElement) {
        input.value = button.dataset.pickerValue || '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
      setEntityPickerOpen(false);
    });
  });
}

function bindUuidPickerInputs() {
  document.querySelectorAll('[data-uuid-picker-kind]').forEach((input) => {
    if (!(input instanceof HTMLInputElement)) return;
    input.addEventListener('focus', () => {
      if (!usersCache.length && roleAllowsTab('people')) {
        loadUsersForRole().catch(() => {});
      }
      if (!licencesCache.length && (userRole() === 'platform_admin' || roleAllowsTab('licences'))) {
        loadLicencesForRole().catch(() => {});
      }
      openEntityPickerForInput(input);
    });
  });
}

/* ---------------- events ---------------- */

function bindClick(id, handler) {
  const node = element(id);
  if (node) node.addEventListener('click', handler);
}

function wireUi() {
  element('loginForm')?.addEventListener('submit', (event) => {
    event.preventDefault();
    handleLogin();
  });
  element('acceptInvitationForm')?.addEventListener('submit', (event) => {
    event.preventDefault();
    handleAcceptInvitation();
  });
  element('changePasswordForm')?.addEventListener('submit', (event) => {
    event.preventDefault();
    handleChangePassword();
  });
  element('inviteForm')?.addEventListener('submit', submitInvite);

  bindClick('bootstrapButton', () => handleBootstrap());
  bindClick('backToLoginButton', () => {
    window.location.href = '/admin';
  });
  bindClick('logoutButton', () => handleLogout());
  bindClick('meLogoutButton', () => handleLogout());
  bindClick('openChangePasswordButton', () => setChangePasswordModalOpen(true));
  bindClick('meChangePasswordButton', () => setChangePasswordModalOpen(true));
  bindClick('closeChangePasswordButton', () => setChangePasswordModalOpen(false));
  bindClick('loadSessionButton', () => {
    loadSession()
      .then(() => setStatus('Session refreshed.'))
      .catch((error) => setStatus(error.message, true));
  });
  bindClick('meRefreshButton', () => {
    loadSession()
      .then(() => setStatus('Session refreshed.'))
      .catch((error) => setStatus(error.message, true));
  });

  bindClick('overflowMenuToggle', () => {
    const shell = element('authenticatedShell');
    setOverflowOpen(!(shell && shell.classList.contains('nav-open')));
  });
  bindClick('overflowMenuClose', () => setOverflowOpen(false));
  bindClick('overflowDrawerOverlay', () => setOverflowOpen(false));

  document.querySelectorAll('#bottomTabs .tab-button').forEach((button) => {
    button.addEventListener('click', () => activateTab(button.dataset.tab));
  });

  bindClick('openInviteSheetButton', () => {
    syncInviteRoleOptions();
    setSheetOpen('inviteSheet', true);
  });
  bindClick('closeInviteSheetButton', () => setSheetOpen('inviteSheet', false));
  bindClick('openLicenceWizardButton', () => {
    syncLicenceWizardMode();
    setSheetOpen('licenceWizard', true);
  });
  bindClick('closeLicenceWizardButton', () => setSheetOpen('licenceWizard', false));
  bindClick('licenceWizardConfirmButton', () => confirmLicenceWizard());
  element('licence_wizard_mode')?.addEventListener('change', syncLicenceWizardMode);
  element('licence_wizard_owner_email')?.addEventListener('input', updateLicenceWizardSummary);

  bindClick('personBackButton', () => activateTab('people'));
  bindClick('licenceBackButton', () => activateTab('licences'));
  bindClick('reassignUserScopeButton', () => reassignUserScope());
  bindClick('updateEntitlementDetailsButton', () => updateEntitlementDetails());
  bindClick('supportReinstateUserButton', () => supportReinstateUser());
  bindClick('vpnEnrollButton', () => vpnEnroll());
  bindClick('loadAuditEventsButton', () => loadAuditEvents().catch((error) => setStatus(error.message, true)));
  bindClick('loadMoreAuditEventsButton', () => loadMoreAuditEvents().catch((error) => setStatus(error.message, true)));

  element('peopleSearch')?.addEventListener('input', (event) => {
    peopleSearchQuery = event.target.value;
    renderPeopleList();
  });
  element('licencesSearch')?.addEventListener('input', (event) => {
    licenceSearchQuery = event.target.value;
    renderLicencesList();
  });

  element('peopleStatusFilter')?.querySelectorAll('[data-people-status]').forEach((button) => {
    button.addEventListener('click', () => {
      peopleStatusFilter = button.dataset.peopleStatus || '';
      element('peopleStatusFilter').querySelectorAll('.segment').forEach((node) => node.classList.remove('active'));
      button.classList.add('active');
      renderPeopleList();
    });
  });
  element('licencesStatusFilter')?.querySelectorAll('[data-licence-status]').forEach((button) => {
    button.addEventListener('click', () => {
      licenceStatusFilter = button.dataset.licenceStatus || '';
      element('licencesStatusFilter').querySelectorAll('.segment').forEach((node) => node.classList.remove('active'));
      button.classList.add('active');
      renderLicencesList();
    });
  });

  element('invite_role_name')?.addEventListener('change', syncInviteScopeFields);
  element('show_login_password')?.addEventListener('change', (event) => {
    const input = element('login_password');
    if (input) input.type = event.target.checked ? 'text' : 'password';
  });
  element('show_accept_password')?.addEventListener('change', (event) => {
    const input = element('accept_password');
    if (input) input.type = event.target.checked ? 'text' : 'password';
  });

  bindClick('closeEntityPickerButton', () => setEntityPickerOpen(false));
  element('entityPickerSearchInput')?.addEventListener('input', renderEntityPickerResults);
  bindUuidPickerInputs();

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      setOverflowOpen(false);
      setSheetOpen('inviteSheet', false);
      setSheetOpen('licenceWizard', false);
      setChangePasswordModalOpen(false);
      setEntityPickerOpen(false);
    }
  });
}

async function boot() {
  wireUi();

  if (loginEmailHint && element('login_email')) {
    element('login_email').value = loginEmailHint;
  }
  if (requestedInvitationToken && element('accept_invitation_token')) {
    element('accept_invitation_token').value = requestedInvitationToken;
    element('loggedOutPanel')?.classList.add('hidden');
    element('acceptInvitationCard')?.classList.remove('hidden');
  }

  sessionToken = persistedSessionToken();
  if (!sessionToken) {
    setSession(null, '');
    return;
  }

  try {
    await loadSession();
    const personParam = searchParams.get('person');
    const licenceParam = searchParams.get('licence') || requestedEditEntitlementUuid;
    if (personParam) {
      selectedPersonUuid = personParam;
      activateTab('person');
    } else if (licenceParam) {
      selectedLicenceUuid = licenceParam;
      activateTab('licence');
    } else if (requestedTab) {
      activateTab(requestedTab);
    } else {
      activateTab(preferredTabForRole(userRole()));
    }
  } catch (error) {
    persistSessionToken('');
    sessionToken = '';
    setSession(null, '');
    setStatus(error.message, true);
  }
}

boot();
