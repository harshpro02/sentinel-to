import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

from api.storage import connection_settings


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    settings = connection_settings()
    if not settings['password'] or not os.getenv('POSTGRES_PASSWORD'):
        raise SystemExit('Set both database passwords before applying migrations.')
    app_user = settings['user']
    app_password = settings['password']
    settings.update(user='sentinel_admin', password=os.environ['POSTGRES_PASSWORD'])
    try:
        with psycopg.connect(**settings) as conn:
            conn.execute('SELECT pg_advisory_xact_lock(7112026)')
            exists = conn.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (app_user,)).fetchone()
            if not exists:
                conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(app_user), sql.Literal(app_password)))
            conn.execute(sql.SQL('ALTER ROLE {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(app_user)))
            conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            conn.execute('CREATE TABLE IF NOT EXISTS public.sentinel_migrations (version text PRIMARY KEY)')
            for path in sorted((Path(__file__).parent / 'migrations').glob('*.sql')):
                applied = conn.execute('SELECT 1 FROM public.sentinel_migrations WHERE version = %s', (path.name,)).fetchone()
                if not applied:
                    conn.execute(path.read_text(encoding='utf-8'))
                    conn.execute('INSERT INTO public.sentinel_migrations VALUES (%s)', (path.name,))
            conn.execute(sql.SQL('GRANT USAGE ON SCHEMA sentinel TO {}').format(sql.Identifier(app_user)))
            conn.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA sentinel FROM {}').format(sql.Identifier(app_user)))
            conn.execute(sql.SQL('GRANT SELECT, INSERT ON sentinel.feed_batches, sentinel.incident_versions TO {}').format(sql.Identifier(app_user)))
            conn.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE ON sentinel.incidents TO {}').format(sql.Identifier(app_user)))
        print('Database migrations applied. Runtime role has no schema creation or deletion privileges.')
    except psycopg.Error:
        raise SystemExit('Database setup failed. Check local configuration and database readiness.') from None


if __name__ == '__main__':
    main()
