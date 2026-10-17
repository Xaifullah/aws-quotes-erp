# Console setup guide — new AWS account, Ubuntu scraper server, full pipeline

Builds the Phase 6 architecture from scratch in a **new** AWS account, using the
**AWS Management Console** only (no AWS CLI). The one exception is building the
Lambda zips and the frontend on your PC, which a console can't do.

```
Ubuntu EC2 (systemd timer) ──┐
API Gateway POST /scrape ──► Lambda quotes-scraper ──┤  publishers
                                                     ▼
                         SQS quotes-ingest-queue ──► quotes-ingest-dlq
                                                     ▼
                         Lambda quotes-consumer (in VPC)        consumer
                                                     ▼
                         RDS PostgreSQL quotes-db (private)
                                                     ▼
          Lambdas quotes-api / quotes-status (in VPC) + auth Lambdas
                                                     ▼
                  API Gateway HTTP API ──► React dashboard (S3 website)
```

A new account has none of the old resources: no Users table, no JWT secret, no
auth Lambdas, no API, no frontend bucket. This guide therefore creates
**everything**, in this order:

| Part | What | Time |
|---|---|---|
| 0 | Pick region, note IDs, build zips on your PC | 10 min |
| 1 | **Ubuntu scraper server** (SQS + IAM role + install) | 20 min |
| 2 | Database: security groups + RDS + schema | 20 min (RDS takes ~10 to start) |
| 3 | Auth: DynamoDB `Users` + JWT secret | 5 min |
| 4 | IAM roles for the Lambdas | 10 min |
| 5 | 7 Lambda functions + SQS trigger | 25 min |
| 6 | API Gateway HTTP API (routes, authorizer, CORS) | 15 min |
| 7 | Frontend on S3 static hosting | 10 min |
| 8 | End-to-end test + troubleshooting | 10 min |

Placeholders used below:
- `<REGION>`: your EC2's region, e.g. `eu-north-1`.
- `<ACCOUNT_ID>`: the 12 digits shown under your account name, top-right of the console.

Keep a notepad open: you'll copy several values (queue URL, RDS endpoint, API URL) between steps.

---

## Part 0 — Before you start

### 0.1 Region and VPC
1. In the console's top-right region picker, select **the region your Ubuntu EC2 is in**. Every resource in this guide must be in that same region.
2. Open **EC2 → Instances → (your instance)**. On the **Details** tab, note:
   - **VPC ID** (in a new account this is the *default VPC*)
   - **Subnet ID**
   - the **security group** name under the **Security** tab (e.g. `launch-wizard-1`)

Everything below goes in this same VPC.

### 0.2 Build the Lambda zips (on your Windows PC, in the repo)
```powershell
git fetch origin; git checkout feature/sqs-rds-pipeline; git pull
powershell -ExecutionPolicy Bypass -File deploy\build-lambdas.ps1
```
This creates `dist-lambda\` with 4 zips:

| Zip | Used by |
|---|---|
| `auth.zip` | `quotes-register`, `quotes-login`, `quotes-authorizer` |
| `scraper.zip` | `quotes-scraper` |
| `consumer.zip` | `quotes-consumer` |
| `quotes-api.zip` | `quotes-api`, `quotes-status` |

The dependencies are built for **Linux x86_64 / Python 3.12**. Every Lambda below must use runtime **Python 3.12** and architecture **x86_64**.

---

## Part 1 — Ubuntu scraper server

The scraper on the EC2 publishes quotes into SQS on a timer. It needs a queue to publish to, and an IAM role that allows it.

### 1.1 Create the SQS queues (console: **SQS**)
1. **Create queue** for the dead-letter queue:
   - Type **Standard**
   - Name `quotes-ingest-dlq`
   - **Message retention period** `14 days`
   - Click **Create queue**.
2. **Create queue** again for the main queue:
   - Type **Standard**
   - Name `quotes-ingest-queue`
   - **Visibility timeout** `3 minutes` (must be at least 6× the consumer Lambda's 30s timeout)
   - **Dead-letter queue** section: **Enabled**, choose `quotes-ingest-dlq`, **Maximum receives** `3`
   - Click **Create queue**.
3. On the queue's page, copy the **URL** (`https://sqs.<REGION>.amazonaws.com/<ACCOUNT_ID>/quotes-ingest-queue`) and the **ARN**.

