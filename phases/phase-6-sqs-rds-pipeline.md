# Phase 6 — API Gateway scraper service → SQS → consumer → RDS

**Status**: Code complete on `feature/sqs-rds-pipeline`. AWS deployment pending (commands below).

## Goal
Move from the batch file pipeline (EC2 → S3 `raw/` → Lambda → S3 `processed/` →
full-bucket scan per request) to an event-driven pipeline:

```
API Gateway POST /scrape  ──►  Lambda quotes-scraper  (publisher)
Ubuntu EC2 systemd timer  ──►  python -m scraper.main (publisher)
                                      │
                                      ▼
                    SQS quotes-ingest-queue  ──(3 failures)──►  quotes-ingest-dlq
                                      │
                                      ▼
                    Lambda quotes-consumer  (consumer: QuoteCleaner + upsert)
                                      │
                                      ▼
                    RDS PostgreSQL  (quotes, scrape_runs)
                                      │
                                      ▼
            Lambdas quotes-api / quotes-status  ──►  React dashboard
```

The `/quotes` and `/status` JSON contracts are unchanged. `POST /scrape` is new.
The S3 path stays in the code as a rollback (`DATA_BACKEND=s3`, `SCRAPER_OUTPUT=s3`).

## Resources
| Resource | Name | Notes |
|---|---|---|
| SQS queue | `quotes-ingest-queue` | visibility timeout 180s (6× consumer timeout), redrive → DLQ after 3 receives |
| SQS DLQ | `quotes-ingest-dlq` | 14-day retention |
| RDS | `quotes-db` | PostgreSQL 16, `db.t4g.micro`, 20 GB gp3, single-AZ, default VPC, **not public** |
| Security groups | `quotes-lambda-sg`, `quotes-ec2-sg`, `quotes-rds-sg` | RDS accepts 5432 only from the other two |
| Lambda (new) | `quotes-scraper` | no VPC (needs internet + SQS), 29s timeout, 256 MB |
| Lambda (new) | `quotes-consumer` | in VPC, 30s timeout, SQS trigger batch 10, `ReportBatchItemFailures` |
| Lambda (moved into VPC) | `quotes-api`, `quotes-status` | `DATA_BACKEND=postgres` + `DB_*` env vars |
| Lambda (retired trigger) | `quotes-processing` | S3 notification removed; function kept for rollback |
| EC2 (new) | `quotes-scraper-ubuntu` | Ubuntu 24.04 `t3.micro`, systemd timer every 6h, also the DB admin host |
| EC2 (retired) | old Windows instance | stop → terminate after the Ubuntu box is verified |
| API route (new) | `POST /scrape` | on `gfoyhnaxh3`, behind the existing `quotes-jwt-authorizer` |

## IAM
- `quotes-scraper-lambda-role`: `AWSLambdaBasicExecutionRole` + `sqs:SendMessage` on `quotes-ingest-queue` only
- `quotes-consumer-lambda-role`: `AWSLambdaVPCAccessExecutionRole` + `sqs:ReceiveMessage`/`DeleteMessage`/`GetQueueAttributes`/`ChangeMessageVisibility` on `quotes-ingest-queue` only
- `quotes-api-lambda-role`, `quotes-status-lambda-role`: **add** `AWSLambdaVPCAccessExecutionRole` (keep the existing S3 read permissions, which are only used for rollback)
- `quotes-ec2-scraper-role` (instance profile): `sqs:SendMessage` on `quotes-ingest-queue` only. No access keys on the box.
- DB password: stored as a Lambda environment variable (encrypted at rest with the Lambda service KMS key). SSM/Secrets Manager isn't used here on purpose: VPC Lambdas can only reach them through a paid interface endpoint (~$7/month each) or a NAT gateway (~$32/month). To upgrade later, add a `secretsmanager` interface endpoint and swap `db/connection.py` to read the secret.

