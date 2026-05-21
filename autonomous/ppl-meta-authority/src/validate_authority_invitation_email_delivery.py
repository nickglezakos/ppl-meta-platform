import os

from fastapi.testclient import TestClient

from validation_support import prepare_validation_database

prepare_validation_database(bootstrap_enabled=True)

os.environ['AUTHORITY_BASE_URL'] = 'https://authority.example.test'
os.environ['MAIL_SERVER'] = 'smtp.example.test'
os.environ['MAIL_PORT'] = '587'
os.environ['MAIL_USERNAME'] = 'mailer@example.test'
os.environ['MAIL_PASSWORD'] = 'not-a-real-password'
os.environ['MAIL_FROM'] = 'noreply@example.test'
os.environ['MAIL_FROM_NAME'] = 'Eyenet Vision Test'
os.environ['MAIL_STARTTLS'] = 'true'
os.environ['MAIL_SSL_TLS'] = 'false'
os.environ['USE_CREDENTIALS'] = 'true'

from main import app
from core import email as authority_email


smtp_events: list[tuple[str, object]] = []


class FakeSMTP:
    def __init__(self, server: str, port: int):
        smtp_events.append(('connect', (server, port)))

    def __enter__(self) -> 'FakeSMTP':
        smtp_events.append(('enter', None))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        smtp_events.append(('exit', exc_type))

    def starttls(self) -> None:
        smtp_events.append(('starttls', None))

    def login(self, username: str, password: str) -> None:
        smtp_events.append(('login', (username, bool(password))))

    def sendmail(self, from_email: str, recipients: list[str], message: str) -> None:
        smtp_events.append(('sendmail', (from_email, tuple(recipients), message)))


original_smtp = authority_email.smtplib.SMTP
authority_email.smtplib.SMTP = FakeSMTP

try:
    client = TestClient(app)
    assert client.post('/api/v1/auth/bootstrap-admin').status_code == 200
    admin_login = client.post('/api/v1/auth/login', json={
        'email': 'admin@authority.local',
        'password': 'change-this-admin-password'
    })
    assert admin_login.status_code == 200
    admin_headers = {'Authorization': f"Bearer {admin_login.json()['session_token']}"}

    invitation = client.post('/api/v1/admin/invitations', json={
        'email': 'email-validated-owner@example.com',
        'role_name': 'owner',
        'reseller_uuid': 'reseller-group-email',
        'distributor_uuid': 'distributor-group-email',
    }, headers=admin_headers)
    assert invitation.status_code == 201
    invitation_body = invitation.json()
    assert invitation_body['email_delivery_attempted'] is True
    assert invitation_body['email_delivered'] is True
    assert 'Invitation email sent to email-validated-owner@example.com.' == invitation_body['email_delivery_message']

    listed = client.get('/api/v1/admin/invitations', headers=admin_headers)
    assert listed.status_code == 200
    persisted = listed.json()[0]
    assert persisted['email_delivery_attempted'] is True
    assert persisted['email_delivered'] is True
    assert persisted['email_delivery_message'] == invitation_body['email_delivery_message']

    sendmail_events = [event for event in smtp_events if event[0] == 'sendmail']
    assert sendmail_events, 'Expected fake SMTP sendmail to be called'
    last_sendmail = sendmail_events[-1][1]
    assert last_sendmail[0] == 'noreply@example.test'
    assert 'email-validated-owner@example.com' in last_sendmail[1]
    assert 'https://authority.example.test/admin?view=session&invitation_token=' in last_sendmail[2]
    assert 'Eyenet Vision' in last_sendmail[2]
    print('Authority invitation email delivery validation passed.')
finally:
    authority_email.smtplib.SMTP = original_smtp