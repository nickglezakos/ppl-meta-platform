from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=False)

from main import app
from core.storage import create_authority_user, list_authority_audit_events, upsert_entitlement

client = TestClient(app)

admin_password = 'authority-admin-pass'
owner_password = 'owner-pass-123'

create_authority_user(
    email='admin@authority.local',
    password=admin_password,
    display_name='Authority Admin',
    role_name='platform_admin',
)
create_authority_user(
    email='support.lifecycle@example.com',
    password='support-pass-123',
    display_name='Lifecycle Support',
    role_name='support',
)
owner = create_authority_user(
    email='owner.lifecycle@example.com',
    password=owner_password,
    display_name='Lifecycle Owner',
    role_name='owner',
)
reseller = create_authority_user(
    email='reseller.lifecycle@example.com',
    password='reseller-pass-123',
    display_name='Lifecycle Reseller',
    role_name='reseller',
    distributor_uuid='dist-lifecycle',
    reseller_uuid='reseller-lifecycle',
)
orphan_owner = create_authority_user(
    email='orphan.owner@example.com',
    password='orphan-pass-123',
    display_name='Orphan Owner',
    role_name='owner',
    distributor_uuid='dist-lifecycle',
    reseller_uuid='reseller-lifecycle',
)
entitlement = upsert_entitlement({
    'application_key': 'lic_aaaaaaaa222233334444555566667777',
    'approved_owner_email': owner['email'],
    'owner_enabled': True,
    'licence_status': 'active',
    'offline_grace_days': 14,
    'tenant_name': 'Lifecycle Tenant',
    'activation_status': 'pending_activation',
    'notes': 'Lifecycle validation record.',
})

login_response = client.post('/api/v1/auth/login', json={
    'email': 'admin@authority.local',
    'password': admin_password,
})
assert login_response.status_code == 200, login_response.text
admin_token = login_response.json()['session_token']
admin_headers = {'Authorization': f'Bearer {admin_token}'}

suspend_user_response = client.patch(
    f"/api/v1/admin/users/{owner['user_uuid']}/status",
    headers=admin_headers,
    json={'status': 'suspended', 'reason_code': 'policy_enforcement'},
)
assert suspend_user_response.status_code == 200, suspend_user_response.text
assert suspend_user_response.json()['status'] == 'suspended'

owner_login_denied = client.post('/api/v1/auth/login', json={
    'email': owner['email'],
    'password': owner_password,
})
assert owner_login_denied.status_code == 401, owner_login_denied.text

reinstate_user_response = client.patch(
    f"/api/v1/admin/users/{owner['user_uuid']}/status",
    headers=admin_headers,
    json={'status': 'active', 'reason_code': 'manual_recovery'},
)
assert reinstate_user_response.status_code == 200, reinstate_user_response.text
assert reinstate_user_response.json()['status'] == 'active'

suspend_for_support_response = client.patch(
    f"/api/v1/admin/users/{owner['user_uuid']}/status",
    headers=admin_headers,
    json={'status': 'suspended', 'reason_code': 'policy_enforcement'},
)
assert suspend_for_support_response.status_code == 200, suspend_for_support_response.text

support_login_response = client.post('/api/v1/auth/login', json={
    'email': 'support.lifecycle@example.com',
    'password': 'support-pass-123',
})
assert support_login_response.status_code == 200, support_login_response.text
support_headers = {'Authorization': f"Bearer {support_login_response.json()['session_token']}"}

support_reinstate_response = client.patch(
    f"/api/v1/support/users/{owner['user_uuid']}/reinstate",
    headers=support_headers,
    json={'reason_code': 'emergency_recovery'},
)
assert support_reinstate_response.status_code == 200, support_reinstate_response.text
assert support_reinstate_response.json()['status'] == 'active'

owner_login_allowed = client.post('/api/v1/auth/login', json={
    'email': owner['email'],
    'password': owner_password,
})
assert owner_login_allowed.status_code == 200, owner_login_allowed.text

suspend_entitlement_response = client.patch(
    f"/api/v1/admin/installations/{entitlement['entitlement_uuid']}/activation-status",
    headers=admin_headers,
    json={'activation_status': 'suspended', 'reason_code': 'policy_enforcement'},
)
assert suspend_entitlement_response.status_code == 200, suspend_entitlement_response.text
assert suspend_entitlement_response.json()['activation_status'] == 'suspended'

revoke_entitlement_response = client.patch(
    f"/api/v1/admin/installations/{entitlement['entitlement_uuid']}/activation-status",
    headers=admin_headers,
    json={'activation_status': 'revoked', 'reason_code': 'commercial_stop'},
)
assert revoke_entitlement_response.status_code == 200, revoke_entitlement_response.text
assert revoke_entitlement_response.json()['activation_status'] == 'revoked'

reinstate_entitlement_response = client.patch(
    f"/api/v1/admin/installations/{entitlement['entitlement_uuid']}/activation-status",
    headers=admin_headers,
    json={'activation_status': 'active', 'reason_code': 'manual_recovery'},
)
assert reinstate_entitlement_response.status_code == 200, reinstate_entitlement_response.text
assert reinstate_entitlement_response.json()['activation_status'] == 'active'

