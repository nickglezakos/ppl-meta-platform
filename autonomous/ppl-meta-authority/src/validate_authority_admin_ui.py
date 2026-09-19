from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=True)

from main import app

client = TestClient(app)

admin_page = client.get('/admin')
assert admin_page.status_code == 200
admin_html = admin_page.text
assert 'id="bottomTabs"' in admin_html
assert 'data-tab="home"' in admin_html
assert 'data-tab="people"' in admin_html
assert 'data-tab="licences"' in admin_html
assert 'data-tab="me"' in admin_html
assert 'id="logoutButton"' in admin_html
assert 'id="loadSessionButton"' in admin_html
assert 'id="openChangePasswordButton"' in admin_html
assert 'id="changePasswordModal"' in admin_html
assert 'id="entityPickerModal"' in admin_html
assert 'id="entityPickerSearchInput"' in admin_html
assert 'id="entityPickerResults"' in admin_html
assert 'id="changePasswordForm"' in admin_html
assert 'id="change_password_current"' in admin_html
assert 'id="change_password_new"' in admin_html
assert 'id="change_password_confirm"' in admin_html
assert 'class="menu-toggle-icon"' in admin_html
assert 'class="view-navigation-user-email" id="currentEmail"' in admin_html
assert 'Role: <span id="currentRole">' in admin_html
assert 'data-view="session"' not in admin_html
assert 'id="bootstrapButton"' in admin_html
assert 'id="inviteForm"' in admin_html
assert 'id="invite_role_name"' in admin_html
assert 'id="invite_email"' in admin_html
assert 'id="invite_distributor_uuid"' in admin_html
assert 'id="invite_reseller_uuid"' in admin_html
assert 'id="acceptInvitationCard"' in admin_html
assert 'data-public-view="login"' in admin_html
assert 'data-public-view="invitation"' in admin_html
assert 'id="acceptInvitationForm"' in admin_html
assert 'id="backToLoginButton"' in admin_html
assert 'id="openInviteSheetButton"' in admin_html
assert 'id="openLicenceWizardButton"' in admin_html
assert 'id="licenceWizard"' in admin_html
assert 'id="peopleList"' in admin_html
assert 'id="licencesList"' in admin_html
assert 'id="toastRegion" class="toast-region"' in admin_html
assert 'id="reassignUserScopeButton"' in admin_html
assert 'id="updateEntitlementDetailsButton"' in admin_html
assert 'id="loadAuditEventsButton"' in admin_html
assert 'id="loadMoreAuditEventsButton"' in admin_html
assert 'id="adminAuditEvents"' in admin_html
assert 'id="supportReinstateUserButton"' in admin_html
assert 'id="audit_target_entity_type"' in admin_html
assert 'id="audit_target_entity_uuid"' in admin_html
assert 'id="audit_action"' in admin_html
assert 'id="audit_actor_role_name"' in admin_html
assert 'id="toolsSection"' in admin_html
assert 'id="homePrimaryCta"' in admin_html

console_redirect = client.get('/admin/console', follow_redirects=False)
assert console_redirect.status_code == 307
assert console_redirect.headers['location'] == '/admin'

assets_js = client.get('/admin/assets/admin.js')
assert assets_js.status_code == 200
js_text = assets_js.text
assert 'activateTab' in js_text
assert 'loadPeople' in js_text
assert 'loadLicences' in js_text
assert 'loadAuditEvents' in js_text
assert 'reassignUserScope' in js_text
assert 'supportReinstateUser' in js_text
assert 'updateEntitlementDetails' in js_text
assert 'setEntityPickerOpen' in js_text
assert 'openEntityPickerForInput' in js_text
assert 'bindUuidPickerInputs' in js_text
assert 'matchingEntitlements' in js_text
assert 'data-uuid-picker-kind' in js_text
assert 'invite_reseller_uuid' in js_text
assert 'reassign_reseller_uuid' in js_text
assert 'function showToast(message, tone = ' in js_text
assert "next.set('tab', tabId)" in js_text
assert '/api/v1/auth/change-password' in js_text
assert 'function confirmLicenceWizard()' in js_text
assert 'TAB_ROLES' in js_text
assert "owner: ['platform_admin', 'distributor', 'reseller', 'owner']" in js_text or "licences: ['platform_admin', 'distributor', 'reseller', 'owner']" in js_text
assert 'requestedInvitationToken' in js_text
assert "window.location.href = '/admin';" in js_text
assert 'login_email=' in js_text
assert 'setChangePasswordModalOpen' in js_text
assert 'loadMoreAuditEvents' in js_text

assets_css = client.get('/admin/assets/admin.css')
assert assets_css.status_code == 200
css_text = assets_css.text
assert '.bottom-tabs' in css_text
assert '.wizard-steps' in css_text
assert '.advanced-card summary' in css_text
assert '.entity-picker-card' in css_text
assert '--primary: #1976d2' in css_text
assert '--secondary: #22d3ee' in css_text
print('Authority admin UI validation passed.')
