# Quotes ERP — AWS Learning Project

A small, end-to-end AWS project built to learn IAM, EC2, S3, Lambda, API
Gateway, and DynamoDB by building a scraper-backed web app with
authentication — structured like a simple ERP dashboard sitting on top of
scraped data.

**Live pipeline**: an EC2-scheduled Python scraper collects quotes from
[quotes.toscrape.com](http://quotes.toscrape.com) → an S3-triggered Lambda
cleans and normalizes the data → a DynamoDB-backed auth API (bcrypt + JWT)
protects a set of Lambda endpoints behind API Gateway → a React dashboard
displays the data with search, tag/author filtering, pagination, CSV/JSON
export, and a live scrape-pipeline health panel.

## Architecture

Phase 6 (event-driven, on branch `feature/sqs-rds-pipeline`):

```
API Gateway POST /scrape → Lambda quotes-scraper ┐
Ubuntu EC2 (systemd timer) → scraper.main ───────┤  publishers
                                                 ▼
                         SQS quotes-ingest-queue (+ DLQ)
                                                 ▼
                         Lambda quotes-consumer (clean + upsert)   consumer
                                                 ▼
                         RDS PostgreSQL (quotes, scrape_runs)
                                                 ▼
            Lambda API (register / login / quotes / status / scrape)
               → API Gateway (HTTP API, Lambda authorizer on protected routes)
                  → React frontend (S3 static hosting)

DynamoDB — Users table (bcrypt password hashes)
SSM Parameter Store — JWT signing secret (SecureString)
```

Phases 1–5 used a file pipeline (EC2 → S3 `raw/` → Lambda → S3 `processed/`).
It remains in the code as a rollback path (`DATA_BACKEND=s3`, `SCRAPER_OUTPUT=s3`).
See [phase 6](phases/phase-6-sqs-rds-pipeline.md) and the
[impact report](reports/phase-6-impact-report.md).

Every Lambda's IAM role is scoped to only the S3 prefixes / DynamoDB table /
SSM parameter it actually needs — see each phase doc under [`phases/`](phases/)
for the exact policies applied.

## Project structure

Each backend component follows the same shape: an `interfaces.py` defining
small abstract classes (Single Responsibility, Dependency Inversion), one
concrete implementation per interface, and a thin Lambda `*_handler.py`
entrypoint that only wires dependencies together and shapes the HTTP
response — no business logic in the handler itself.

| Directory | Deploys as | Responsibility |
|---|---|---|
| [`scraper/`](scraper/) | Lambda `quotes-scraper` + Ubuntu EC2 (systemd timer) | Scrapes quotes.toscrape.com, publishes batches to SQS (legacy: raw JSON to S3) |
| [`processing/`](processing/) | Lambda `quotes-consumer` (SQS-triggered) | Cleans/normalizes quotes, upserts them into RDS (legacy: S3 `processed/`) |
| [`db/`](db/) | — (bundled into the VPC Lambdas) | Postgres connection (TLS against the RDS CA), schema |
| [`auth/`](auth/) | 3 Lambdas | Register, login (bcrypt + JWT), and the Lambda authorizer |
| [`quotes_api/`](quotes_api/) | 2 Lambdas (in VPC) | Serves quotes from RDS; reports scrape-pipeline health |
| [`deploy/ec2-ubuntu/`](deploy/ec2-ubuntu/) | Ubuntu EC2 | Install script + systemd service/timer for the scheduled scraper |
| [`frontend/`](frontend/) | S3 static site | React + TypeScript ERP-style dashboard |
| [`phases/`](phases/) | — | Build log: what was built, why, and every bug hit along the way |

## Frontend

Vite + React + TypeScript, no heavy state library. Feature-folder layout
(`src/features/auth/`, `src/features/quotes/`, `src/features/pipeline/`)
with shared presentational primitives in `src/shared/ui/`. Local dev:

```bash
cd frontend
cp .env.example .env   # fill in your own API Gateway URL
npm install
npm run dev
```

## Build history

This project was built in phases, each documented as it happened —
including the real bugs hit and how they were fixed (a console-vs-CLI
Lambda handler mismatch, PowerShell's quoting behavior with native
executables, an S3→Lambda infinite-loop guard, a login timing side-channel,
and more):

1. [S3 + EC2 scraper](phases/phase-1-s3-ec2-scraper.md)
2. [Lambda processing](phases/phase-2-lambda-processing.md)
3. [DynamoDB + auth API](phases/phase-3-dynamodb-auth-api.md)
4. [React frontend](phases/phase-4-frontend.md)
5. [Code audit fixes + new features](phases/phase-5-hardening-and-features.md)
6. [API Gateway scraper → SQS → RDS](phases/phase-6-sqs-rds-pipeline.md) — console walkthrough for a new account: [`deploy/CONSOLE-SETUP.md`](deploy/CONSOLE-SETUP.md)

## Free tier notes

Only Lambda and DynamoDB are **Always Free**. EC2, S3, API Gateway, and
CloudFront are free for a new AWS account's first 12 months (RDS
`db.t4g.micro` too, on the legacy free tier; SQS has an always-free 1M requests/month) — see
[`phase-1`](phases/phase-1-s3-ec2-scraper.md) for the full breakdown.