## Checklist
- [x] `scraper/sqs_publisher.py` (`SqsRecordPublisher`), `scraper/lambda_handler.py`, `scraper/main.py` with `SCRAPER_OUTPUT` switch
- [x] `processing/postgres_quote_store.py` (`PostgresQuoteStore`), `processing/sqs_consumer_handler.py`
- [x] `db/connection.py` (cached connection, TLS against bundled RDS CA, reconnect-once), `db/schema.sql`
- [x] `quotes_api/postgres_*_repository.py`, `quotes_api/repositories.py` (`DATA_BACKEND` switch)
- [x] Frontend: "Run scrape now" button + relabelled pipeline metrics
- [x] `deploy/ec2-ubuntu/` install script + systemd service/timer
- [x] Local verification: py_compile, stubbed smoke tests, live scrape → fake SQS (100 quotes → 4 messages), `npm run build`
- [ ] AWS: SQS + DLQ
- [ ] AWS: security groups + RDS
- [ ] AWS: Ubuntu EC2 + schema migration
- [ ] AWS: `quotes-consumer` + SQS trigger
- [ ] AWS: `quotes-scraper` + `POST /scrape` route
- [ ] AWS: `quotes-api`/`quotes-status` into VPC with new code
- [ ] AWS: remove the S3 trigger from `quotes-processing`; retire the Windows EC2
- [ ] Frontend redeploy to `sadi-quotes-frontend`
- [ ] End-to-end verification (bottom of this doc)

---

## Deployment commands

All commands are single-line PowerShell + AWS CLI, region `eu-north-1`.
Replace `ACCOUNT_ID`, `<VPC_ID>`, `<SUBNET_A>`, `<SUBNET_B>`, `<SUBNET_C>`, `<MY_IP>`, and the `sg-…` ids printed along the way.
Policy JSON files go in the repo root, where `/*.json` is git-ignored (same convention as phases 1–5).

### 0. Look up the default VPC and its subnets
```powershell
aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region eu-north-1
aws ec2 describe-subnets --filters Name=vpc-id,Values=<VPC_ID> --query "Subnets[].SubnetId" --output text --region eu-north-1
```

### 1. SQS queue + DLQ
```powershell
aws sqs create-queue --queue-name quotes-ingest-dlq --attributes MessageRetentionPeriod=1209600 --region eu-north-1
```
`redrive.json`:
```json
{"VisibilityTimeout":"180","RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:eu-north-1:ACCOUNT_ID:quotes-ingest-dlq\",\"maxReceiveCount\":\"3\"}"}
```
```powershell
aws sqs create-queue --queue-name quotes-ingest-queue --attributes file://redrive.json --region eu-north-1
aws sqs get-queue-url --queue-name quotes-ingest-queue --region eu-north-1
```

### 2. Security groups
```powershell
aws ec2 create-security-group --group-name quotes-lambda-sg --description "VPC Lambdas that talk to RDS" --vpc-id <VPC_ID> --region eu-north-1 --query GroupId --output text
aws ec2 create-security-group --group-name quotes-ec2-sg --description "Ubuntu scraper / DB admin host" --vpc-id <VPC_ID> --region eu-north-1 --query GroupId --output text
aws ec2 create-security-group --group-name quotes-rds-sg --description "quotes-db Postgres" --vpc-id <VPC_ID> --region eu-north-1 --query GroupId --output text
aws ec2 authorize-security-group-ingress --group-id <EC2_SG> --protocol tcp --port 22 --cidr <MY_IP>/32 --region eu-north-1
aws ec2 authorize-security-group-ingress --group-id <RDS_SG> --protocol tcp --port 5432 --source-group <LAMBDA_SG> --region eu-north-1
aws ec2 authorize-security-group-ingress --group-id <RDS_SG> --protocol tcp --port 5432 --source-group <EC2_SG> --region eu-north-1
```

