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
    'email': 'reseller4@example.com',
    'password': 'reseller44',
    'role_name': 'reseller',
    'distributor_uuid': 'distributor-group-4',
    'reseller_uuid': 'reseller-group-4'
}).status_code == 201
reseller_login = client.post('/api/v1/auth/login', json={
    'email': 'reseller4@example.com',
    'password': 'reseller44'
})
assert reseller_login.status_code == 200
reseller_headers = {'Authorization': f"Bearer {reseller_login.json()['session_token']}"}
assert reseller_login.json()['user']['distributor_uuid'] == 'distributor-group-4'
invitation = client.post('/api/v1/reseller/invitations', json={
    'email': 'invited4@example.com'
}, headers=reseller_headers)
assert invitation.status_code == 201
assert client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': invitation.json()['invitation_token'],
    'password': 'invitepass4'
}).status_code == 201
installations = client.get('/api/v1/admin/installations', headers=admin_headers)
assert installations.status_code == 200
entitlement = next(
    record for record in installations.json()
    if record['approved_owner_email'] == 'invited4@example.com'
)
assert entitlement['notes'] == 'Auto-created during owner onboarding'
assert entitlement['activation_status'] == 'pending_activation'
assert client.post('/api/v1/reseller/installation-assignments', json={
    'entitlement_uuid': entitlement['entitlement_uuid'],
    'user_email': 'invited4@example.com'
}, headers=reseller_headers).status_code == 201
owner_login = client.post('/api/v1/auth/login', json={
    'email': 'invited4@example.com',
    'password': 'invitepass4'
})
assert owner_login.status_code == 200
owner_headers = {'Authorization': f"Bearer {owner_login.json()['session_token']}"}
owner_user_uuid = owner_login.json()['user']['user_uuid']

reseller_suspend_owner = client.patch(
    f'/api/v1/reseller/users/{owner_user_uuid}/status',
    json={
        'status': 'suspended',
        'reason_code': 'scope_policy_test',
    },
    headers=reseller_headers,
)
assert reseller_suspend_owner.status_code == 200, reseller_suspend_owner.text
assert reseller_suspend_owner.json()['status'] == 'suspended'

owner_login_denied = client.post('/api/v1/auth/login', json={
    'email': 'invited4@example.com',
    'password': 'invitepass4'
})
assert owner_login_denied.status_code == 401, owner_login_denied.text

reseller_reinstate_owner = client.patch(
    f'/api/v1/reseller/users/{owner_user_uuid}/status',
    json={
        'status': 'active',
        'reason_code': 'scope_policy_test',
    },
    headers=reseller_headers,
)
assert reseller_reinstate_owner.status_code == 200, reseller_reinstate_owner.text
assert reseller_reinstate_owner.json()['status'] == 'active'

reseller_suspend_self = client.patch(
    f"/api/v1/reseller/users/{reseller_login.json()['user']['user_uuid']}/status",
    json={
        'status': 'suspended',
        'reason_code': 'scope_policy_test',
    },
    headers=reseller_headers,
)
assert reseller_suspend_self.status_code == 403, reseller_suspend_self.text
assert reseller_suspend_self.json()['detail'] == 'Reseller may only suspend or reinstate owner users'

owner_login = client.post('/api/v1/auth/login', json={
    'email': 'invited4@example.com',
    'password': 'invitepass4'
})
assert owner_login.status_code == 200, owner_login.text
owner_headers = {'Authorization': f"Bearer {owner_login.json()['session_token']}"}

assert owner_login.json()['user']['distributor_uuid'] == 'distributor-group-4'
assert client.get('/api/v1/dashboard/owner/installations', headers=owner_headers).status_code == 200
assert client.get('/api/v1/dashboard/reseller/summary', headers=reseller_headers).status_code == 200
print('Authority reseller scope validation passed.')
