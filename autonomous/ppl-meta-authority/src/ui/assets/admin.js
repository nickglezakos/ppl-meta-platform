const pageName = document.body.dataset.page || 'admin';
const SESSION_TOKEN_STORAGE_KEY = 'authority.sessionToken';
const statusEls = Array.from(document.querySelectorAll('[data-shared-status]'));
const acceptStatusEl = document.getElementById('acceptStatus');
const bodyEl = document.getElementById('dataBody');
const loggedOutPanelEl = document.getElementById('loggedOutPanel');
const authenticatedShellEl = document.getElementById('authenticatedShell');
let sessionToken = '';
let currentUser = null;
let activeConsoleFilter = 'all';
let consoleRowsByFilter = {
  entitlements: [],
  invitations: [],
  assignments: [],
  updates: [],
  health: [],
};
const roleTabMap = {
  admin: ['platform_admin'],
  reseller: ['reseller', 'platform_admin'],
  owner: ['owner', 'support', 'platform_admin', 'reseller'],
};

function element(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const target = element(id);
  if (target) {
    target.textContent = value;
  }
}

function setStatus(message, isError = false) {
  if (!statusEls.length) {
    return;
  }
  statusEls.forEach((statusEl) => {
    statusEl.textContent = message;
    statusEl.className = isError ? 'status error' : 'status ok';
  });
}

function setAcceptStatus(message, isError = false) {
  if (!acceptStatusEl) {
    return;
  }
  acceptStatusEl.textContent = message;
  acceptStatusEl.className = isError ? 'status error' : 'status ok';
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
    loggedOutPanelEl.classList.toggle('hidden', isAuthenticated);
  }
  if (authenticatedShellEl) {
    authenticatedShellEl.classList.toggle('hidden', !isAuthenticated);
  }
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
  setText('currentResellerScope', user && user.reseller_uuid ? user.reseller_uuid : '-');
  setText('metricRole', user ? user.role_name : '-');
  setText('metricScope', user && user.reseller_uuid ? user.reseller_uuid : '-');
  setMetricValue('metricPendingInvitations', 0);
  setMetricValue('metricRecentAssignments', 0);
  if (!user) {
    setMetricValue('metricOwnerCount', 0);
    setMetricValue('metricResellerCount', 0);
    renderSummaryCards('adminSummaryCards', []);
    renderSummaryCards('resellerSummaryCards', []);
    renderSummaryCards('ownerSummaryCards', []);
    renderActivityList('adminRecentInvitations', [], 'No invitation activity yet.');
    renderActivityList('adminRecentAssignments', [], 'No assignment activity yet.');
    renderActivityList('adminRecentHealth', [], 'No health activity yet.');
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

  document.querySelectorAll('.tab-button').forEach((button) => {
    const allowedRoles = roleTabMap[button.dataset.tab] || [];
    const shouldHide = allowedRoles.length ? !isRoleAllowed(allowedRoles) : false;
    button.classList.toggle('hidden', shouldHide);
    if (button.classList.contains('active') && shouldHide) {
      activateTab('overview');
    }
  });

  const bootstrapButton = document.getElementById('bootstrapButton');
  if (bootstrapButton) {
    bootstrapButton.classList.toggle('hidden', Boolean(currentUser));
  }
}

function activateTab(tabId) {
  if (!document.querySelectorAll('.tab-button').length) {
    return;
  }
  document.querySelectorAll('.tab-button').forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === tabId);
  });
}

