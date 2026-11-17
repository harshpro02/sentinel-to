import json
from pathlib import Path
import subprocess
from datetime import datetime, timedelta, timezone

root = Path('/opt/portfolio')
config = json.loads((root / 'backup.json').read_text())
directory = root / 'backups'
for service in ['db', 'matching-db']:
    output = subprocess.run(['python3', str(root / 'current/scripts/backup.py'), 'backup', '--env-file', str(root / '.env.production'), '--service', service, '--directory', str(directory)], capture_output=True, check=True)
    data = json.loads(output.stdout)
    archive = Path(data['file'])
    subprocess.run(['aws', 's3', 'cp', str(archive), f"s3://{config['bucket']}/backups/{archive.name}", '--region', config['region'], '--only-show-errors'], check=True)
    print(json.dumps({'backup': archive.name, 'bytes': data['bytes'], 'sha256': data['sha256'], 'uploaded': True}))
cutoff = datetime.now(timezone.utc) - timedelta(days=7)
for archive in directory.glob('*.dump'):
    if archive.name.startswith(('db-', 'matching-db-')) and datetime.fromtimestamp(archive.stat().st_mtime, timezone.utc) < cutoff:
        archive.unlink()