### 1.2 IAM role for the EC2 (console: **IAM → Roles → Create role**)
1. Trusted entity:
   - **AWS service**
   - Use case **EC2** → **Next**.
2. Skip the permissions list for now → **Next**.
3. Name it `quotes-ec2-scraper-role` → **Create role**.
4. Open the role and add the SQS permission:
   - **Add permissions → Create inline policy → JSON**
   - Paste the policy below
   - **Next**
   - Name it `sqs-send` → **Create policy**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": "sqs:SendMessage",
       "Resource": "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:quotes-ingest-queue"
     }]
   }
   ```
5. Attach the role to the instance: **EC2 → Instances → (your instance) → Actions → Security → Modify IAM role** → choose `quotes-ec2-scraper-role` → **Update IAM role**.

### 1.3 Install the scraper (on the Ubuntu server)
1. Connect to the instance:
   - **EC2 → (instance) → Connect → EC2 Instance Connect → Connect** (opens a browser terminal)
   - or `ssh -i <key>.pem ubuntu@<public-ip>`
2. Run the installer:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Xaifullah/aws-quotes-erp/feature/sqs-rds-pipeline/deploy/ec2-ubuntu/install.sh -o install.sh
   sudo bash install.sh feature/sqs-rds-pipeline
   ```
   It installs Python, git and `postgresql-client`, creates a `quotes` service user, clones the repo to `/opt/quotes-erp`, builds a virtualenv, and installs the systemd service + timer.
3. Configure:
   ```bash
   sudo nano /etc/quotes-scraper.env
   ```
   Set these two lines (Ctrl+O, Enter, Ctrl+X to save):
   ```
   QUEUE_URL=https://sqs.<REGION>.amazonaws.com/<ACCOUNT_ID>/quotes-ingest-queue
   AWS_DEFAULT_REGION=<REGION>
   ```
4. Check that the instance sees its IAM role:
   ```bash
   sudo -u quotes /opt/quotes-erp/.venv/bin/python -c "import boto3;print(boto3.client('sts').get_caller_identity()['Arn'])"
   ```
   It should print `arn:aws:sts::<ACCOUNT_ID>:assumed-role/quotes-ec2-scraper-role/i-…`. If you get `NoCredentialsError`, wait 30 seconds after step 1.2.5 and retry.
5. Run the scraper once:
   ```bash
   sudo systemctl start quotes-scraper.service
   journalctl -u quotes-scraper -n 20 --no-pager
   ```
   Expect `Run <uuid>: published 100 records in 4 SQS messages`.
6. Confirm the messages arrived: in **SQS → Queues**, the list shows **Messages available = 4** for `quotes-ingest-queue`.
   > ⚠️ Don't click **Send and receive messages → Poll for messages** to look at them. Every poll counts as a receive, and after 3 receives SQS moves the messages to the DLQ. They'll sit in the queue safely (4 days by default) until the consumer Lambda from Part 5 drains them.
7. Turn on the schedule:
   ```bash
   sudo systemctl enable --now quotes-scraper.timer
   systemctl list-timers quotes-scraper.timer
   ```
   The scraper now runs at 00:00, 06:00, 12:00 and 18:00 UTC. A run missed while the instance was stopped fires at boot.

**Updating the server later**: `sudo bash /opt/quotes-erp/deploy/ec2-ubuntu/install.sh <branch>`. It's safe to re-run, and it keeps your env file.

---

## Part 2 — Database (RDS PostgreSQL)

### 2.1 Security groups (console: **EC2 → Security Groups → Create security group**)
Create both in **your EC2's VPC**.

1. `quotes-lambda-sg`:
   - description "Lambdas that talk to RDS"
   - **no inbound rules**
   - leave the default outbound rule
   - **Create**
