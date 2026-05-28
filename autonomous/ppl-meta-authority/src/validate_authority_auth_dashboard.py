from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=True)

from main import app

client = TestClient(app)
assert client.post('/api/v1/auth/bootstrap-admin').status_code == 200
admin_login = client.post('/api/v1/auth/login', json={
    'email': 'admin@authority.local',
    'password': 'change-this-admin-password'
})
assert admin_login.status_code == 200
admin_token = admin_login.json()['session_token']
admin_headers = {'Authorization': f'Bearer {admin_token}'}
assert client.get('/api/v1/auth/me', headers=admin_headers).status_code == 200
change_password_response = client.post('/api/v1/auth/change-password', headers=admin_headers, json={
    'current_password': 'change-this-admin-password',
    'new_password': 'authority-admin-pass-2'
})
assert change_password_response.status_code == 200, change_password_response.text
admin_login_after_password_change = client.post('/api/v1/auth/login', json={
    'email': 'admin@authority.local',
    'password': 'authority-admin-pass-2'
})
assert admin_login_after_password_change.status_code == 200
admin_token = admin_login_after_password_change.json()['session_token']
admin_headers = {'Authorization': f'Bearer {admin_token}'}
assert client.post('/api/v1/auth/register', json={
    'email': 'reseller@example.com',
    'password': 'resellerpass',
    'role_name': 'reseller',
    'reseller_uuid': 'reseller-group-1'
}).status_code == 201
owner_create = client.post('/api/v1/auth/register', json={
    'email': 'owner2@example.com',
    'password': 'ownerpass1',
    'role_name': 'owner',
    'reseller_uuid': 'reseller-group-1'
})
assert owner_create.status_code == 201
owner_user_uuid = owner_create.json()['user_uuid']
created_entitlement = client.post('/api/v1/admin/installations', json={
    'application_key': 'owner2-key',
    'approved_owner_email': 'owner2@example.com',
    'owner_enabled': True,
    'licence_status': 'active',
    'tenant_name': 'Owner 2 Tenant'
}, headers=admin_headers)
assert created_entitlement.status_code == 200
updated_entitlement = client.post('/api/v1/admin/installations', json={
    'entitlement_uuid': created_entitlement.json()['entitlement_uuid'],
    'approved_owner_email': 'owner2@example.com',
    'owner_enabled': False,
    'licence_status': 'grace',
    'offline_grace_days': 21,
    'tenant_name': 'Owner 2 Tenant Updated'
}, headers=admin_headers)
assert updated_entitlement.status_code == 200
assert updated_entitlement.json()['application_key'] == 'owner2-key'
assert updated_entitlement.json()['owner_enabled'] is False
assert updated_entitlement.json()['licence_status'] == 'grace'
assert updated_entitlement.json()['offline_grace_days'] == 21
owner_login = client.post('/api/v1/auth/login', json={
    'email': 'owner2@example.com',
    'password': 'ownerpass1'
})
assert owner_login.status_code == 200
owner_headers = {'Authorization': f"Bearer {owner_login.json()['session_token']}"}
assert client.get('/api/v1/dashboard/owner/installations', headers=owner_headers).status_code == 200
admin_summary = client.get('/api/v1/dashboard/admin/summary', headers=admin_headers)
assert admin_summary.status_code == 200
assert 'suspended_user_count' in admin_summary.json()
assert 'orphaned_user_count' in admin_summary.json()
reseller_login = client.post('/api/v1/auth/login', json={
    'email': 'reseller@example.com',
    'password': 'resellerpass'
})
assert reseller_login.status_code == 200
reseller_headers = {'Authorization': f"Bearer {reseller_login.json()['session_token']}"}
reseller_summary = client.get('/api/v1/dashboard/reseller/summary', headers=reseller_headers)
assert reseller_summary.status_code == 200
assert 'suspended_owner_count' in reseller_summary.json()
assert 'orphaned_owner_count' in reseller_summary.json()
assert client.patch(
    f'/api/v1/admin/users/{owner_user_uuid}/status',
    headers=admin_headers,
    json={'status': 'suspended', 'reason_code': 'dashboard_check'}
).status_code == 200
admin_summary_after_suspend = client.get('/api/v1/dashboard/admin/summary', headers=admin_headers)
assert admin_summary_after_suspend.status_code == 200
assert admin_summary_after_suspend.json()['suspended_user_count'] >= 1
print('Authority auth and dashboard validation passed.')
