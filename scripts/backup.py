import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parents[1]


def run(command, **kwargs):
    completed = subprocess.run(command, stderr=subprocess.PIPE, **kwargs)
    if completed.returncode:
        raise SystemExit('Database backup/recovery command failed. No credentials were printed.')
    return completed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['backup', 'restore-check'])
    parser.add_argument('--env-file', default='.env.production')
    parser.add_argument('--directory', default='backups')
    parser.add_argument('--file', type=Path)
    parser.add_argument('--service', choices=['db', 'matching-db'], default='db')
    args = parser.parse_args()
    compose = ['docker', 'compose', '--env-file', args.env_file, '-f', str(ROOT / 'compose.production.yaml')]
    if args.service == 'matching-db':
        compose += ['-f', str(ROOT / 'deploy/with-matching.yaml')]
    user = 'sentinel_admin' if args.service == 'db' else 'matching'
    tables = ('sentinel.incidents', 'sentinel.incident_versions') if args.service == 'db' else ('public.orders', 'public.trades')
    if args.operation == 'backup':
        directory = Path(args.directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / (datetime.now(timezone.utc).strftime(f'{args.service}-%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8] + '.dump')
        try:
            with destination.open('xb') as output:
                os.chmod(destination, 0o600)
                run(compose + ['exec', '-T', args.service, 'sh', '-c', f'exec pg_dump -U {user} -d "$POSTGRES_DB" -Fc'], stdout=output)
            run(compose + ['exec', '-T', args.service, 'pg_restore', '--list'], input=destination.read_bytes(), stdout=subprocess.DEVNULL)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        print(json.dumps({'file': str(destination), 'bytes': destination.stat().st_size, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}))
    else:
        if not args.file or not args.file.is_file():
            raise SystemExit('Supply an existing --file backup.')
        database = 'sentinel_restore_' + uuid.uuid4().hex[:12]
        run(compose + ['exec', '-T', args.service, 'createdb', '-U', user, database], stdout=subprocess.DEVNULL)
        try:
            run(compose + ['exec', '-T', args.service, 'pg_restore', '--exit-on-error', '--no-owner', '--no-privileges', '-U', user, '-d', database], input=args.file.read_bytes(), stdout=subprocess.DEVNULL)
            outcome = run(compose + ['exec', '-T', args.service, 'psql', '-U', user, '-d', database, '-At', '-c', f'SELECT count(*) FROM {tables[0]}; SELECT count(*) FROM {tables[1]};'], stdout=subprocess.PIPE)
            counts = [int(value) for value in outcome.stdout.decode().splitlines()]
            print(json.dumps({'restored': True, 'tables': dict(zip(tables, counts)), 'production_database_modified': False}))
        finally:
            run(compose + ['exec', '-T', args.service, 'dropdb', '-U', user, database], stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
