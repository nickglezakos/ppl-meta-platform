from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=True)

from main import app

client = TestClient(app)

assert client.post('/api/v1/auth/bootstrap-admin').status_code == 200
admin_login = client.post('/api/v1/auth/login', json={
    'email': 'admin@authority.local',
    'password': 'change-this-admin-password',
})
assert admin_login.status_code == 200
admin_headers = {'Authorization': f"Bearer {admin_login.json()['session_token']}"}

entitlement_response = client.post('/api/v1/admin/installations', json={
    'application_key': 'lic-activation-001',
    'approved_owner_email': 'owner.contract@example.com',
    'owner_enabled': True,
    'licence_status': 'active',
    'tenant_name': 'Contract Tenant',
}, headers=admin_headers)
assert entitlement_response.status_code == 200
entitlement_payload = entitlement_response.json()
assert entitlement_payload['application_key'] == 'lic-activation-001'
assert entitlement_payload['approved_owner_email'] == 'owner.contract@example.com'
assert entitlement_payload['activation_status'] == 'pending_activation'

settings_payload = {
    'application_key': 'lic-activation-001',
    'installation_uuid': 'platform-settings-installation-001',
}

activation_response = client.post('/api/v1/installations/activate', json={
    **settings_payload,
    'owner_email': 'owner.contract@example.com',
})
assert activation_response.status_code == 200
activation_payload = activation_response.json()
assert activation_payload['approved'] is True
assert activation_payload['reason'] == 'approved_owner'
assert activation_payload['application_key'] == settings_payload['application_key']
assert activation_payload['installation_uuid'] == settings_payload['installation_uuid']
assert activation_payload['approved_owner_email'] == 'owner.contract@example.com'
assert activation_payload['licence_status'] == 'active'
assert activation_payload['activation_status'] == 'active'

owner_mismatch_response = client.post('/api/v1/installations/activate', json={
    'application_key': 'lic-activation-001',
    'installation_uuid': 'platform-settings-installation-002',
    'owner_email': 'other.owner@example.com',
})
assert owner_mismatch_response.status_code == 200
assert owner_mismatch_response.json() == {
    'approved': False,
    'reason': 'owner_email_not_approved',
    'entitlement_uuid': None,
    'installation_uuid': None,
    'application_key': None,
    'approved_owner_email': None,
    'owner_enabled': None,
    'licence_status': None,
    'offline_grace_days': None,
    'tenant_name': None,
    'activation_status': None,
    'notes': None,
}

unknown_key_response = client.post('/api/v1/installations/activate', json={
    'application_key': 'lic-missing-001',
    'installation_uuid': 'platform-settings-installation-003',
    'owner_email': 'owner.contract@example.com',
})
assert unknown_key_response.status_code == 200
assert unknown_key_response.json()['reason'] == 'unknown_application_key'

second_installation_response = client.post('/api/v1/installations/activate', json={
    'application_key': 'lic-activation-001',
    'installation_uuid': 'platform-settings-installation-elsewhere',
    'owner_email': 'owner.contract@example.com',
})
assert second_installation_response.status_code == 200
assert second_installation_response.json()['reason'] == 'installation_already_bound_elsewhere'

state_report_response = client.post('/api/v1/installations/report-state', json={
    'installation_uuid': settings_payload['installation_uuid'],
    'current_release_version': '2.24.90',
    'deployment_mode': 'settings-driven-local',
    'health_state': 'healthy',
    'components': {
        'ppl-meta-node': '2.24.90',
        'ppl-meta-frontend': '2.24.90',
    },
})
assert state_report_response.status_code == 200
assert state_report_response.json()['installation_uuid'] == settings_payload['installation_uuid']

update_check_response = client.post('/api/v1/installations/check-update', json={
    'installation_uuid': settings_payload['installation_uuid'],
    'target_release_version': '2.24.91',
})
assert update_check_response.status_code == 200
assert update_check_response.json()['installation_uuid'] == settings_payload['installation_uuid']

print('Authority activation contract validation passed.')
