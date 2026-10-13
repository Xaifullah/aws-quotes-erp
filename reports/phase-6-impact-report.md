# Phase 6 Impact Report — API Gateway scraper → SQS → RDS

**Branch**: `feature/sqs-rds-pipeline` (based on `main` @ `ae1cd12`)
**Date**: 2026-10-14
**Scope**: code, docs, and deploy commands. The AWS resources are not created yet; the steps are in [`phases/phase-6-sqs-rds-pipeline.md`](../phases/phase-6-sqs-rds-pipeline.md).

## 1. Summary

| Dimension | Impact | Notes |
|---|---|---|
| Architecture | **High** | Batch S3 file pipeline is replaced by an event-driven queue + relational DB |
| Backend code | **Medium** | 410 lines added, 19 changed across 17 files. Existing classes are reused, not rewritten |
| API contract | **Low** | `/quotes` and `/status` keep the same JSON shape. One new route, `POST /scrape` |
| Frontend | **Low** | 4 files, +88/−10: one new button, two relabelled metrics |
| Auth (`auth/`, DynamoDB, SSM) | **None** | No file touched, no resource changed |
| AWS footprint | **High** | +1 RDS, +2 SQS, +2 Lambdas, +3 SGs, +1 EC2 (Ubuntu); −1 EC2 (Windows); 2 Lambdas move into the VPC |
| Monthly cost | **Up** | RDS is the main new cost (see §7) |
| Data correctness | **Better** | Fixes the duplicate quotes that build up with every scrape (see §8) |
| Rollback | **Easy** | One env var per component; legacy code paths kept |

## 2. Architecture: before → after

**Before (phases 1–5)**
```
Windows EC2 (Task Scheduler) → S3 raw/*.json
  → S3 event → Lambda quotes-processing → S3 processed/*.json
    → Lambda quotes-api (lists + downloads EVERY processed file per cache miss)
      → API Gateway → React dashboard
```

**After (phase 6)**
```
API Gateway POST /scrape → Lambda quotes-scraper ┐
Ubuntu EC2 systemd timer → scraper.main ─────────┤ publishers
                                                 ▼
                      SQS quotes-ingest-queue ──► DLQ (after 3 failures)
                                                 ▼
                      Lambda quotes-consumer (QuoteCleaner + upsert)
                                                 ▼
                      RDS PostgreSQL: quotes, scrape_runs
                                                 ▼
                      Lambda quotes-api / quotes-status (in VPC)
                                                 ▼
                      API Gateway → React dashboard
```

The diagram's components map to the code as follows:

| Diagram | Implemented as |
|---|---|
| API Gateway (Scraper Service) | `POST /scrape` on HTTP API `gfoyhnaxh3`, protected by the existing JWT authorizer |
| Lambda Function | `quotes-scraper` → `scraper/lambda_handler.py` |
| SQS | `quotes-ingest-queue` + `quotes-ingest-dlq` |
| Code (Publisher) | `SqsRecordPublisher` (`scraper/sqs_publisher.py`), used by both the Lambda and the EC2 |
| Code (Consumer) | `quotes-consumer` → `processing/sqs_consumer_handler.py` + `PostgresQuoteStore` |
| Database | RDS PostgreSQL `quotes-db` (`db/schema.sql`) |
| Vertical Container | Existing React dashboard, served through `quotes-api`/`quotes-status` |

## 3. File-level change inventory