2. `quotes-rds-sg`:
   - description "quotes-db Postgres"
   - Inbound rule 1: Type **PostgreSQL** (5432), Source **Custom** → pick `quotes-lambda-sg`
   - Inbound rule 2: Type **PostgreSQL** (5432), Source **Custom** → pick **your EC2's security group** (from 0.1)
   - **Create**

### 2.2 Create the database (console: **RDS → Databases → Create database**)

| Setting | Value |
|---|---|
| Creation method | **Standard create** |
| Engine | **PostgreSQL**, version **16.x** (latest 16) |
| Template | **Free tier** (or **Sandbox** / **Dev/Test** if Free tier isn't shown) |
| DB instance identifier | `quotes-db` |
| Master username | `quotes_admin` |
| Credentials management | **Self managed**, type a strong password (no `/`, `@`, `"` or spaces). **Save it** |
| Instance class | `db.t4g.micro` (or `db.t3.micro`) |
| Storage | gp3, **20 GiB**, untick *Enable storage autoscaling* |
| Compute resource | **Don't connect to an EC2 compute resource** (the security groups handle it) |
| VPC | **your EC2's VPC** |
| DB subnet group | default |
| Public access | **No** |
| VPC security group | **Choose existing** → `quotes-rds-sg` (remove `default`) |
| Availability Zone | No preference |
| Monitoring | untick Performance Insights / Enhanced monitoring (saves cost) |
| **Additional configuration → Initial database name** | **`quotes`** ← don't skip this |
| Backup retention | 1 day |

Click **Create database**. It takes about 10 minutes. When the status is **Available**, open it and copy the **Endpoint** from **Connectivity & security** (e.g. `quotes-db.xxxx.<REGION>.rds.amazonaws.com`).

### 2.3 Create the tables (on the Ubuntu server)
```bash
psql "host=<RDS_ENDPOINT> port=5432 dbname=quotes user=quotes_admin sslmode=require" -f /opt/quotes-erp/db/schema.sql
```
Enter the password when asked. Expected output: `CREATE TABLE` ×2, `CREATE INDEX` ×3.
- If the command **hangs**: the `quotes-rds-sg` inbound rule for the EC2 security group is missing, or RDS is in a different VPC.
- If you get `database "quotes" does not exist`: you skipped *Initial database name*. Fix it by connecting with `dbname=postgres`, running `CREATE DATABASE quotes;`, and repeating this step.

---

## Part 3 — Auth resources

### 3.1 DynamoDB users table (console: **DynamoDB → Tables → Create table**)
1. Set the table:
   - Table name `Users`
   - Partition key `username` (**String**)
   - No sort key
2. **Table settings → Customize settings**:
   - Capacity mode **Provisioned**
   - Read **1** / Write **1**
   - **Auto scaling off** for both (stays in the always-free tier)
3. Click **Create table**.

### 3.2 JWT signing secret (console: **Systems Manager → Parameter Store → Create parameter**)
1. Generate a random secret on the Ubuntu server and copy the output:
   ```bash
   openssl rand -base64 48
   ```
2. Create the parameter:
   - Name `/quotes-app/jwt-secret`
   - Tier **Standard**
   - Type **SecureString**
   - KMS key source **My current account**, key `alias/aws/ssm`
   - Value: paste the secret
   - Click **Create parameter**.

---

## Part 4 — IAM roles for the Lambdas

Create each role in **IAM → Roles → Create role**:
- Trusted entity **AWS service**, use case **Lambda**
- Attach the managed policy listed
- Name it as listed

Then open the role → **Add permissions → Create inline policy → JSON** for the inline part.

| Role name | Managed policy to attach | Inline policy |
|---|---|---|
| `quotes-auth-lambda-role` | `AWSLambdaBasicExecutionRole` | A (DynamoDB + secret) |
| `quotes-authorizer-lambda-role` | `AWSLambdaBasicExecutionRole` | B (secret only) |
| `quotes-scraper-lambda-role` | `AWSLambdaBasicExecutionRole` | C (send to SQS) |
| `quotes-consumer-lambda-role` | `AWSLambdaVPCAccessExecutionRole` | D (consume SQS) |
| `quotes-read-lambda-role` | `AWSLambdaVPCAccessExecutionRole` | none |

`AWSLambdaVPCAccessExecutionRole` already includes CloudWatch Logs permissions, so the VPC roles don't need the basic policy as well.

**A — `auth-access`**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["dynamodb:GetItem", "dynamodb:PutItem"],
      "Resource": "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/Users" },
    { "Effect": "Allow", "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:<REGION>:<ACCOUNT_ID>:parameter/quotes-app/jwt-secret" }
  ]
}
```
**B — `jwt-secret-read`**
```json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow", "Action": "ssm:GetParameter",
    "Resource": "arn:aws:ssm:<REGION>:<ACCOUNT_ID>:parameter/quotes-app/jwt-secret" }]
}
```
**C — `sqs-send`**
```json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow", "Action": "sqs:SendMessage",
    "Resource": "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:quotes-ingest-queue" }]
}
```
**D — `sqs-consume`**
```json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow",
    "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"],
    "Resource": "arn:aws:sqs:<REGION>:<ACCOUNT_ID>:quotes-ingest-queue" }]
}
```

---

## Part 5 — Lambda functions

### 5.1 How to create each function (repeat for every row in 5.2)
1. **Lambda → Functions → Create function → Author from scratch**:
   - Function name: from the table
   - Runtime **Python 3.12**
   - Architecture **x86_64**
   - **Change default execution role → Use an existing role** → the role from the table
   - **Create function**
2. **Code** tab: **Upload from → .zip file** → choose the zip from `dist-lambda\` → **Save**.
3. **Code** tab, scroll down to **Runtime settings → Edit** → set **Handler** exactly as in the table → **Save**.
   > This step is the most common mistake in this project. The console default `lambda_function.lambda_handler` gives `Unable to import module 'lambda_function'`.
4. **Configuration → General configuration → Edit**: set the timeout and memory from the table.
5. **Configuration → Environment variables → Edit**: add the variables from the table.
6. VPC functions only: **Configuration → VPC → Edit**:
   - VPC: **your EC2's VPC**
   - Subnets: **select all** subnets
   - Security group: **`quotes-lambda-sg`** only
   - Save. This takes 1–2 minutes.

### 5.2 The functions

| Function | Zip | Handler | Role | Timeout / Memory | VPC |
|---|---|---|---|---|---|
| `quotes-register` | auth.zip | `auth.register_handler.handler` | quotes-auth-lambda-role | 10 s / 256 MB | no |
| `quotes-login` | auth.zip | `auth.login_handler.handler` | quotes-auth-lambda-role | 10 s / 256 MB | no |
| `quotes-authorizer` | auth.zip | `auth.authorizer_handler.handler` | quotes-authorizer-lambda-role | 10 s / 128 MB | no |
| `quotes-scraper` | scraper.zip | `scraper.lambda_handler.handler` | quotes-scraper-lambda-role | 29 s / 256 MB | **no** (needs internet) |
| `quotes-consumer` | consumer.zip | `processing.sqs_consumer_handler.handler` | quotes-consumer-lambda-role | 30 s / 256 MB | **yes** |
| `quotes-api` | quotes-api.zip | `quotes_api.handler.handler` | quotes-read-lambda-role | 15 s / 256 MB | **yes** |
| `quotes-status` | quotes-api.zip | `quotes_api.status_handler.handler` | quotes-read-lambda-role | 15 s / 128 MB | **yes** |

Environment variables:

| Function(s) | Variables |
|---|---|
| `quotes-register` | `USERS_TABLE=Users` |
| `quotes-login` | `USERS_TABLE=Users`, `JWT_SECRET_PARAMETER=/quotes-app/jwt-secret` |
| `quotes-authorizer` | `JWT_SECRET_PARAMETER=/quotes-app/jwt-secret` |
| `quotes-scraper` | `QUEUE_URL=<queue URL from 1.1>` |
| `quotes-consumer`, `quotes-api`, `quotes-status` | `DB_HOST=<RDS endpoint>`, `DB_NAME=quotes`, `DB_USER=quotes_admin`, `DB_PASSWORD=<your RDS password>` |
| `quotes-api`, `quotes-status` | also `DATA_BACKEND=postgres` |

### 5.3 Connect the consumer to SQS (this drains the 4 messages from Part 1)
1. **Lambda → quotes-consumer → Add trigger** → source **SQS**.
2. SQS queue `quotes-ingest-queue`, **Batch size** `10`.
3. **Additional settings**: tick **Report batch item failures**.
4. **Add**.

Within a minute, check:
- **SQS → quotes-ingest-queue** shows **Messages available = 0**, and `quotes-ingest-dlq` shows 0.
- **Lambda → quotes-consumer → Monitor → View CloudWatch logs**: the latest log stream has `upserted 25 quotes` four times.

### 5.4 Quick test of each function (optional, **Test** tab)
- `quotes-status`: test event `{}` → `statusCode 200` with `"processed_count": 100`.
- `quotes-api`: test event `{}` → `statusCode 200` with a `quotes` list of 100.

---

## Part 6 — API Gateway HTTP API

### 6.1 Create the API (console: **API Gateway → Create API → HTTP API → Build**)
1. **Integrations → Add integration → Lambda**. Add 5, one per function: `quotes-register`, `quotes-login`, `quotes-api`, `quotes-status`, `quotes-scraper`.
2. API name `quotes-app-api` → **Next**.
3. **Configure routes**:

   | Method | Path | Integration target |
   |---|---|---|
   | POST | `/register` | quotes-register |
   | POST | `/login` | quotes-login |
   | GET | `/quotes` | quotes-api |
   | GET | `/status` | quotes-status |
   | POST | `/scrape` | quotes-scraper |
4. **Stages**: keep `$default` with **Auto-deploy** on → **Next → Create**.
5. Copy the **Invoke URL** (`https://xxxx.execute-api.<REGION>.amazonaws.com`).

