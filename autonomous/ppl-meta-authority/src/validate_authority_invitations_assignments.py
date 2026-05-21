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
    'email': 'reseller2@example.com',
    'password': 'reseller22',
    'role_name': 'reseller',
    'distributor_uuid': 'distributor-group-2',
    'reseller_uuid': 'reseller-group-2'
}).status_code == 201
invitation = client.post('/api/v1/admin/invitations', json={
    'email': 'invited-owner@example.com',
    'role_name': 'owner',
    'distributor_uuid': 'distributor-group-2',
    'reseller_uuid': 'reseller-group-2'
}, headers=admin_headers)
assert invitation.status_code == 201
assert 'email_delivery_attempted' in invitation.json()
assert 'email_delivered' in invitation.json()
assert 'email_delivery_message' in invitation.json()
missing_distributor_scope = client.post('/api/v1/admin/invitations', json={
    'email': 'missing-distributor-scope@example.com',
    'role_name': 'distributor'
}, headers=admin_headers)
assert missing_distributor_scope.status_code == 400
assert missing_distributor_scope.json()['detail'] == 'Distributor invitations require a distributor_uuid'
list_invitations = client.get('/api/v1/admin/invitations', headers=admin_headers)
assert list_invitations.status_code == 200
assert 'email_delivery_attempted' in list_invitations.json()[0]
assert client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': invitation.json()['invitation_token'],
    'password': 'invitepass1'
}).status_code == 201
entitlement = client.post('/api/v1/admin/installations', json={
    'application_key': 'invited-owner-key',
    'approved_owner_email': 'invited-owner@example.com',
    'owner_enabled': True,
    'licence_status': 'active',
    'tenant_name': 'Invited Owner Tenant'
}, headers=admin_headers)
assert entitlement.status_code == 200
assert client.post('/api/v1/admin/installation-assignments', json={
    'entitlement_uuid': entitlement.json()['entitlement_uuid'],
    'user_email': 'invited-owner@example.com'
}, headers=admin_headers).status_code == 201
owner_login = client.post('/api/v1/auth/login', json={
    'email': 'invited-owner@example.com',
    'password': 'invitepass1'
})
assert owner_login.status_code == 200
owner_headers = {'Authorization': f"Bearer {owner_login.json()['session_token']}"}
assert client.get('/api/v1/dashboard/owner/installations', headers=owner_headers).status_code == 200
reseller_login = client.post('/api/v1/auth/login', json={
    'email': 'reseller2@example.com',
    'password': 'reseller22'
})
assert reseller_login.status_code == 200
reseller_headers = {'Authorization': f"Bearer {reseller_login.json()['session_token']}"}
assert reseller_login.json()['user']['distributor_uuid'] == 'distributor-group-2'
assert client.get('/api/v1/dashboard/reseller/summary', headers=reseller_headers).status_code == 200
print('Authority invitation and assignment validation passed.')
