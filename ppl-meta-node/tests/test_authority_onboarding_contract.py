import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

TESTS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(TESTS_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.services.authority_service import (  # noqa: E402
    AUTHORITY_APPLICATION_KEY_SETTING,
    AUTHORITY_INSTALLATION_UUID_SETTING,
    AuthorityService,
)


class AuthorityOnboardingContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_activate_owner_candidate_uses_persisted_settings_values(self):
        db = MagicMock()
        app_setting_query = MagicMock()
        installation_query = MagicMock()
        installation_info = SimpleNamespace(guid='generated-installation-guid')

        db.query.side_effect = [app_setting_query, app_setting_query, installation_query]

        application_key_setting = SimpleNamespace(
            key=AUTHORITY_APPLICATION_KEY_SETTING,
            value='persisted-licence-key',
        )
        installation_uuid_setting = SimpleNamespace(
            key=AUTHORITY_INSTALLATION_UUID_SETTING,
            value='persisted-installation-uuid',
        )

        app_setting_query.filter.side_effect = [
            MagicMock(first=MagicMock(return_value=application_key_setting)),
            MagicMock(first=MagicMock(return_value=installation_uuid_setting)),
        ]
        installation_query.first.return_value = installation_info

        activation_payload = {
            'approved': True,
            'reason': 'approved_owner',
            'installation_uuid': 'persisted-installation-uuid',
            'application_key': 'persisted-licence-key',
            'approved_owner_email': 'owner@example.com',
            'owner_enabled': True,
            'licence_status': 'active',
            'offline_grace_days': 14,
            'activation_status': 'active',
        }

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = activation_payload

        http_client = AsyncMock()
        http_client.__aenter__.return_value = http_client
        http_client.__aexit__.return_value = None
        http_client.post.return_value = response

        with patch('src.services.authority_service.settings.AUTHORITY_SERVICE_ENABLED', True), patch(
            'src.services.authority_service.settings.AUTHORITY_SERVICE_URL',
            'https://authority.example.com',
        ), patch('src.services.authority_service.settings.AUTHORITY_INSTALLATION_UUID', ''), patch(
            'src.services.authority_service.settings.AUTHORITY_APPLICATION_KEY',
            '',
        ), patch('src.services.authority_service.settings.AUTHORITY_TIMEOUT_SECONDS', 5), patch(
            'src.services.authority_service.httpx.AsyncClient',
            return_value=http_client,
        ), patch.object(
            AuthorityService,
            '_persist_effective_authority_settings',
        ), patch.object(
            AuthorityService,
            '_cache_authority_state',
        ), patch.object(
            AuthorityService,
            '_record_failed_check',
        ):
            service = AuthorityService()
            result = await service.activate_owner_candidate(db, 'owner@example.com')

        self.assertTrue(result['configured'])
        self.assertTrue(result['approved'])
        self.assertEqual(result['reason'], 'approved_owner')
        http_client.post.assert_awaited_once_with(
            'https://authority.example.com/api/v1/installations/activate',
            json={
                'application_key': 'persisted-licence-key',
                'installation_uuid': 'persisted-installation-uuid',
                'owner_email': 'owner@example.com',
            },
        )

    async def test_activate_owner_candidate_falls_back_to_generated_installation_guid(self):
        db = MagicMock()
        app_setting_query = MagicMock()
        installation_query = MagicMock()
        installation_info = SimpleNamespace(guid='generated-installation-guid')

        db.query.side_effect = [app_setting_query, app_setting_query, installation_query]

        application_key_setting = SimpleNamespace(
            key=AUTHORITY_APPLICATION_KEY_SETTING,
            value='persisted-licence-key',
        )

        app_setting_query.filter.side_effect = [
            MagicMock(first=MagicMock(return_value=application_key_setting)),
            MagicMock(first=MagicMock(return_value=None)),
        ]
        installation_query.first.return_value = installation_info

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            'approved': False,
            'reason': 'owner_email_not_approved',
        }

        http_client = AsyncMock()
        http_client.__aenter__.return_value = http_client
        http_client.__aexit__.return_value = None
        http_client.post.return_value = response

        with patch('src.services.authority_service.settings.AUTHORITY_SERVICE_ENABLED', True), patch(
            'src.services.authority_service.settings.AUTHORITY_SERVICE_URL',
            'https://authority.example.com',
        ), patch('src.services.authority_service.settings.AUTHORITY_INSTALLATION_UUID', ''), patch(
            'src.services.authority_service.settings.AUTHORITY_APPLICATION_KEY',
            '',
        ), patch('src.services.authority_service.settings.AUTHORITY_TIMEOUT_SECONDS', 5), patch(
            'src.services.authority_service.httpx.AsyncClient',
            return_value=http_client,
        ), patch.object(
            AuthorityService,
            '_persist_effective_authority_settings',
        ), patch.object(
            AuthorityService,
            '_cache_authority_state',
        ), patch.object(
            AuthorityService,
            '_record_failed_check',
        ):
            service = AuthorityService()
            result = await service.activate_owner_candidate(db, 'owner@example.com')

        self.assertTrue(result['configured'])
        self.assertFalse(result['approved'])
        self.assertEqual(result['reason'], 'owner_email_not_approved')
        http_client.post.assert_awaited_once_with(
            'https://authority.example.com/api/v1/installations/activate',
            json={
                'application_key': 'persisted-licence-key',
                'installation_uuid': 'generated-installation-guid',
                'owner_email': 'owner@example.com',
            },
        )


if __name__ == '__main__':
    unittest.main()