The console automatically gives API Gateway permission to invoke each integrated Lambda.

### 6.2 JWT authorizer (protects `/quotes`, `/status` and `/scrape`)
1. Open the authorizer screen: **(your API) → Develop → Authorization → Manage authorizers → Create**.
2. Fill in:

   | Field | Value |
   |---|---|
   | Authorizer type | **Lambda** |
   | Name | `quotes-jwt-authorizer` |
   | Lambda function | `quotes-authorizer` |
   | Payload format version | **2.0** |
   | Response mode | **Simple** |
   | Identity sources | `$request.header.Authorization` |
   | Authorizer caching | **off** |
   | Automatically grant API Gateway permission to invoke your Lambda function | **on** |
3. **Create**.
4. Go to the **Attach authorizers to routes** tab. For **GET /quotes**, **GET /status** and **POST /scrape**: select the route → choose `quotes-jwt-authorizer` → **Attach authorizer**.
5. Leave `/register` and `/login` **without** an authorizer.

### 6.3 CORS (**Develop → CORS → Configure**)

| Field | Value |
|---|---|
| Access-Control-Allow-Origin | `http://localhost:5173` (you'll add the S3 website URL in Part 7) |
| Access-Control-Allow-Headers | `authorization`, `content-type` |
| Access-Control-Allow-Methods | `GET`, `POST`, `OPTIONS` |
| Access-Control-Max-Age | `300` |

**Save**.

---

## Part 7 — Frontend (S3 static website)

### 7.1 Build (on your PC)
1. Create the environment file:
   ```powershell
   cd frontend; Copy-Item .env.example .env
   ```
2. Edit `frontend\.env`:
   ```
   VITE_API_URL=https://xxxx.execute-api.<REGION>.amazonaws.com
   ```
   No trailing slash.
3. Build:
   ```powershell
   npm install; npm run build; cd ..
   ```

### 7.2 Hosting bucket (console: **S3 → Create bucket**)
1. Create the bucket:
   - Name: globally unique, e.g. `<yourname>-quotes-frontend`
   - Region: same as everything else
   - **Untick Block all public access** and tick the acknowledgement
   - **Create bucket**
2. Open the bucket → **Upload**:
   - **Add files** → everything at the top level of `frontend\dist\` (`index.html`, `favicon.svg`, `icons.svg`)
   - **Add folder** → `frontend\dist\assets`
   - **Upload**
3. **Properties → Static website hosting → Edit**:
   - **Enable**
   - Index document `index.html`
   - Error document `index.html`
   - Save
   - Copy the **Bucket website endpoint** (`http://<bucket>.s3-website.<REGION>.amazonaws.com`).
4. **Permissions → Bucket policy → Edit**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{ "Sid": "PublicReadWebsite", "Effect": "Allow", "Principal": "*",
       "Action": "s3:GetObject", "Resource": "arn:aws:s3:::<bucket-name>/*" }]
   }
   ```
5. **API Gateway → (your API) → CORS → Configure**: add the website endpoint from step 3 to **Access-Control-Allow-Origin**. Use no trailing slash and keep `http://` → **Save**.

