# Production release

The release uses one Amazon Linux EC2 t3.small host for Sentinel and the Crossing portfolio demo. CloudFormation defines the network, host, encrypted disk, Elastic IP, private S3 backup bucket, image repositories and instance role. Only TCP 80 and 443 are public. Administration uses AWS Systems Manager rather than SSH.

## Sign in and validate

Start Docker Desktop. In a terminal, authenticate with temporary browser credentials:

```powershell
docker run --rm -it -e AWS_PAGER= -v "${env:USERPROFILE}/.aws:/root/.aws" public.ecr.aws/aws-cli/aws-cli:latest login --remote --profile portfolio --region us-east-1
.\.venv\Scripts\python.exe scripts/deploy_aws.py
```

The second command verifies access and validates the infrastructure template without creating resources. Verify the selected AWS account before applying. Never paste authentication codes or keys into chat or commit them.

## Release

Commit both repositories first. The server-side Ontario 511 key must exist in the local ignored `.env`. Existing local databases are not uploaded.

```powershell
.\.venv\Scripts\python.exe scripts/deploy_aws.py --apply
```

The helper builds three images locally before provisioning, publishes immutable commit tags, stores the feed key as an SSM SecureString, and sends a release command to the instance. It writes a nonsecret, ignored `deploy/last-release.local.json` receipt. If a release fails, inspect the existing CloudFormation stack and SSM command before retrying; do not create duplicate stacks.

Caddy terminates HTTPS on the generated sslip.io hostnames. PostgreSQL services have no host ports. Sentinel migrations use a separate administrative credential; the running API uses a restricted role. Persistent Docker volumes retain database and certificate data across container replacement. Do not remove volumes to troubleshoot a release.

## Verification and recovery

Verify both HTTPS pages, Sentinel health and official feed timestamps, incident history, and an actual Crossing demo trade. Check container health and memory on the server. A green container health check alone does not verify the public site.

Nightly backups run at 04:17 server time, create PostgreSQL custom-format archives and upload them to private encrypted S3 storage. Local archives expire after seven days and S3 archives after fourteen days. Manually run `/usr/bin/python3 /opt/portfolio/current/deploy/backup_remote.py` through Systems Manager for the first backup. Use `scripts/backup.py restore-check` with an archive to verify recovery into a new temporary database without changing production data.

Database volumes live on the instance disk, so replacing the instance loses them. The template therefore pins `HostAmi`; the release helper passes the running host's image so a newer Amazon Linux image never triggers replacement. To move to a newer image deliberately, back up first, then plan the restore below.

To restore production from a nightly archive, run through Systems Manager: take a fresh `backup_remote.py` backup, download the chosen archives from S3, run `scripts/backup.py restore-check` for each, stop `api` and `matching-api`, then run `pg_restore --single-transaction --clean --if-exists --exit-on-error` inside each database container and start the stack with `docker compose up -d --no-build --wait`. Verify row counts and the public history API afterwards. This was done on November 25, 2026.

The previous release directory is retained at `/opt/portfolio/previous`. Application rollback requires selecting the previous images and verifying schema compatibility; it is not an automatic database rollback.

## Costs and shutdown

Budget approximately USD 21/month baseline in us-east-1 before credits, taxes, bandwidth, registry storage and backups. Confirm current account pricing and credits before launch. Budget alerts warn and do not impose a spending cap. No NAT gateway or load balancer is provisioned. CPU credits use standard mode.

Stopping EC2 stops compute charges but the disk, Elastic IP, stored images and backups can still incur charges. Deleting the stack terminates the host and its disk; the S3 bucket and ECR repositories are intentionally retained. Back up required data first, then separately review retained resources and the SSM parameter when decommissioning.
