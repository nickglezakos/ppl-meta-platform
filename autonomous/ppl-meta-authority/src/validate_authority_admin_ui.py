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
assert 'id="loadDistributorResellersButton"' in admin_html
assert 'id="loadDistributorOwnersButton"' in admin_html
assert 'id="distributorAssignButton"' in admin_html
assert 'id="invite_distributor_uuid"' in admin_html
assert 'id="currentDistributorScope"' in admin_html
assert 'class="status page-status" data-shared-status data-auth-visibility="authenticated"' in admin_html

console_page = client.get('/admin/console')
assert console_page.status_code == 200
console_html = console_page.text
assert 'data-console-filter="hierarchy"' in console_html
assert 'id="currentDistributorScope"' in console_html
assert 'class="status page-status" data-shared-status data-auth-visibility="authenticated"' in console_html

assets_js = client.get('/admin/assets/admin.js')
assert assets_js.status_code == 200
js_text = assets_js.text
assert 'loadDistributorSummary' in js_text
assert 'loadAdminUsers' in js_text
assert 'loadDistributorScopedUsers' in js_text
assert 'data-console-filter="hierarchy"' not in js_text

assets_css = client.get('/admin/assets/admin.css')
assert assets_css.status_code == 200
print('Authority admin UI validation passed.')