### Added (20)
| Area | Files | Lines |
|---|---|---|
| Publisher | `scraper/sqs_publisher.py`, `scraper/lambda_handler.py` | 87 |
| Consumer | `processing/postgres_quote_store.py`, `processing/sqs_consumer_handler.py`, `processing/requirements.txt` | 98 |
| DB layer | `db/__init__.py`, `db/connection.py`, `db/schema.sql`, `db/rds-global-bundle.pem` | 73 (+2,812 lines of public CA certificates) |
| Read side | `quotes_api/postgres_quote_repository.py`, `quotes_api/postgres_pipeline_status_repository.py`, `quotes_api/repositories.py`, `quotes_api/requirements.txt` | 109 |
| EC2 deploy | `deploy/ec2-ubuntu/install.sh`, `quotes-scraper.service`, `quotes-scraper.timer`, `scraper.env.example` | 100 |
| Docs | `phases/phase-6-sqs-rds-pipeline.md`, `reports/phase-6-impact-report.md` | — |
| Repo | `.gitattributes` (forces LF for `deploy/` and `*.sh`) | 3 |

### Modified (11)
| File | Change |
|---|---|
| `scraper/interfaces.py` | + `RecordPublisher` ABC |
| `scraper/main.py` | `SCRAPER_OUTPUT=sqs\|s3` switch; S3 kept as the legacy branch |
| `processing/interfaces.py` | + `QuoteStore` ABC |
| `quotes_api/handler.py` | Repository comes from `repositories.build_quote_repository()`; same 60s warm cache |
| `quotes_api/status_handler.py` | Repository comes from `repositories.build_status_repository()` |
| `frontend/.../pipelineApi.ts` | + `triggerScrape()` |
| `frontend/.../PipelineStatusPanel.tsx/.css` | "Run scrape now" button, run feedback, relabelled metrics |
| `frontend/.../QuotesDashboard.tsx` | Passes `reload` so quotes refresh after a scrape (1 line) |
| `README.md`, `.gitignore` | New architecture, table rows, phase link; ignore `build-{consumer,scraper,api}/` |

### Unchanged but now legacy (rollback only)
`scraper/s3_storage.py`, `processing/handler.py`, `processing/s3_objects.py`, `quotes_api/s3_quote_repository.py`, `quotes_api/s3_pipeline_status_repository.py`