### 3. RDS PostgreSQL
Choose a strong password and keep it out of shell history where you can. `--manage-master-user-password` is not used, because the Lambdas read the password from an env var (see IAM).
```powershell
aws rds create-db-instance --db-instance-identifier quotes-db --engine postgres --engine-version 16 --db-instance-class db.t4g.micro --allocated-storage 20 --storage-type gp3 --master-username quotes_admin --master-user-password "<DB_PASSWORD>" --db-name quotes --vpc-security-group-ids <RDS_SG> --no-publicly-accessible --backup-retention-period 1 --no-multi-az --region eu-north-1
aws rds wait db-instance-available --db-instance-identifier quotes-db --region eu-north-1
aws rds describe-db-instances --db-instance-identifier quotes-db --query "DBInstances[0].Endpoint.Address" --output text --region eu-north-1
```

### 4. Ubuntu EC2 (scraper + DB admin host)
`ec2-trust.json`:
```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}
```
`sqs-send.json`:
```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"sqs:SendMessage","Resource":"arn:aws:sqs:eu-north-1:ACCOUNT_ID:quotes-ingest-queue"}]}
```
```powershell
aws iam create-role --role-name quotes-ec2-scraper-role --assume-role-policy-document file://ec2-trust.json
aws iam put-role-policy --role-name quotes-ec2-scraper-role --policy-name sqs-send --policy-document file://sqs-send.json
aws iam create-instance-profile --instance-profile-name quotes-ec2-scraper-profile
aws iam add-role-to-instance-profile --instance-profile-name quotes-ec2-scraper-profile --role-name quotes-ec2-scraper-role
aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text --region eu-north-1
aws ec2 run-instances --image-id <UBUNTU_AMI> --instance-type t3.micro --key-name <KEY_PAIR> --security-group-ids <EC2_SG> --subnet-id <SUBNET_A> --associate-public-ip-address --iam-instance-profile Name=quotes-ec2-scraper-profile --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=quotes-scraper-ubuntu}]" --region eu-north-1
```

