from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=True)

from main import app

client = TestClient(app)

admin_page = client.get('/admin')
assert admin_page.status_code == 200
admin_html = admin_page.text
assert 'id="viewMenuToggle"' in admin_html
assert 'data-view="distributor"' in admin_html
assert 'id="sessionOpenConsoleButton"' in admin_html
assert 'id="logoutButton"' in admin_html
assert 'id="loadSessionButton"' in admin_html
assert 'id="openChangePasswordButton"' in admin_html
assert 'id="changePasswordModal"' in admin_html
assert 'id="changePasswordForm"' in admin_html
assert 'id="change_password_current"' in admin_html
assert 'id="change_password_new"' in admin_html
assert 'id="change_password_confirm"' in admin_html
assert 'class="menu-toggle-icon"' in admin_html
assert 'class="view-navigation-user-email" id="currentEmail"' in admin_html
assert 'Role: <span id="currentRole">' in admin_html
assert 'data-view="session"' not in admin_html
assert 'id="bootstrapButton"' not in admin_html
assert 'id="distributorInviteButton"' in admin_html
assert 'id="distributor_invite_role_name"' in admin_html
assert 'id="distributorInviteEmailLabel"' in admin_html
assert 'id="distributor_invite_reseller_uuid"' not in admin_html
assert 'id="loadDistributorResellersButton"' in admin_html
assert 'id="loadDistributorOwnersButton"' in admin_html
assert 'id="distributorAssignButton"' in admin_html
assert 'id="acceptInvitationCard"' in admin_html
assert 'data-public-view="login"' in admin_html
assert 'data-public-view="invitation"' in admin_html
assert 'id="acceptInvitationForm" class="compact-invitation-form invitation-view-form"' in admin_html
assert 'id="backToLoginButton"' in admin_html
assert 'id="invite_distributor_uuid"' in admin_html
assert 'id="toastRegion" class="toast-region"' in admin_html
assert 'id="updateUserStatusButton"' in admin_html
assert 'id="reassignUserScopeButton"' in admin_html
assert 'id="updateEntitlementStatusButton"' in admin_html
assert 'id="loadAuditEventsButton"' in admin_html
assert 'id="loadMoreAuditEventsButton"' in admin_html
assert 'id="adminAuditEvents"' in admin_html
assert 'id="supportReinstateUserButton"' in admin_html
assert 'id="adminUserDirectory"' in admin_html
assert 'id="admin_user_lookup"' in admin_html
assert 'id="adminUserLookupResults"' in admin_html
assert 'id="reassign_user_lookup"' in admin_html
assert 'id="reassignUserLookupResults"' in admin_html
assert 'id="audit_target_entity_type"' in admin_html
assert 'id="audit_target_entity_uuid"' in admin_html
assert 'id="audit_action"' in admin_html
assert 'id="audit_actor_role_name"' in admin_html

console_page = client.get('/admin/console')
assert console_page.status_code == 200
console_html = console_page.text
assert 'data-console-filter="hierarchy"' in console_html
assert 'data-console-filter="audit"' in console_html
assert 'data-console-filter="users"' in console_html
assert 'id="consoleSearchInput"' in console_html
assert '<th>Actions</th>' in console_html
assert 'colspan="7"' in console_html
assert 'id="openChangePasswordButton"' in console_html
assert 'id="changePasswordModal"' in console_html
assert 'class="menu-toggle-icon"' in console_html
assert 'class="view-navigation-user-email" id="currentEmail"' in console_html
assert 'Role: <span id="currentRole">' in console_html
assert 'data-view="session"' not in console_html
assert 'id="toastRegion" class="toast-region"' in console_html
assert 'data-view="distributor" href="/admin?view=distributor"' in console_html
assert 'data-view="reseller" href="/admin?view=reseller"' in console_html

assets_js = client.get('/admin/assets/admin.js')
assert assets_js.status_code == 200
js_text = assets_js.text
assert 'loadDistributorSummary' in js_text
assert 'loadAdminUsers' in js_text
assert 'loadAuditEvents' in js_text
assert 'updateUserStatus' in js_text
assert 'reassignUserScope' in js_text
assert 'updateEntitlementStatus' in js_text
assert 'supportReinstateUser' in js_text
assert 'adminUserActivityItems' in js_text
assert 'renderUserLookupResults' in js_text
assert 'matchingUsers' in js_text
assert 'userRows' in js_text
assert 'data-user-quick-status' in js_text
assert 'data-prepare-reassign' in js_text
assert 'data-select-user-lookup' in js_text
assert 'data-entitlement-status' in js_text
assert 'data-open-audit' in js_text
assert 'data-support-reinstate-user' in js_text
assert 'buildUserConsoleActions' in js_text
assert 'buildEntitlementConsoleActions' in js_text
assert 'viewerCanManageEntitlements' in js_text
assert 'viewerCanEmergencyReinstate' in js_text
assert 'target_entity_uuid' in js_text
assert 'target_entity_type' in js_text
assert 'actor_role_name' in js_text
assert 'actor_email' in js_text
assert 'auditTransitionSummary' in js_text
assert 'loadMoreAuditEvents' in js_text
assert 'applyAuditFiltersToInputs' in js_text
assert 'loadDistributorScopedUsers' in js_text
assert 'function showToast(message, tone = ' in js_text
assert 'function resolvedRequestedView(roleName)' in js_text
assert "nextSearch.set('view', viewId)" in js_text
assert 'function syncDistributorInviteForm()' in js_text
assert "owner: ['owner', 'support']" in js_text
assert 'requestedPublicView' in js_text
assert "window.location.href = '/admin';" in js_text
assert 'login_email=' in js_text
assert 'setChangePasswordModalOpen' in js_text
assert '/api/v1/auth/change-password' in js_text
assert 'data-console-filter="hierarchy"' not in js_text

assets_css = client.get('/admin/assets/admin.css')
assert assets_css.status_code == 200
css_text = assets_css.text
assert '.console-action-menu' in css_text
assert '.console-actions-cell' in css_text
assert 'td::before {' in css_text
assert 'content: attr(data-label);' in css_text
assert 'thead {' in css_text
assert 'display: none;' in css_text
print('Authority admin UI validation passed.')