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
admin_headers = {'Authorization': f"Bearer {admin_login.json()['session_token']}"}

assert client.post('/api/v1/auth/register', json={
    'email': 'distributor@example.com',
    'password': 'distrib88',
    'role_name': 'distributor',
    'distributor_uuid': 'distributor-group-8'
}).status_code == 201

distributor_login = client.post('/api/v1/auth/login', json={
    'email': 'distributor@example.com',
    'password': 'distrib88'
})
assert distributor_login.status_code == 200
distributor_headers = {'Authorization': f"Bearer {distributor_login.json()['session_token']}"}

reseller_invitation = client.post('/api/v1/distributor/invitations', json={
    'email': 'dist-reseller@example.com',
    'role_name': 'reseller',
    'reseller_uuid': 'reseller-group-8'
}, headers=distributor_headers)
assert reseller_invitation.status_code == 201

assert client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': reseller_invitation.json()['invitation_token'],
    'password': 'reseller88'
}).status_code == 201

reseller_login = client.post('/api/v1/auth/login', json={
    'email': 'dist-reseller@example.com',
    'password': 'reseller88'
})
assert reseller_login.status_code == 200
assert reseller_login.json()['user']['role_name'] == 'reseller'
assert reseller_login.json()['user']['distributor_uuid'] == 'distributor-group-8'
assert reseller_login.json()['user']['reseller_uuid'] == 'reseller-group-8'
reseller_headers = {'Authorization': f"Bearer {reseller_login.json()['session_token']}"}

owner_invitation = client.post('/api/v1/distributor/invitations', json={
    'email': 'dist-owner@example.com',
    'role_name': 'owner'
}, headers=distributor_headers)
assert owner_invitation.status_code == 201

assert client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': owner_invitation.json()['invitation_token'],
    'password': 'owner8888'
}).status_code == 201

owner_login = client.post('/api/v1/auth/login', json={
    'email': 'dist-owner@example.com',
    'password': 'owner8888'
})
assert owner_login.status_code == 200
assert owner_login.json()['user']['role_name'] == 'owner'
assert owner_login.json()['user']['distributor_uuid'] == 'distributor-group-8'
assert owner_login.json()['user']['reseller_uuid'] is None

missing_reseller_scope = client.post('/api/v1/distributor/invitations', json={
    'email': 'missing-reseller-scope@example.com',
    'role_name': 'reseller'
}, headers=distributor_headers)
assert missing_reseller_scope.status_code == 400
assert missing_reseller_scope.json()['detail'] == 'Reseller invitations require a reseller_uuid'

distributor_summary = client.get('/api/v1/dashboard/distributor/summary', headers=distributor_headers)
assert distributor_summary.status_code == 200
summary_payload = distributor_summary.json()
assert summary_payload['distributor_uuid'] == 'distributor-group-8'
assert summary_payload['reseller_count'] == 1
assert summary_payload['owner_count'] == 1
assert len(summary_payload['resellers']) == 1
assert summary_payload['resellers'][0]['reseller_uuid'] == 'reseller-group-8'

entitlement = client.post('/api/v1/admin/installations', json={
    'application_key': 'dist-owner-key',
    'approved_owner_email': 'dist-owner@example.com',
    'owner_enabled': True,
    'licence_status': 'active',
    'tenant_name': 'Distributor Owner Tenant'
}, headers=admin_headers)
assert entitlement.status_code == 200

owner_list = client.get('/api/v1/distributor/owners', headers=distributor_headers)
assert owner_list.status_code == 200
assert len(owner_list.json()) == 1
assert owner_list.json()[0]['email'] == 'dist-owner@example.com'

reseller_list = client.get('/api/v1/distributor/resellers', headers=distributor_headers)
assert reseller_list.status_code == 200
assert len(reseller_list.json()) == 1
assert reseller_list.json()[0]['email'] == 'dist-reseller@example.com'

assignment = client.post('/api/v1/distributor/installation-assignments', json={
    'entitlement_uuid': entitlement.json()['entitlement_uuid'],
    'user_email': 'dist-owner@example.com'
}, headers=distributor_headers)
assert assignment.status_code == 201

admin_reseller_invitation = client.post('/api/v1/admin/invitations', json={
    'email': 'admin-dist-reseller@example.com',
    'role_name': 'reseller',
    'distributor_uuid': 'distributor-group-8',
    'reseller_uuid': 'reseller-group-8b'
}, headers=admin_headers)
assert admin_reseller_invitation.status_code == 201
assert admin_reseller_invitation.json()['distributor_uuid'] == 'distributor-group-8'
print('Authority distributor scope validation passed.')