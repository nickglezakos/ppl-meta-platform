from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=True)

from main import app

client = TestClient(app)

admin_page = client.get('/admin')
assert admin_page.status_code == 200
admin_html = admin_page.text
assert 'id="distributorInviteButton"' in admin_html
assert 'id="loadDistributorResellersButton"' in admin_html
assert 'id="loadDistributorOwnersButton"' in admin_html
assert 'id="distributorAssignButton"' in admin_html

console_page = client.get('/admin/console')
assert console_page.status_code == 200
assert 'data-console-filter="hierarchy"' in console_page.text

assert client.post('/api/v1/auth/bootstrap-admin').status_code == 200
admin_login = client.post('/api/v1/auth/login', json={
    'email': 'admin@authority.local',
    'password': 'change-this-admin-password'
})
assert admin_login.status_code == 200
admin_headers = {'Authorization': f"Bearer {admin_login.json()['session_token']}"}

distributor_invitation = client.post('/api/v1/admin/invitations', json={
    'email': 'e2e-distributor@example.com',
    'role_name': 'distributor',
    'distributor_uuid': 'e2e-distributor-group'
}, headers=admin_headers)
assert distributor_invitation.status_code == 201

assert client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': distributor_invitation.json()['invitation_token'],
    'password': 'e2edist88'
}).status_code == 201

distributor_login = client.post('/api/v1/auth/login', json={
    'email': 'e2e-distributor@example.com',
    'password': 'e2edist88'
})
assert distributor_login.status_code == 200
distributor_headers = {'Authorization': f"Bearer {distributor_login.json()['session_token']}"}
assert distributor_login.json()['user']['role_name'] == 'distributor'

assert client.post('/api/v1/auth/register', json={
    'email': 'existing-owner-upgrade@example.com',
    'password': 'ownerstay88',
    'role_name': 'owner'
}).status_code == 201

owner_upgrade_invitation = client.post('/api/v1/admin/invitations', json={
    'email': 'existing-owner-upgrade@example.com',
    'role_name': 'distributor',
    'distributor_uuid': 'upgraded-distributor-group'
}, headers=admin_headers)
assert owner_upgrade_invitation.status_code == 201

owner_upgrade_accept = client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': owner_upgrade_invitation.json()['invitation_token'],
    'password': 'nowdistrib88',
    'display_name': 'Upgraded Distributor'
})
assert owner_upgrade_accept.status_code == 201
assert owner_upgrade_accept.json()['role_name'] == 'distributor'
assert owner_upgrade_accept.json()['distributor_uuid'] == 'upgraded-distributor-group'

upgraded_login = client.post('/api/v1/auth/login', json={
    'email': 'existing-owner-upgrade@example.com',
    'password': 'nowdistrib88'
})
assert upgraded_login.status_code == 200
assert upgraded_login.json()['user']['role_name'] == 'distributor'
assert upgraded_login.json()['user']['display_name'] == 'Upgraded Distributor'
assert upgraded_login.json()['user']['distributor_uuid'] == 'upgraded-distributor-group'

reseller_invitation = client.post('/api/v1/distributor/invitations', json={
    'email': 'e2e-reseller@example.com',
    'reseller_uuid': 'e2e-reseller-group'
}, headers=distributor_headers)
assert reseller_invitation.status_code == 201

assert client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': reseller_invitation.json()['invitation_token'],
    'password': 'e2eres88'
}).status_code == 201

reseller_login = client.post('/api/v1/auth/login', json={
    'email': 'e2e-reseller@example.com',
    'password': 'e2eres88'
})
assert reseller_login.status_code == 200
reseller_headers = {'Authorization': f"Bearer {reseller_login.json()['session_token']}"}

owner_invitation = client.post('/api/v1/reseller/invitations', json={
    'email': 'e2e-owner@example.com'
}, headers=reseller_headers)
assert owner_invitation.status_code == 201

assert client.post('/api/v1/auth/accept-invitation', json={
    'invitation_token': owner_invitation.json()['invitation_token'],
    'password': 'e2eowner88'
}).status_code == 201

installations = client.get('/api/v1/admin/installations', headers=admin_headers)
assert installations.status_code == 200
entitlement = next(
    record for record in installations.json()
    if record['approved_owner_email'] == 'e2e-owner@example.com'
)
assert entitlement['notes'] == 'Auto-created during owner onboarding'
assert entitlement['activation_status'] == 'pending_activation'

owner_list = client.get('/api/v1/distributor/owners', headers=distributor_headers)
assert owner_list.status_code == 200
assert any(record['email'] == 'e2e-owner@example.com' for record in owner_list.json())

reseller_list = client.get('/api/v1/distributor/resellers', headers=distributor_headers)
assert reseller_list.status_code == 200
assert any(record['email'] == 'e2e-reseller@example.com' for record in reseller_list.json())

assignment = client.post('/api/v1/distributor/installation-assignments', json={
    'entitlement_uuid': entitlement['entitlement_uuid'],
    'user_email': 'e2e-owner@example.com'
}, headers=distributor_headers)
assert assignment.status_code == 201

distributor_summary = client.get('/api/v1/dashboard/distributor/summary', headers=distributor_headers)
assert distributor_summary.status_code == 200
summary_payload = distributor_summary.json()
assert summary_payload['distributor_uuid'] == 'e2e-distributor-group'
assert summary_payload['reseller_count'] >= 1
assert summary_payload['owner_count'] >= 1
assert any(record['email'] == 'e2e-owner@example.com' for record in summary_payload['owners'])

print('Authority admin end-to-end workflow validation passed.')