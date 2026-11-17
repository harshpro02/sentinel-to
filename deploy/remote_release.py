import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess


def run(command, capture=False):
    completed = subprocess.run(command, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE)
    if completed.returncode:
        raise SystemExit('A release command failed; inspect service status without printing secret configuration.')
    return completed.stdout if capture else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--registry-prefix', required=True)
    parser.add_argument('--sentinel-tag', required=True)
    parser.add_argument('--matching-tag', required=True)
    parser.add_argument('--bucket', required=True)
    args = parser.parse_args()
    root = Path('/opt/portfolio')
    config = root / '.env.production'
    values = {}
    if config.exists():
        for line in config.read_text().splitlines():
            key, _, value = line.partition('=')
            values[key] = value
    key = json.loads(run(['aws', 'ssm', 'get-parameter', '--region', args.region, '--name', '/portfolio-demo/ontario-511-key', '--with-decryption', '--query', 'Parameter.Value', '--output', 'json'], capture=True))
    if not re.fullmatch(r'[A-Za-z0-9_=.-]+', key):
        raise SystemExit('The feed key format needs manual review before writing deployment configuration.')
    for name in ['POSTGRES_PASSWORD', 'DATABASE_PASSWORD', 'MATCHING_DATABASE_PASSWORD']:
        values.setdefault(name, secrets.token_urlsafe(36))
    values.update(COMPOSE_PROJECT_NAME='portfolio-production', SITE_ADDRESS=f'sentinel.{args.ip}.sslip.io', MATCHING_SITE_ADDRESS=f'exchange.{args.ip}.sslip.io', SENTINEL_ALLOWED_HOSTS=f'sentinel.{args.ip}.sslip.io,api,127.0.0.1', ONTARIO_511_API_KEY=key, DATABASE_NAME='sentinel', DATABASE_USER='sentinel_app', IMAGE_REGISTRY_PREFIX=args.registry_prefix, IMAGE_TAG=args.sentinel_tag, MATCHING_IMAGE_TAG=args.matching_tag, HTTP_PORT='80', HTTPS_PORT='443', HTTP_BIND='0.0.0.0', SENTINEL_REQUESTS_PER_MINUTE='120')
    with os.fdopen(os.open(str(config), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as output:
        output.write(''.join(f'{name}={value}\n' for name, value in values.items()))
    registry = args.registry_prefix.split('/')[0]
    password = run(['aws', 'ecr', 'get-login-password', '--region', args.region], capture=True)
    signed = subprocess.run(['docker', 'login', '--username', 'AWS', '--password-stdin', registry], input=password, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if signed.returncode:
        raise SystemExit('Registry authentication failed.')
    release = Path(__file__).resolve().parents[1]
    compose = ['docker', 'compose', '--env-file', str(config), '-f', str(release / 'compose.production.yaml'), '-f', str(release / 'deploy/with-matching.yaml')]
    run(compose + ['pull', '--quiet'])
    run(['docker', 'logout', registry])
    run(compose + ['run', '--rm', '--no-deps', 'web', 'caddy', 'validate', '--config', '/etc/caddy/Caddyfile', '--adapter', 'caddyfile'])
    run(compose + ['up', '-d', '--no-build', '--wait', '--wait-timeout', '240'])
    current = root / 'current'
    previous = root / 'previous'
    if current.is_symlink():
        previous.unlink(missing_ok=True)
        previous.symlink_to(current.resolve())
        current.unlink()
    current.symlink_to(release)
    backup_config = root / 'backup.json'
    backup_config.write_text(json.dumps({'bucket': args.bucket, 'region': args.region}))
    os.chmod(backup_config, 0o600)
    Path('/etc/cron.d/portfolio-backup').write_text('17 4 * * * root /usr/bin/python3 /opt/portfolio/current/deploy/backup_remote.py >> /var/log/portfolio-backup.log 2>&1\n')
    os.chmod('/etc/cron.d/portfolio-backup', 0o600)
    Path('/etc/logrotate.d/portfolio-backup').write_text('/var/log/portfolio-backup.log {\n daily\n rotate 7\n compress\n missingok\n notifempty\n copytruncate\n}\n')
    print(json.dumps({'released': True, 'sentinel': f'https://sentinel.{args.ip}.sslip.io', 'matching': f'https://exchange.{args.ip}.sslip.io', 'sentinel_tag': args.sentinel_tag, 'matching_tag': args.matching_tag}))


if __name__ == '__main__':
    main()
