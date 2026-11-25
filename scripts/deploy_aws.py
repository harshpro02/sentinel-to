import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CLI_IMAGE = 'public.ecr.aws/aws-cli/aws-cli:latest'


def checked(command, **kwargs):
    completed = subprocess.run(command, stderr=subprocess.PIPE, **kwargs)
    if completed.returncode:
        raise SystemExit('A deployment command failed. Credentials and configuration values were withheld; inspect the named service or AWS console.')
    return completed.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--region', default='us-east-1')
    parser.add_argument('--profile', default='portfolio')
    parser.add_argument('--matching-repo', type=Path, default=ROOT.parent / 'trade-matching-engine')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    stage = Path(tempfile.mkdtemp(prefix='portfolio-deploy-')).resolve()
    if not stage.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise SystemExit('Unexpected staging directory.')
    def aws(*command, raw=False):
        output = checked(['docker', 'run', '--rm', '-e', 'AWS_PAGER=', '--mount', f'type=bind,source={Path.home() / ".aws"},target=/root/.aws', '--mount', f'type=bind,source={ROOT},target=/workspace,readonly', '--mount', f'type=bind,source={stage},target=/stage,readonly', CLI_IMAGE, '--profile', args.profile, '--region', args.region, '--output', 'json', *command], stdout=subprocess.PIPE)
        return output if raw else json.loads(output) if output.strip() else None
    def sha(directory):
        if checked(['git', '-C', str(directory), 'diff', '--name-only', 'HEAD'], stdout=subprocess.PIPE).strip():
            raise SystemExit('Commit tracked changes before creating a reproducible release.')
        return checked(['git', '-C', str(directory), 'rev-parse', 'HEAD'], stdout=subprocess.PIPE).decode().strip()[:12]
    try:
        aws('sts', 'get-caller-identity')
        aws('cloudformation', 'validate-template', '--template-body', 'file:///workspace/deploy/aws-portfolio.json')
        print('AWS access and infrastructure template verified. One t3.small host, 20 GiB gp3 disk and one public IPv4. Estimated baseline around USD 21/month in us-east-1 before credits, tax, transfer and small image/backup storage charges.', flush=True)
        if not args.apply:
            print('No resources created. Use --apply after reviewing the deployment plan.')
            return
        sentinel_tag, matching_tag = sha(ROOT), sha(args.matching_repo)
        from dotenv import dotenv_values
        feed_key = dotenv_values(ROOT / '.env').get('ONTARIO_511_API_KEY')
        if not feed_key:
            raise SystemExit('Set the local server-side Ontario 511 key before deploying.')
        for command in [
            ['docker', 'build', '-t', 'sentinel-api:release-check', str(ROOT)],
            ['docker', 'build', '-f', str(ROOT / 'web/Dockerfile'), '-t', 'sentinel-web:release-check', str(ROOT)],
            ['docker', 'build', '-t', 'matching-engine:release-check', str(args.matching_repo)],
        ]:
            print('Building a release image before creating cloud resources.', flush=True)
            checked(command, stdout=subprocess.DEVNULL)
        existing_stack = aws('cloudformation', 'list-stacks', '--stack-status-filter', 'CREATE_COMPLETE', 'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE', '--query', "StackSummaries[?StackName=='portfolio-demo'].StackName")
        if existing_stack:
            running = aws('cloudformation', 'describe-stacks', '--stack-name', 'portfolio-demo', '--query', "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue | [0]")
            host_ami = aws('ec2', 'describe-instances', '--instance-ids', running, '--query', 'Reservations[0].Instances[0].ImageId')
            print(f'Keeping the running host image {host_ami}; the instance and its database disk are not replaced.', flush=True)
        else:
            host_ami = aws('ssm', 'get-parameter', '--name', '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64', '--query', 'Parameter.Value')
            print(f'New stack: using the current Amazon Linux 2023 image {host_ami}.', flush=True)
        print('Provisioning the portfolio-demo stack; existing local databases are not uploaded.', flush=True)
        aws('cloudformation', 'deploy', '--stack-name', 'portfolio-demo', '--template-file', '/workspace/deploy/aws-portfolio.json', '--capabilities', 'CAPABILITY_IAM', '--no-fail-on-empty-changeset', '--parameter-overrides', f'HostAmi={host_ami}', '--tags', 'Project=portfolio-demo', raw=True)
        stack = aws('cloudformation', 'describe-stacks', '--stack-name', 'portfolio-demo')['Stacks'][0]
        outputs = {item['OutputKey']: item['OutputValue'] for item in stack['Outputs']}
        prefix = outputs['RegistryPrefix']
        registry = prefix.split('/')[0]
        password = aws('ecr', 'get-login-password', raw=True)
        checked(['docker', 'login', '--username', 'AWS', '--password-stdin', registry], input=password, stdout=subprocess.DEVNULL)
        for local, remote, tag in [('sentinel-api', 'sentinel-api', sentinel_tag), ('sentinel-web', 'sentinel-web', sentinel_tag), ('matching-engine', 'matching-engine', matching_tag)]:
            target = f'{prefix}{remote}:{tag}'
            existing = aws('ecr', 'list-images', '--repository-name', 'portfolio-demo-' + remote, '--filter', 'tagStatus=TAGGED', '--query', 'imageIds[].imageTag')
            if tag in existing:
                print(f'Image {remote} ({tag}) already exists; reusing its immutable tag.', flush=True)
                continue
            checked(['docker', 'tag', f'{local}:release-check', target])
            print(f'Publishing {remote} ({tag})', flush=True)
            checked(['docker', 'push', target], stdout=subprocess.DEVNULL)
        checked(['docker', 'logout', registry], stdout=subprocess.DEVNULL)
        secret = stage / 'feed-key.json'
        secret.write_text(json.dumps({'Name': '/portfolio-demo/ontario-511-key', 'Type': 'SecureString', 'Value': feed_key, 'Overwrite': True}), encoding='utf-8')
        os.chmod(secret, 0o600)
        aws('ssm', 'put-parameter', '--cli-input-json', 'file:///stage/feed-key.json')
        secret.unlink()
        release_id = f'{sentinel_tag}-{matching_tag}'
        archive = stage / f'{release_id}.tar.gz'
        files = ['compose.production.yaml', 'deploy/with-matching.yaml', 'deploy/Caddyfile.portfolio', 'deploy/remote_release.py', 'deploy/backup_remote.py', 'scripts/backup.py']
        with tarfile.open(archive, 'w:gz') as bundle:
            for filename in files:
                bundle.add(ROOT / filename, arcname=filename)
        bucket = outputs['ArtifactBucket']
        aws('s3', 'cp', f'/stage/{archive.name}', f's3://{bucket}/releases/{archive.name}', '--only-show-errors', raw=True)
        instance = outputs['InstanceId']
        print('Waiting for the EC2 management agent.', flush=True)
        for _ in range(60):
            hosts = aws('ssm', 'describe-instance-information', '--filters', f'Key=InstanceIds,Values={instance}')['InstanceInformationList']
            if hosts and hosts[0]['PingStatus'] == 'Online':
                break
            time.sleep(10)
        else:
            raise SystemExit('The EC2 management agent is not ready. Inspect bootstrap logs; do not create another stack.')
        release = f'/opt/portfolio/releases/{release_id}'
        commands = ['set -eu', 'for attempt in $(seq 1 60); do test -f /opt/portfolio/bootstrap-ready && break; sleep 5; done', 'test -f /opt/portfolio/bootstrap-ready', f'mkdir -p {shlex.quote(release)}', f'aws s3 cp s3://{bucket}/releases/{archive.name} /opt/portfolio/release.tar.gz --region {args.region} --only-show-errors', f'tar -xzf /opt/portfolio/release.tar.gz -C {shlex.quote(release)}', 'python3 ' + shlex.quote(release + '/deploy/remote_release.py') + ' ' + ' '.join(shlex.quote(value) for value in ['--ip', outputs['PublicIp'], '--region', args.region, '--registry-prefix', prefix, '--sentinel-tag', sentinel_tag, '--matching-tag', matching_tag, '--bucket', bucket])]
        request = stage / 'command.json'
        request.write_text(json.dumps({'DocumentName': 'AWS-RunShellScript', 'InstanceIds': [instance], 'Parameters': {'commands': commands, 'executionTimeout': ['900']}}), encoding='utf-8')
        command_id = aws('ssm', 'send-command', '--cli-input-json', 'file:///stage/command.json')['Command']['CommandId']
        print('Releasing both apps through Session Manager, without an SSH port.', flush=True)
        for _ in range(100):
            invocations = aws('ssm', 'list-command-invocations', '--command-id', command_id)['CommandInvocations']
            status = invocations[0]['Status'] if invocations else 'Pending'
            if status == 'Success':
                break
            if status not in ['Pending', 'InProgress', 'Delayed']:
                raise SystemExit(f'Release status {status}. Inspect this SSM command in AWS; no second deployment was started.')
            time.sleep(10)
        else:
            raise SystemExit('Release still running; inspect the existing SSM command before retrying.')
        receipt = {key: outputs[key] for key in ['InstanceId', 'PublicIp', 'ArtifactBucket', 'SentinelUrl', 'MatchingUrl']}
        receipt.update(sentinel_tag=sentinel_tag, matching_tag=matching_tag, region=args.region, public_browser_verification='pending')
        (ROOT / 'deploy/last-release.local.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt, indent=2))
        print('Deployment finished. Verify HTTPS, official feeds, demo trades and backup recovery before claiming a public release.', flush=True)
    finally:
        for file in stage.iterdir():
            if file.is_file():
                file.unlink()
        stage.rmdir()


if __name__ == '__main__':
    main()
