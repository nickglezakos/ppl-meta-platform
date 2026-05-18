from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=False)

from main import app

client = TestClient(app)
assert client.post('/api/v1/installations/activate', json={
    'application_key': 'mvp-demo-key',
    'installation_uuid': 'test-installation',
    'owner_email': 'owner@example.com'
}).status_code == 200
assert client.post('/api/v1/installations/report-state', json={
    'installation_uuid': 'test-installation',
    'current_release_version': '2.24.88',
    'deployment_mode': 'docker',
    'health_state': 'healthy',
    'components': {'ppl-meta-node': '2.24.88', 'ppl-meta-frontend': '2.24.88'}
}).status_code == 200
assert client.post('/api/v1/installations/check-update', json={
    'installation_uuid': 'test-installation',
    'target_release_version': '2.25.00'
}).status_code == 200
assert client.post('/api/v1/installations/report-update-result', json={
    'installation_uuid': 'test-installation',
    'from_release_version': '2.24.88',
    'to_release_version': '2.25.00',
    'status': 'succeeded',
    'components': {'ppl-meta-node': '2.25.00', 'ppl-meta-frontend': '2.25.00'}
}).status_code == 200
print('Authority lifecycle validation passed.')
