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
assert client.post('/api/v1/auth/register', json={
    'email': 'reseller@example.com',
    'password': 'resellerpass',
    'role_name': 'reseller',
    'reseller_uuid': 'reseller-group-1'
}).status_code == 201
assert client.post('/api/v1/auth/register', json={
    'email': 'owner2@example.com',
    'password': 'ownerpass1',
    'role_name': 'owner',
    'reseller_uuid': 'reseller-group-1'
}).status_code == 201
assert client.post('/api/v1/admin/installations', json={
    'application_key': 'owner2-key',
    'approved_owner_email': 'owner2@example.com',
    'owner_enabled': True,
    'licence_status': 'active',
    'tenant_name': 'Owner 2 Tenant'
}, headers=admin_headers).status_code == 200
owner_login = client.post('/api/v1/auth/login', json={
    'email': 'owner2@example.com',
    'password': 'ownerpass1'
})
assert owner_login.status_code == 200
owner_headers = {'Authorization': f"Bearer {owner_login.json()['session_token']}"}
assert client.get('/api/v1/dashboard/owner/installations', headers=owner_headers).status_code == 200
reseller_login = client.post('/api/v1/auth/login', json={
    'email': 'reseller@example.com',
    'password': 'resellerpass'
})
assert reseller_login.status_code == 200
reseller_headers = {'Authorization': f"Bearer {reseller_login.json()['session_token']}"}
assert client.get('/api/v1/dashboard/reseller/summary', headers=reseller_headers).status_code == 200
print('Authority auth and dashboard validation passed.')
