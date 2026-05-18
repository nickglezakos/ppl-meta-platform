import os

import psycopg

DEFAULT_VALIDATION_DATABASE_URL = os.getenv(
    'AUTHORITY_VALIDATION_DATABASE_URL',
    'postgresql://authority_user:authority_password@localhost:5432/authority_db',
)


TRUNCATE_STATEMENT = '''
TRUNCATE TABLE
    authority_user_installations,
    authority_sessions,
    authority_invitations,
    update_events,
    installation_state_reports,
    installations,
    entitlements,
    authority_users
RESTART IDENTITY CASCADE
'''


def prepare_validation_database(bootstrap_enabled: bool = False) -> str:
    database_url = os.getenv('AUTHORITY_DATABASE_URL', DEFAULT_VALIDATION_DATABASE_URL)
    os.environ['AUTHORITY_DATABASE_URL'] = database_url
    if bootstrap_enabled:
        os.environ['AUTHORITY_BOOTSTRAP_ADMIN_ENABLED'] = 'true'
    else:
        os.environ.pop('AUTHORITY_BOOTSTRAP_ADMIN_ENABLED', None)

    from core.storage import initialize_database, seed_demo_installation

    initialize_database()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(TRUNCATE_STATEMENT)
        connection.commit()

    initialize_database()
    seed_demo_installation()
    return database_url
