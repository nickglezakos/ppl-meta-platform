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

console_page = client.get('/admin/console')
assert console_page.status_code == 200
console_html = console_page.text
assert 'data-console-filter="hierarchy"' in console_html
assert 'id="currentDistributorScope"' in console_html
assert 'id="toastRegion" class="toast-region"' in console_html
assert 'data-view="distributor" href="/admin?view=distributor"' in console_html
assert 'data-view="reseller" href="/admin?view=reseller"' in console_html

assets_js = client.get('/admin/assets/admin.js')
assert assets_js.status_code == 200
js_text = assets_js.text
assert 'loadDistributorSummary' in js_text
assert 'loadAdminUsers' in js_text
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