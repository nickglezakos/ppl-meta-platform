from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=False)

from main import app

client = TestClient(app)
response = client.post('/api/v1/auth/bootstrap-admin')
assert response.status_code == 403
print('Authority bootstrap gate validation passed.')