remove_reseller_response = client.patch(
    f"/api/v1/admin/users/{reseller['user_uuid']}/status",
    headers=admin_headers,
    json={'status': 'removed', 'reason_code': 'parent_removed'},
)
assert remove_reseller_response.status_code == 200, remove_reseller_response.text
assert remove_reseller_response.json()['status'] == 'removed'

orphan_login_allowed = client.post('/api/v1/auth/login', json={
    'email': orphan_owner['email'],
    'password': 'orphan-pass-123',
})
assert orphan_login_allowed.status_code == 200, orphan_login_allowed.text
assert orphan_login_allowed.json()['user']['status'] == 'orphaned'

reassign_orphan_response = client.patch(
    f"/api/v1/admin/users/{orphan_owner['user_uuid']}/scope",
    headers=admin_headers,
    json={
        'distributor_uuid': 'dist-reassigned',
        'reseller_uuid': 'reseller-reassigned',
        'reason_code': 'manual_reassignment',
    },
)
assert reassign_orphan_response.status_code == 200, reassign_orphan_response.text
assert reassign_orphan_response.json()['status'] == 'active'
assert reassign_orphan_response.json()['distributor_uuid'] == 'dist-reassigned'
assert reassign_orphan_response.json()['reseller_uuid'] == 'reseller-reassigned'

audit_events = list_authority_audit_events(limit=10)
assert len(audit_events) >= 7
assert any(
    event['target_entity_type'] == 'authority_user'
    and event['target_entity_uuid'] == owner['user_uuid']
    and event['new_state'] == {'status': 'suspended'}
    for event in audit_events
)
assert any(
    event['target_entity_type'] == 'authority_user'
    and event['target_entity_uuid'] == owner['user_uuid']
    and event['reason_code'] == 'emergency_recovery'
    and event['actor_role_name'] == 'support'
    and event['actor_email'] == 'support.lifecycle@example.com'
    for event in audit_events
)
assert any(
    event['target_entity_type'] == 'entitlement'
    and event['target_entity_uuid'] == entitlement['entitlement_uuid']
    and event['new_state'] == {'activation_status': 'revoked'}
    for event in audit_events
)
assert any(
    event['action'] == 'user_orphaned'
    and event['target_entity_uuid'] == orphan_owner['user_uuid']
    for event in audit_events
)
assert any(
    event['action'] == 'user_scope_reassigned'
    and event['target_entity_uuid'] == orphan_owner['user_uuid']
    and event['scope_after'] == {
        'distributor_uuid': 'dist-reassigned',
        'reseller_uuid': 'reseller-reassigned',
    }
    for event in audit_events
)

user_filtered_events = list_authority_audit_events(
    limit=10,
    target_entity_type='authority_user',
    target_entity_uuid=owner['user_uuid'],
)
assert user_filtered_events
assert all(event['target_entity_type'] == 'authority_user' for event in user_filtered_events)
assert all(event['target_entity_uuid'] == owner['user_uuid'] for event in user_filtered_events)

entitlement_filtered_events = client.get(
    '/api/v1/admin/audit-events',
    headers=admin_headers,
    params={
        'target_entity_type': 'entitlement',
        'target_entity_uuid': entitlement['entitlement_uuid'],
        'action': 'entitlement_status_changed',
    },
)
assert entitlement_filtered_events.status_code == 200, entitlement_filtered_events.text
entitlement_events_payload = entitlement_filtered_events.json()
assert entitlement_events_payload['items']
assert entitlement_events_payload['offset'] == 0
assert entitlement_events_payload['limit'] == 100
assert all(event['target_entity_type'] == 'entitlement' for event in entitlement_events_payload['items'])
assert all(event['target_entity_uuid'] == entitlement['entitlement_uuid'] for event in entitlement_events_payload['items'])
assert all(event['action'] == 'entitlement_status_changed' for event in entitlement_events_payload['items'])
assert any(event['actor_email'] == 'admin@authority.local' for event in entitlement_events_payload['items'])

paged_audit_events = client.get(
    '/api/v1/admin/audit-events',
    headers=admin_headers,
    params={'limit': 2, 'offset': 0},
)
assert paged_audit_events.status_code == 200, paged_audit_events.text
paged_payload = paged_audit_events.json()
assert len(paged_payload['items']) == 2
assert paged_payload['offset'] == 0
assert paged_payload['has_more'] is True
assert paged_payload['next_offset'] == 2

next_page_audit_events = client.get(
    '/api/v1/admin/audit-events',
    headers=admin_headers,
    params={'limit': 2, 'offset': 2},
)
assert next_page_audit_events.status_code == 200, next_page_audit_events.text
next_paged_payload = next_page_audit_events.json()
assert next_paged_payload['offset'] == 2
first_page_ids = [event['audit_event_uuid'] for event in paged_payload['items']]
second_page_ids = [event['audit_event_uuid'] for event in next_paged_payload['items']]
assert not set(first_page_ids).intersection(second_page_ids)

combined_page_events = paged_payload['items'] + next_paged_payload['items']
combined_sorted = sorted(
    combined_page_events,
    key=lambda event: ((event['created_at'] or ''), event['audit_event_uuid']),
    reverse=True,
)
assert [event['audit_event_uuid'] for event in combined_page_events] == [event['audit_event_uuid'] for event in combined_sorted]
print('Authority lifecycle validation passed.')