---

## Part 8 — End-to-end test

1. Open the **bucket website endpoint** in your browser → **Register** a user → **Log in**.
2. The dashboard should show **100 quotes**, and the pipeline panel shows **Scrape runs: 1**. That run is the EC2 test run from Part 1.
3. Click **Run scrape now**:
   - The message reads "Queued 100 quotes in 4 messages".
   - After about 8 seconds, **Scrape runs** goes up to 2.
   - **Quotes in DB** stays 100, because quotes are stored once each (upsert).
4. On the Ubuntu server, check the timer: `systemctl list-timers quotes-scraper.timer` shows the next run time.
5. Optional, from the Ubuntu server, look at the data:
   ```bash
   psql "host=<RDS_ENDPOINT> dbname=quotes user=quotes_admin sslmode=require" -c "SELECT source, started_at, quote_count FROM scrape_runs ORDER BY started_at DESC;"
   ```

### Troubleshooting

| Symptom | Cause → fix |
|---|---|
| `Unable to import module 'lambda_function'` | Handler not changed → step 5.1.3 |
| `invalid ELF header` / `No module named '_bcrypt'` | Function architecture is arm64, or the zip wasn't built with `build-lambdas.ps1` → use x86_64 + rebuild |
| Consumer / quotes-api **times out** | Lambda VPC differs from the RDS VPC, or `quotes-rds-sg` lacks the rule from `quotes-lambda-sg` |
| `password authentication failed` | `DB_PASSWORD` / `DB_USER` env var typo |
| `relation "quotes" does not exist` | Schema not created → Part 2.3 |
| Messages land in `quotes-ingest-dlq` | Read the consumer's CloudWatch logs and fix the cause, then **SQS → quotes-ingest-dlq → Start DLQ redrive** |
| Browser: "Failed to fetch" / CORS error | Website origin missing from API CORS (exact `http://…` string, no trailing slash), or the authorization header isn't allowed |
| `/quotes` returns **401** with a valid login | Authorizer payload isn't **2.0**, or response mode isn't **Simple** |
| `/quotes` returns **500** | Lambda → Monitor → CloudWatch logs, usually DB env vars |
| EC2: `AccessDenied ... sqs:SendMessage` | Role not attached (1.2.5) or wrong ARN in the inline policy |
| EC2: `$'\r': command not found` | install.sh downloaded with Windows line endings → use the `curl` command from 1.3, not a copy-paste |
| Run scrape returns **502** | quotes.toscrape.com unreachable → `quotes-scraper` must **not** be in a VPC |

### Cost notes
- The **RDS** instance is the main cost. Covered by the free tier/credits on a new account; otherwise about $13–16/month.
- To pause it: **RDS → quotes-db → Actions → Stop temporarily**. It restarts by itself after 7 days.
- SQS, Lambda and DynamoDB at this volume are within the always-free tiers.
