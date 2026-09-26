# Phase 1 — S3 buckets + EC2 scraper

**Status**: Complete

## Goal
EC2 runs a scheduled Python scraper against quotes.toscrape.com and writes
raw JSON to `s3://<bucket>/raw/`.

## Resources
- One S3 bucket (`raw/` and `processed/` prefixes)
- One EC2 instance — **Windows Server** (launched via console, not CLI),
  t3.micro/t2.micro
- One IAM role + instance profile for the EC2 instance

> Note: originally planned as Amazon Linux + systemd timer; user launched a
> Windows instance via the console instead, so scheduling uses **Task
> Scheduler** (`schtasks`) and access is via **RDP**, not SSH/cron.

## IAM
EC2 instance role: `s3:PutObject` scoped to `arn:aws:s3:::<bucket>/raw/*` only.

## Checklist
- [x] Implement `scraper/interfaces.py` (`Scraper`, `RawStorage` ABCs)
- [x] Implement `scraper/quotes_scraper.py` (`QuotesToScrapeScraper`)
- [x] Implement `scraper/s3_storage.py` (`S3RawStorage`)
- [x] Implement `scraper/main.py` (composition root)
- [x] Create S3 bucket, block all public access
- [x] Create IAM role + instance profile for EC2 (least-privilege: `s3:PutObject` on `raw/*` only)
- [x] Launch EC2 instance (Windows, via console)
- [x] Verify IAM instance profile is attached (not long-lived IAM user credentials)
- [x] RDP in, install Python, copy `scraper/` package over, install deps
- [x] Test run `scraper/main.py` manually, confirm object appears in S3
- [x] Set up a Windows Task Scheduler task to run the scraper on a schedule
- [x] Verify: scheduled run succeeds (`Last Result: 0`) and writes a fresh object to `s3://<bucket>/raw/`
- [ ] Verify: objects land in `s3://<bucket>/raw/` on schedule (`aws s3 ls`)

## Activity Log
- 2026-09-21: Wrote `scraper/` package (interfaces, `QuotesToScrapeScraper`,
  `S3RawStorage`, `main.py`) and `scraper/requirements.txt`.
- 2026-09-21: Gave user CLI commands for S3 bucket creation, public-access
  block, IAM trust policy, role, inline policy (`s3-raw-put-only`), and
  instance profile creation.
- 2026-09-21: User confirmed S3 bucket + IAM role/instance profile created.
- 2026-09-21: User launched the EC2 instance via the AWS Console instead of
  CLI, and chose a **Windows** AMI (not Amazon Linux as originally planned).
  Adjusted this phase's remaining steps: RDP instead of SSH, Task Scheduler
  instead of systemd/cron. User has the .pem key for the RDP password.
  **Next**: get Windows password, RDP in, install Python, deploy code,
  test run, create the scheduled task.
- 2026-09-21: Hit `NoCredentialsError` on first test run — IAM instance
  profile wasn't attached at console launch. Fixed with
  `aws ec2 associate-iam-instance-profile`.
- 2026-09-21: Hit broken quoting in the first `schtasks /TR` attempt
  (unescaped nested quotes around the python.exe path). Fixed by wrapping
  the run command in `C:\quotes-scraper\run_scraper.bat` and pointing
  `schtasks` at that file instead of an inline nested-quoted command.
- 2026-09-21: User confirmed scheduled task ran successfully
  (`Last Result: 0`) and a new object landed in `s3://<bucket>/raw/`.
  **Phase 1 complete.**
- 2026-09-21: Bucket renamed to **`sadi-qoutes-bucket`**. Updated the EC2
  role's inline policy (`s3-raw-put-only`) to the new bucket ARN, and
  updated `RAW_BUCKET` machine env var on the EC2 instance. User confirmed
  the scraper writes to the new bucket successfully.