function preferredTabForRole(roleName) {
  if (roleName === 'platform_admin') {
    return 'admin';
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
      <div class="activity-meta">${item.meta}</div>
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
}

function renderRows(rows) {
  if (!bodyEl) {
    return;
  }
  if (!rows.length) {
    bodyEl.innerHTML = '<tr><td colspan="6" class="small">No rows returned.</td></tr>';
    return;
  }

  bodyEl.innerHTML = rows.map((row) => `
    <tr>
      <td>${row.type}</td>
      <td>${row.primary}</td>
      <td>${row.scope}</td>
      <td>${row.owner}</td>
      <td>${row.keyInfo}</td>
      <td>${row.details}</td>
    </tr>
  `).join('');

  bindConsoleActions();
}

function allConsoleRows() {
  return [
    ...consoleRowsByFilter.entitlements,
    ...consoleRowsByFilter.invitations,
    ...consoleRowsByFilter.assignments,
    ...consoleRowsByFilter.updates,
    ...consoleRowsByFilter.health,
  ];
}

function rowsForActiveFilter() {
  if (activeConsoleFilter === 'all') {
    return allConsoleRows();
  }
  return consoleRowsByFilter[activeConsoleFilter] || [];
}

function renderConsoleFilter() {
  const counts = {
    all: allConsoleRows().length,
    entitlements: consoleRowsByFilter.entitlements.length,
    invitations: consoleRowsByFilter.invitations.length,
    assignments: consoleRowsByFilter.assignments.length,
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
  if (bodyEl) {
    renderRows(rowsForActiveFilter());
  }
}

function setConsoleRows(filterName, rows) {
  consoleRowsByFilter[filterName] = rows;
}

function resetConsoleRows() {
  consoleRowsByFilter = {
    entitlements: [],
    invitations: [],
    assignments: [],
    updates: [],
    health: [],
  };
  activeConsoleFilter = 'all';
}

function updateEventRows(records) {
  return records.map((record) => ({
    type: `<span class="pill ${badgeClassForStatus(record.status)}">Update</span>`,
    primary: `<code class="inline">${escapeHtml(record.installation_uuid)}</code>`,
    scope: `${escapeHtml(record.status)}<br><span class="small">${escapeHtml(record.created_at)}</span>`,
    owner: escapeHtml(record.approved_owner_email || '-'),
    keyInfo: `${escapeHtml(record.from_release_version || 'unknown')} -> <code class="inline">${escapeHtml(record.to_release_version)}</code>`,
    details: `${escapeHtml(record.tenant_name || record.application_key || 'Unknown tenant')}<br><span class="small">${escapeHtml(record.failure_reason || 'no failure')}</span>`,
  }));
}

function stateReportRows(records) {
  return records.map((record) => ({
    type: '<span class="pill">Health</span>',
    primary: `<code class="inline">${escapeHtml(record.installation_uuid)}</code>`,
    scope: `${escapeHtml(record.health_state || 'unknown')}<br><span class="small">${escapeHtml(record.reported_at)}</span>`,
    owner: escapeHtml(record.approved_owner_email || '-'),
    keyInfo: `<code class="inline">${escapeHtml(record.current_release_version)}</code><br><span class="small">${escapeHtml(record.deployment_mode || 'unknown mode')}</span>`,
    details: `${escapeHtml(record.tenant_name || record.application_key || 'Unknown tenant')}<br><span class="small">${escapeHtml(record.activation_status)} / ${escapeHtml(record.licence_status)}</span>`,
  }));
}

function entitlementRows(records) {
  return records.map((record) => ({
    type: '<span class="pill">Entitlement</span>',
    primary: `<code class="inline">${record.entitlement_uuid}</code>`,
    scope: `${record.activation_status}<br><span class="small">${record.tenant_name || 'No tenant'}</span>`,
    owner: record.approved_owner_email,
    keyInfo: `<code class="inline">${record.application_key}</code><br><span class="small">${record.licence_status}</span>`,
    details: `${record.installation_uuid || 'unbound'}<br><span class="small">grace ${record.offline_grace_days}d</span>`,
  }));
}

function invitationRows(records) {
  return records.map((record) => ({
    type: `<span class="pill ${badgeClassForStatus(record.effective_status || record.status)}">Invitation</span>`,
    primary: `<code class="inline">${escapeHtml(record.invitation_uuid)}</code>`,
    scope: `<span class="pill ${badgeClassForStatus(record.effective_status || record.status)}">${escapeHtml(record.effective_status || record.status)}</span><br><span class="small">${escapeHtml(record.reseller_uuid || 'no reseller scope')}</span>`,
    owner: escapeHtml(record.email),
    keyInfo: `<code class="inline">${escapeHtml(record.role_name)}</code>`,
    details: `<div class="token-actions"><code class="inline">${escapeHtml(record.invitation_token)}</code><button type="button" class="mini-button" data-copy-token="${escapeHtml(record.invitation_token)}">Copy</button><button type="button" class="mini-button" data-fill-token="${escapeHtml(record.invitation_token)}">Use</button></div>${formatLifecycleTimestamp('created', record.created_at)}<br>${formatLifecycleTimestamp('expires', record.expires_at)}<br>${formatLifecycleTimestamp('accepted', record.accepted_at)}`,
  }));
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
}

function resellerSummaryRows(summary) {
  setMetricValue('metricResellerCount', summary.installation_count || 0);
  return summary.installations.map((record) => ({
    type: '<span class="pill">Reseller Installation</span>',
    primary: `<code class="inline">${record.entitlement_uuid}</code>`,
    scope: `${summary.reseller_uuid}<br><span class="small">${record.activation_status}</span>`,
    owner: record.approved_owner_email,
    keyInfo: `<code class="inline">${record.application_key}</code>`,
    details: `${record.tenant_name || 'No tenant'}<br><span class="small">${record.licence_status}</span>`,
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
    activateTab(preferredTabForRole(payload.user.role_name));
    if (pageName === 'console') {
      await loadConsoleLandingData(payload.user.role_name);
    } else if (payload.user.role_name === 'platform_admin') {
      await loadAdminSummary();
      await loadOwnerSummary();
      await loadInstallations();
    } else if (payload.user.role_name === 'reseller') {
      await loadResellerSummary();
    } else if (payload.user.role_name === 'owner' || payload.user.role_name === 'support') {
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
    document.getElementById('login_email').value = payload.email;
    activateTab('overview');
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
    setStatus('Session cleared.');
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function handleBootstrap() {
  try {
    const result = await api('/api/v1/auth/bootstrap-admin', { method: 'POST' });
    setStatus(`Bootstrap admin ready for ${result.email}. Use change-this-admin-password unless this admin already existed.`);
  } catch (error) {
    if (error.message === 'Bootstrap admin flow is disabled') {
      setStatus('Bootstrap is disabled on the running service. Stop it and start Local Bootstrap Admin mode first.', true);
      return;
    }
    setStatus(error.message, true);
  }
}

async function loadConsoleLandingData(roleName) {
  if (roleName === 'platform_admin') {
    await loadAdminSummary();
    await loadInstallations();
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

async function createInvitation() {
  try {
    const invitation = await api('/api/v1/admin/invitations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        email: document.getElementById('invite_email').value.trim(),
        role_name: document.getElementById('invite_role_name').value,
        reseller_uuid: document.getElementById('invite_reseller_uuid').value.trim() || null,
        expires_in_days: Number(document.getElementById('invite_expires_in_days').value || 7),
      }),
    });
    setConsoleRows('invitations', invitationRows([invitation]));
    renderConsoleFilter();
    setStatus(`Created invitation for ${invitation.email}.`);
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
    ]);
    renderActivityList('resellerRecentAssignments', assignmentActivityItems(summary.recent_assignments || []), 'No reseller assignment activity yet.');
    renderActivityList('resellerRecentHealth', stateReportActivityItems(summary.recent_health_reports || []), 'No reseller health activity yet.');
    setConsoleRows('entitlements', resellerSummaryRows(summary));
    setConsoleRows('health', stateReportRows(summary.recent_health_reports || []));
    renderConsoleFilter();
    setStatus(`Loaded reseller summary for ${summary.reseller_uuid}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

function bindClick(id, handler) {
  const node = element(id);
  if (node) {
    node.addEventListener('click', handler);
  }
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

document.querySelectorAll('.tab-button').forEach((button) => {
  button.addEventListener('click', () => activateTab(button.dataset.tab));
});

document.querySelectorAll('.console-filter').forEach((button) => {
  button.addEventListener('click', () => {
    activeConsoleFilter = button.dataset.consoleFilter || 'all';
    renderConsoleFilter();
  });
});

bindClick('loginButton', handleLogin);
bindClick('logoutButton', handleLogout);
bindClick('bootstrapButton', handleBootstrap);
bindClick('acceptInvitationButton', handleAcceptInvitation);
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
bindClick('createInvitation', createInvitation);
bindClick('loadInvitations', loadInvitations);
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
    setStatus(`Reseller invitation created for ${invitation.email}.`);
  } catch (error) {
    setStatus(error.message, true);
  }
});
bindClick('resellerAssignButton', () => assignInstallation('/api/v1/reseller/installation-assignments', 'reseller_assignment_entitlement_uuid', 'reseller_assignment_user_email').catch((error) => setStatus(error.message, true)));
bindClick('loadOwnerInstallations', loadOwnerInstallations);
bindClick('loadResellerSummary', loadResellerSummary);
bindClick('loadAdminSummary', loadAdminSummary);
bindClick('loadOverviewResellerSummary', loadResellerSummary);
bindClick('loadOwnerSummary', loadOwnerSummary);

const requestedFilter = new URLSearchParams(window.location.search).get('filter');
if (requestedFilter && (requestedFilter === 'all' || Object.prototype.hasOwnProperty.call(consoleRowsByFilter, requestedFilter))) {
  activeConsoleFilter = requestedFilter;
}
renderConsoleFilter();
updateAuthView();
syncRoleVisibility();

async function restoreSessionOnLoad() {
  const storedToken = persistedSessionToken();
  if (!storedToken) {
    return;
  }
  sessionToken = storedToken;
  try {
    const me = await loadSession();
    activateTab(preferredTabForRole(me.role_name));
    if (pageName === 'console') {
      await loadConsoleLandingData(me.role_name);
    }
  } catch (error) {
    sessionToken = '';
    currentUser = null;
    storeSessionToken('');
    updateAuthView();
  }
}

restoreSessionOnLoad();
