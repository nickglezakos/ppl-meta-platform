from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=False)

from main import app
from core.storage import create_authority_user, upsert_entitlement

client = TestClient(app)

admin_password = 'authority-admin-pass'

create_authority_user(
    email='admin@authority.local',
    password=admin_password,
    display_name='Authority Admin',
    role_name='platform_admin',
)
owner = create_authority_user(
    email='owner.audit@example.com',
    password='owner-pass-123',
    display_name='Audit Owner',
    role_name='owner',
)
entitlement = upsert_entitlement({
    'application_key': 'audit-api-key',
    'approved_owner_email': owner['email'],
    'owner_enabled': True,
    'licence_status': 'active',
    'offline_grace_days': 14,
    'tenant_name': 'Audit API Tenant',
    'activation_status': 'pending_activation',
})

login_response = client.post('/api/v1/auth/login', json={
    'email': 'admin@authority.local',
    'password': admin_password,
})
assert login_response.status_code == 200, login_response.text
admin_headers = {'Authorization': f"Bearer {login_response.json()['session_token']}"}

for status_value in ['suspended', 'active']:
    response = client.patch(
        f"/api/v1/admin/users/{owner['user_uuid']}/status",
        headers=admin_headers,
        json={'status': status_value, 'reason_code': 'audit_api_check'},
    )
    assert response.status_code == 200, response.text

for activation_status in ['suspended', 'revoked', 'active']:
    response = client.patch(
        f"/api/v1/admin/installations/{entitlement['entitlement_uuid']}/activation-status",
        headers=admin_headers,
        json={'activation_status': activation_status, 'reason_code': 'audit_api_check'},
    )
    assert response.status_code == 200, response.text

page_one = client.get('/api/v1/admin/audit-events', headers=admin_headers, params={'limit': 2, 'offset': 0})
assert page_one.status_code == 200, page_one.text
page_one_payload = page_one.json()
assert len(page_one_payload['items']) == 2
assert page_one_payload['offset'] == 0
assert page_one_payload['limit'] == 2
assert isinstance(page_one_payload['has_more'], bool)

if page_one_payload['has_more']:
    assert page_one_payload['next_offset'] == 2
    page_two = client.get('/api/v1/admin/audit-events', headers=admin_headers, params={'limit': 2, 'offset': 2})
    assert page_two.status_code == 200, page_two.text
    page_two_payload = page_two.json()
    first_ids = [item['audit_event_uuid'] for item in page_one_payload['items']]
    second_ids = [item['audit_event_uuid'] for item in page_two_payload['items']]
    assert not set(first_ids).intersection(second_ids)

filtered = client.get(
    '/api/v1/admin/audit-events',
    headers=admin_headers,
    params={
        'target_entity_type': 'entitlement',
        'target_entity_uuid': entitlement['entitlement_uuid'],
        'action': 'entitlement_status_changed',
        'limit': 10,
        'offset': 0,
    },
)
assert filtered.status_code == 200, filtered.text
filtered_payload = filtered.json()
assert filtered_payload['items']
assert all(item['target_entity_type'] == 'entitlement' for item in filtered_payload['items'])
assert all(item['target_entity_uuid'] == entitlement['entitlement_uuid'] for item in filtered_payload['items'])
assert all(item['action'] == 'entitlement_status_changed' for item in filtered_payload['items'])
assert all(item['actor_email'] == 'admin@authority.local' for item in filtered_payload['items'])

print('Authority audit API validation passed.')