#### 4a. Ubuntu install guide (run on the instance)
1. **Connect**: `ssh -i <KEY_PAIR>.pem ubuntu@<PUBLIC_IP>`. On Windows, fix the key file's permissions first with `icacls <KEY_PAIR>.pem /inheritance:r /grant:r "$env:USERNAME:R"`.
2. **Install**: this creates the `quotes` user, clones the repo to `/opt/quotes-erp`, builds `.venv`, installs `postgresql-client`, and installs the systemd units. Pass `main` instead once the branch is merged.
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Xaifullah/aws-quotes-erp/feature/sqs-rds-pipeline/deploy/ec2-ubuntu/install.sh -o install.sh && sudo bash install.sh feature/sqs-rds-pipeline
   ```
3. **Configure**: `sudo nano /etc/quotes-scraper.env` and set `QUEUE_URL` to the value from step 1. Keep `SCRAPER_OUTPUT=sqs`.
4. **Check the role**: `sudo apt-get install -y awscli` is optional. Otherwise run `sudo -u quotes /opt/quotes-erp/.venv/bin/python -c "import boto3;print(boto3.client('sts').get_caller_identity()['Arn'])"`. It should print `…assumed-role/quotes-ec2-scraper-role/…`.
5. **Create the schema** (this box is the only host besides the Lambdas that can reach RDS):
   ```bash
   PGPASSWORD='<DB_PASSWORD>' psql "host=<RDS_ENDPOINT> dbname=quotes user=quotes_admin sslmode=require" -f /opt/quotes-erp/db/schema.sql
   ```
6. **Run once by hand** (do this after section 5, so the consumer exists to drain the queue):
   ```bash
   sudo systemctl start quotes-scraper.service && journalctl -u quotes-scraper -n 30 --no-pager
   ```
   Expect `Run <uuid>: published 100 records in 4 SQS messages`.
7. **Schedule**: `sudo systemctl enable --now quotes-scraper.timer`, then check with `systemctl list-timers quotes-scraper.timer`. It runs at 00:00/06:00/12:00/18:00 UTC; missed runs fire on boot.
8. **Update later**: run `sudo bash /opt/quotes-erp/deploy/ec2-ubuntu/install.sh <branch>`. It's idempotent and keeps `/etc/quotes-scraper.env`.
9. **Troubleshooting**:
   - `AccessDenied` on SendMessage → the instance profile isn't attached, or the queue ARN in `sqs-send.json` is wrong.
   - `NoRegionError` → `AWS_DEFAULT_REGION` is missing from the env file.
   - `$'\r': command not found` → the script was checked out with CRLF. `.gitattributes` forces LF, so re-clone.
   - `psql` hangs → `quotes-rds-sg` is missing the ingress rule from `quotes-ec2-sg`.
10. **Retire the Windows instance**: once two timer runs show up in `journalctl`, run `aws ec2 stop-instances --instance-ids <WINDOWS_INSTANCE_ID> --region eu-north-1` and terminate it a week later.

### 5. Consumer Lambda (`quotes-consumer`)
Package it from the repo root. pg8000 and its deps are pure Python, so building on Windows is fine.
```powershell
Remove-Item -Recurse -Force build-consumer -ErrorAction SilentlyContinue; pip install -r processing/requirements.txt -t build-consumer; Copy-Item -Recurse processing, db build-consumer; Compress-Archive -Path build-consumer\* -DestinationPath consumer.zip -Force
```
`lambda-trust.json`:
```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
```
`sqs-consume.json`:
```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes","sqs:ChangeMessageVisibility"],"Resource":"arn:aws:sqs:eu-north-1:ACCOUNT_ID:quotes-ingest-queue"}]}
```
```powershell
aws iam create-role --role-name quotes-consumer-lambda-role --assume-role-policy-document file://lambda-trust.json
aws iam attach-role-policy --role-name quotes-consumer-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
aws iam put-role-policy --role-name quotes-consumer-lambda-role --policy-name sqs-consume --policy-document file://sqs-consume.json
aws lambda create-function --function-name quotes-consumer --runtime python3.12 --handler processing.sqs_consumer_handler.handler --role arn:aws:iam::ACCOUNT_ID:role/quotes-consumer-lambda-role --zip-file fileb://consumer.zip --timeout 30 --memory-size 256 --vpc-config SubnetIds=<SUBNET_A>,<SUBNET_B>,<SUBNET_C>,SecurityGroupIds=<LAMBDA_SG> --environment "Variables={DB_HOST=<RDS_ENDPOINT>,DB_NAME=quotes,DB_USER=quotes_admin,DB_PASSWORD=<DB_PASSWORD>}" --region eu-north-1
aws lambda get-function-configuration --function-name quotes-consumer --query "{Handler:Handler,Role:Role,Vpc:VpcConfig.SubnetIds}" --region eu-north-1
aws lambda create-event-source-mapping --function-name quotes-consumer --event-source-arn arn:aws:sqs:eu-north-1:ACCOUNT_ID:quotes-ingest-queue --batch-size 10 --function-response-types ReportBatchItemFailures --region eu-north-1
```
No NAT or VPC endpoint is needed: the event source mapping polls and deletes messages from the Lambda service side. The function itself only talks to RDS.

### 6. Scraper Lambda (`quotes-scraper`) + `POST /scrape`
```powershell
Remove-Item -Recurse -Force build-scraper -ErrorAction SilentlyContinue; pip install requests beautifulsoup4 -t build-scraper; Copy-Item -Recurse scraper build-scraper; Compress-Archive -Path build-scraper\* -DestinationPath scraper.zip -Force
aws iam create-role --role-name quotes-scraper-lambda-role --assume-role-policy-document file://lambda-trust.json
aws iam attach-role-policy --role-name quotes-scraper-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name quotes-scraper-lambda-role --policy-name sqs-send --policy-document file://sqs-send.json
aws lambda create-function --function-name quotes-scraper --runtime python3.12 --handler scraper.lambda_handler.handler --role arn:aws:iam::ACCOUNT_ID:role/quotes-scraper-lambda-role --zip-file fileb://scraper.zip --timeout 29 --memory-size 256 --environment "Variables={QUEUE_URL=https://sqs.eu-north-1.amazonaws.com/ACCOUNT_ID/quotes-ingest-queue}" --region eu-north-1
aws lambda get-function-configuration --function-name quotes-scraper --query "{Handler:Handler,Role:Role}" --region eu-north-1
aws apigatewayv2 create-integration --api-id gfoyhnaxh3 --integration-type AWS_PROXY --integration-uri arn:aws:lambda:eu-north-1:ACCOUNT_ID:function:quotes-scraper --payload-format-version 2.0 --timeout-in-millis 29000 --region eu-north-1 --query "IntegrationId" --output text
aws apigatewayv2 create-route --api-id gfoyhnaxh3 --route-key "POST /scrape" --target integrations/<INTEGRATION_ID> --authorization-type CUSTOM --authorizer-id 146rv0 --region eu-north-1
aws lambda add-permission --function-name quotes-scraper --statement-id apigw-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:eu-north-1:ACCOUNT_ID:gfoyhnaxh3/*/*/scrape" --region eu-north-1
aws apigatewayv2 get-api --api-id gfoyhnaxh3 --query CorsConfiguration --region eu-north-1
```
If `AllowMethods` in the last output doesn't include `POST`, re-run the phase-4 `update-api --cors-configuration` command with `POST` added. Keep the existing `AllowOrigins`.

### 7. Point `quotes-api` / `quotes-status` at RDS
```powershell
Remove-Item -Recurse -Force build-api -ErrorAction SilentlyContinue; pip install -r quotes_api/requirements.txt -t build-api; Copy-Item -Recurse quotes_api, db build-api; Compress-Archive -Path build-api\* -DestinationPath quotes-api.zip -Force
aws iam attach-role-policy --role-name quotes-api-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
aws iam attach-role-policy --role-name quotes-status-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
aws lambda update-function-code --function-name quotes-api --zip-file fileb://quotes-api.zip --region eu-north-1
aws lambda wait function-updated --function-name quotes-api --region eu-north-1
aws lambda update-function-configuration --function-name quotes-api --vpc-config SubnetIds=<SUBNET_A>,<SUBNET_B>,<SUBNET_C>,SecurityGroupIds=<LAMBDA_SG> --environment "Variables={DATA_BACKEND=postgres,QUOTES_BUCKET=sadi-quotes-bucket,DB_HOST=<RDS_ENDPOINT>,DB_NAME=quotes,DB_USER=quotes_admin,DB_PASSWORD=<DB_PASSWORD>}" --region eu-north-1
aws lambda update-function-code --function-name quotes-status --zip-file fileb://quotes-api.zip --region eu-north-1
aws lambda wait function-updated --function-name quotes-status --region eu-north-1
aws lambda update-function-configuration --function-name quotes-status --vpc-config SubnetIds=<SUBNET_A>,<SUBNET_B>,<SUBNET_C>,SecurityGroupIds=<LAMBDA_SG> --environment "Variables={DATA_BACKEND=postgres,QUOTES_BUCKET=sadi-quotes-bucket,DB_HOST=<RDS_ENDPOINT>,DB_NAME=quotes,DB_USER=quotes_admin,DB_PASSWORD=<DB_PASSWORD>}" --region eu-north-1
aws lambda get-function-configuration --function-name quotes-api --query "{Handler:Handler,Role:Role,Vpc:VpcConfig.SubnetIds}" --region eu-north-1
aws lambda get-function-configuration --function-name quotes-status --query "{Handler:Handler,Role:Role,Vpc:VpcConfig.SubnetIds}" --region eu-north-1
```
Handlers stay `quotes_api.handler.handler` / `quotes_api.status_handler.handler`.

### 8. Retire the old S3 trigger
```powershell
aws s3api get-bucket-notification-configuration --bucket sadi-quotes-bucket
aws s3api put-bucket-notification-configuration --bucket sadi-quotes-bucket --notification-configuration "{}"
```
Save the output of the first command to `s3-notification-backup.json` before running the second. That file is the rollback.

### 9. Frontend
```powershell
cd frontend; npm run build; aws s3 sync dist s3://sadi-quotes-frontend --delete; cd ..
```

---

## End-to-end verification
1. Get a token: `curl.exe -s -X POST <API_URL>/login -H "Content-Type: application/json" --data-binary "@login.json"`
2. Trigger a scrape: `curl.exe -s -X POST <API_URL>/scrape -H "Authorization: Bearer <TOKEN>"` → `202 {"run_id": …, "published": 100, "messages": 4}`
3. The queue drains: `aws sqs get-queue-attributes --queue-url <QUEUE_URL> --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible --region eu-north-1` → both `0` within seconds
4. The DLQ is empty: the same command against `quotes-ingest-dlq` → `0`
5. Consumer logs: `aws logs tail /aws/lambda/quotes-consumer --since 10m --region eu-north-1` → `upserted 25 quotes` ×4
6. DB on the EC2 box: `psql … -c "SELECT count(*) FROM quotes; SELECT * FROM scrape_runs ORDER BY started_at DESC LIMIT 3;"` → `100`
7. API: `curl.exe -s <API_URL>/status -H "Authorization: Bearer <TOKEN>"` → `processed_count: 100`
8. Browser: the dashboard shows 100 quotes. "Run scrape now" queues a run, and the "Scrape runs" count goes up.
9. EC2 path: `sudo systemctl start quotes-scraper.service` → a second `scrape_runs` row with `source = 'ec2'`. The quote count stays 100 (idempotent upsert).

## Rollback
Each step can be undone on its own:
- Read side back to S3: set `DATA_BACKEND=s3` on `quotes-api` and `quotes-status`. They can stay in the VPC, but S3 access then needs a free S3 **gateway** endpoint. The simpler option is to also remove the VPC config with `--vpc-config SubnetIds=[],SecurityGroupIds=[]`.
- Ingestion back to S3: restore `s3-notification-backup.json` with `put-bucket-notification-configuration`, and set `SCRAPER_OUTPUT=s3` + `RAW_BUCKET` in `/etc/quotes-scraper.env`. The EC2 role then also needs `s3:PutObject` on `raw/*`.
- Delete the `POST /scrape` route. The rest of the API is untouched.

## Activity Log
- 2026-10-14: Implemented phase 6 code on `feature/sqs-rds-pipeline`:
  - publisher (`SqsRecordPublisher`, Lambda + EC2 entrypoints)
  - consumer (`PostgresQuoteStore`, partial-batch-failure handler)
  - `db/` (TLS against the bundled RDS CA, reconnect-once helper, idempotent schema)
  - Postgres repositories behind a `DATA_BACKEND` switch
  - "Run scrape now" in the dashboard
  - Ubuntu EC2 install script + systemd timer, and `.gitattributes` forcing LF for `deploy/` and `*.sh`

  Verified locally:
  - py_compile
  - stubbed smoke tests (batching ≤10/call with retry; 202/502 from the scraper handler; consumer commits good messages and reports malformed ones as `batchItemFailures`; repository JSON matches the S3 contract; reconnect-once)
  - a live scrape into a fake SQS client (100 quotes → 4 messages, largest body 6.6 KB)
  - `npm run build`

  **Next**: user runs deployment sections 0–9 and the end-to-end checks.