### Reused as-is
`scraper/quotes_scraper.py` (`QuotesToScrapeScraper`) and `processing/quote_cleaner.py` (`QuoteCleaner`, including its deterministic `id`, which becomes the table's primary key)

### Untouched
All of `auth/` (9 modules), `quotes_api/interfaces.py`, and 39 of the 43 frontend source files.

**Net code growth**: about 600 lines of source on a baseline of about 2,700 (≈ +22%), not counting docs and the CA bundle.

## 4. AWS resource delta

| Change | Resource |
|---|---|
| **New** | RDS `quotes-db`; SQS `quotes-ingest-queue`, `quotes-ingest-dlq`; Lambdas `quotes-scraper`, `quotes-consumer`; SQS→Lambda event source mapping; SGs `quotes-lambda-sg`, `quotes-ec2-sg`, `quotes-rds-sg`; IAM roles `quotes-scraper-lambda-role`, `quotes-consumer-lambda-role`, `quotes-ec2-scraper-role` (+ instance profile); EC2 `quotes-scraper-ubuntu`; API route `POST /scrape` + integration |
| **Modified** | `quotes-api`, `quotes-status`: new code, VPC config, `DB_*`/`DATA_BACKEND` env vars, `AWSLambdaVPCAccessExecutionRole` attached. API CORS gets `POST` if it's missing |
| **Retired** | S3 → `quotes-processing` event notification; Windows EC2 instance + Task Scheduler job |
| **Kept as-is** | DynamoDB `Users`; SSM `/quotes-app/jwt-secret`; `quotes-register`/`login`/`authorizer`; S3 `sadi-quotes-frontend`; S3 `sadi-quotes-bucket` (historical data + rollback) |

## 5. API contract impact

| Route | Before | After | Client impact |
|---|---|---|---|
| `GET /quotes` | `{quotes:[{id,text,author,tags,processed_at}]}` from S3 | Same shape, from Postgres, sorted by author | None |
| `GET /status` | `raw_count`/`processed_count` = **file** counts in S3 | Same keys: `raw_count` = **scrape runs**, `processed_count` = **quotes in DB** | Only the meaning changes; labels updated in the UI |
| `POST /scrape` | — | **New**, JWT-protected → `202 {run_id, published, messages}` / `502` if the source site fails | New button |
| `/register`, `/login` | — | Unchanged | None |

## 6. Security / IAM impact
- **Better**:
  - RDS is private: no public endpoint, and 5432 is reachable only from two SGs.
  - Every new role is scoped to a single queue ARN.
  - The EC2 uses an instance profile, not keys.
  - Lambdas verify the DB's TLS certificate against the bundled Amazon RDS CA (`db/connection.py`).
  - The systemd unit runs as an unprivileged `quotes` user with `ProtectSystem=strict`.
- **New attack surface**:
  - `POST /scrape` lets any logged-in user trigger outbound scraping. This is bounded by the JWT authorizer and the 29s Lambda timeout, but there's no per-user rate limit. API Gateway route throttling is the recommended follow-up.
  - SSH (22) on the EC2 is open to one IP only.
- **Trade-off**: the DB password is in Lambda env vars (KMS-encrypted at rest, visible to anyone with `lambda:GetFunctionConfiguration`), not in SSM/Secrets Manager. Reaching those from a VPC Lambda needs a paid interface endpoint (about $7/month) or a NAT gateway (about $32/month). The upgrade path is documented in the phase doc.

## 7. Cost impact (eu-north-1, approximate, on-demand)

| Item | Δ / month | Notes |
|---|---|---|
| RDS `db.t4g.micro` + 20 GB gp3 + 1-day backups | **+$13–16** | $0 within the legacy 12-month free tier (750 h + 20 GB). On the post-July-2025 credit-based free plan it draws down credits |
| EC2 Ubuntu `t3.micro` + public IPv4 | +$8–11 | Free-tier eligible hours apply; public IPv4 is about $3.60/month |
| EC2 Windows (retired) | **−$12–15** | Windows licensing is included in its hourly rate, so removing it saves more than the Ubuntu box costs |
| SQS | ≈ $0 | About 20 requests per scrape; the always-free tier is 1M/month |
| Lambda (2 new) | ≈ $0 | Always-free tier |
| VPC Lambdas | $0 | No NAT or interface endpoints by design |
| S3 | ≈ −$0 | `raw/`/`processed/` stop growing |

**Net**: roughly **+$10–15/month** outside the free tier. RDS is the main cost driver; you can stop it when idle (it auto-restarts after 7 days).

## 8. Behavioural / data impact
- **Duplicate quotes fixed**:
  - Today every scrape writes another `processed/*.json` file, and `S3QuoteRepository.list_quotes()` concatenates all of them. The dashboard's "Total quotes" therefore grows by 100 with every scrape, and the same `id` appears repeatedly.
  - Postgres upserts on `id`, so after cut-over the count settles at the real number of distinct quotes (100).
  - Existing S3 history is **not migrated**; the first scrape after deploy fills the DB.
- **Scraping on demand**: users can trigger a run from the dashboard instead of waiting for the schedule. The EC2 timer runs every 6h (00/06/12/18 UTC) as the baseline.
- **Run tracking**:
  - `scrape_runs` records each run's `source` (`lambda`/`ec2`), start time, last message time and quote count.
  - Known limitation: if SQS delivers a message twice, that run's `quote_count` is over-counted. The quotes themselves stay correct, because the upsert is idempotent.
- **Post-scrape refresh lag**:
  - The dashboard re-reads data 8s after `POST /scrape`.
  - `/status` is uncached, so it updates right away.
  - `/quotes` keeps its 60s warm-container cache, so on a warm Lambda the new quotes can take up to a minute to appear. This only matters when the content changes; quotes.toscrape.com is static.

## 9. Performance impact
| Path | Before | After |
|---|---|---|
| `/quotes` cold read | `ListObjectsV2` + **one `GetObject` per processed file**, getting slower with every scrape | One indexed `SELECT` of 100 rows, constant time |
| `/status` | Two full prefix listings | One 4-subquery `SELECT` |
| Lambda cold start | No VPC | VPC Lambdas: Hyperplane ENIs mean almost no added cold-start time; the first DB connection plus TLS adds about 100–300 ms, then it's reused per container |
| Ingestion latency | Scrape → S3 → event → Lambda (seconds) | Scrape → SQS → consumer (seconds), with batches of up to 10 messages processed in parallel |
| Scrape size | 100 quotes → 1 S3 object | 100 quotes → 4 messages in 1 `SendMessageBatch` call (largest about 6.6 KB, limit 256 KB) |

## 10. Reliability impact
- **DLQ**: a message that fails 3 times moves to `quotes-ingest-dlq` (kept 14 days) instead of being lost or retried forever.
- **Partial batch failure**: `ReportBatchItemFailures` means one bad message doesn't make its 9 batch-mates retry.
- **Idempotent writes**: upserts on a deterministic `id`, so redelivery and double scrapes are harmless.
- **Connection resilience**: `run_with_reconnect` retries once on a dead cached connection, and the consumer resets the connection after any failed message.
- **Publisher retry**: entries that SQS rejects get one retry; after that the run fails loudly (Lambda 5xx / non-zero systemd exit).
- **New single point of failure**: RDS is single-AZ. A DB outage means `/quotes` returns 5xx, but scrapes still queue up in SQS for up to the 4-day default retention and drain once the DB is back. Multi-AZ would roughly double the RDS cost.

## 11. Risks & mitigations
| Risk | Likelihood | Mitigation |
|---|---|---|
| Console-created Lambda picks up the default handler/role (a known issue in this project) | Medium | Every create/update step in the phase doc is followed by a `get-function-configuration` check |
| `POST` missing from API CORS → browser blocks "Run scrape now" | Medium | `get-api --query CorsConfiguration` check is included in step 6 |
| `install.sh` checked out with CRLF on Windows → fails on Ubuntu | Low | `.gitattributes` forces LF; troubleshooting entry included |
| RDS CA bundle rotates | Low (years) | Re-download `global-bundle.pem` and redeploy |
| `POST /scrape` abuse | Low | JWT required; add API Gateway route throttling as a follow-up |

## 12. Rollback plan
1. **Read path**: set `DATA_BACKEND=s3` on `quotes-api`/`quotes-status`, and remove their VPC config (or add a free S3 gateway endpoint).
2. **Ingestion**: restore the saved S3 bucket notification, and set `SCRAPER_OUTPUT=s3` + `RAW_BUCKET` on the EC2. The EC2 role then needs `s3:PutObject` on `raw/*`.
3. **API**: delete the `POST /scrape` route. The frontend button then shows an error, and nothing else is affected.
4. **Code**: `main` is untouched until this branch is merged.

## 13. Verification performed (local, pre-deploy)
| Check | Result |
|---|---|
| `python -m py_compile` on all backend modules | ✅ |
| Publisher: 260 records → 11 messages, batches ≤10, retry of a rejected entry | ✅ |
| Scraper Lambda handler: `202` on success, `502` when the source site fails | ✅ |
| Consumer: valid message committed; malformed JSON and missing `run_id` returned as `batchItemFailures` | ✅ |
| Postgres repositories return exactly the S3 JSON contract | ✅ |
| `run_with_reconnect` retries once on `InterfaceError` | ✅ |
| pg8000 1.31 API (`ssl_context`, `timeout`, `format` paramstyle, exception classes) matches usage | ✅ |
| **Live** scrape of quotes.toscrape.com → fake SQS: 100 quotes, 4 messages, 1 batch call | ✅ |
| Bundled RDS CA loads into an `ssl` context | ✅ |
| `bash -n install.sh` | ✅ |
| `npm run build` (tsc + vite) | ✅ |
| Against real AWS (RDS, SQS, VPC networking) | ⏳ Pending: end-to-end checklist in the phase doc |
