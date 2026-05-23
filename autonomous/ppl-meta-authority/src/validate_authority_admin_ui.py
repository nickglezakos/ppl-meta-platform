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
assert 'id="distributorInviteButton"' in admin_html
assert 'id="distributor_invite_role_name"' in admin_html
assert 'id="distributorInviteEmailLabel"' in admin_html
assert 'id="distributor_invite_reseller_uuid"' not in admin_html
assert 'id="loadDistributorResellersButton"' in admin_html
assert 'id="loadDistributorOwnersButton"' in admin_html
assert 'id="distributorAssignButton"' in admin_html
assert 'id="acceptInvitationCard" data-auth-visibility="logged-out"' in admin_html
assert 'id="acceptInvitationForm" class="compact-invitation-form invitation-view-form"' in admin_html
assert 'id="invite_distributor_uuid"' in admin_html
assert 'id="currentDistributorScope"' in admin_html
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
assert 'id="currentDistributorScope"' in console_html
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
assert 'target_entity_uuid' in js_text
assert 'target_entity_type' in js_text
assert 'actor_role_name' in js_text
assert 'actor_email' in js_text
assert 'auditTransitionSummary' in js_text
assert 'loadMoreAuditEvents' in js_text
assert 'applyAuditFiltersToInputs' in js_text
assert 'loadDistributorScopedUsers' in js_text
assert 'function showToast(message, tone = ' in js_text
assert "pageName === 'admin' && Boolean(requestedInvitationToken)" in js_text
assert 'function resolvedRequestedView(roleName)' in js_text
assert 'function syncDistributorInviteForm()' in js_text
assert "owner: ['owner', 'support']" in js_text
assert 'data-console-filter="hierarchy"' not in js_text

assets_css = client.get('/admin/assets/admin.css')
assert assets_css.status_code == 200
print('Authority admin UI validation passed.')