# Phase 2 — Lambda processing

**Status**: Complete

## Goal
An S3 event on `raw/*` triggers a Lambda that cleans/normalizes the data and
writes it to `processed/*` in the same bucket.

## Resources
- One Lambda function
- S3 event notification, **prefix-filtered to `raw/`** (avoids the
  S3→Lambda infinite-loop hazard — see plan's Architecture Review #1)

## IAM
Lambda execution role: `s3:GetObject` on `.../raw/*`, `s3:PutObject` on
`.../processed/*`. Nothing else.

## Checklist
- [x] Implement `processing/interfaces.py` (`DataCleaner`, `ObjectReader`, `ObjectWriter` ABCs)
- [x] Implement `processing/quote_cleaner.py` (`QuoteCleaner` — strips
      wrapping quote chars, normalizes/dedupes tags, adds a stable `id`
      and `processed_at` timestamp)
- [x] Implement `processing/s3_objects.py` (`S3ObjectReader`, `S3ObjectWriter`)
- [x] Implement `processing/handler.py` (thin Lambda entrypoint, wires reader → cleaner → writer)
- [x] Create the Lambda function (`quotes-processing`), deploy the package
- [x] Configure S3 event notification: `s3:ObjectCreated:*`, prefix `raw/`
- [x] Grant S3 permission to invoke the Lambda (resource-based policy)
- [x] Verify: drop a test object in `raw/`, confirm a normalized counterpart
      appears in `processed/`; check Lambda CloudWatch Logs

## Activity Log
- 2026-09-21: Implemented `processing/` package (interfaces, `QuoteCleaner`,
  `S3ObjectReader`/`S3ObjectWriter`, `handler.py`). No third-party deps
  needed beyond `boto3` (already in the Lambda runtime), so no dependency
  packaging step required for this one.
- 2026-09-21: Deployed `quotes-processing` Lambda (role
  `quotes-processing-lambda-role`, `s3:GetObject` on `raw/*` +
  `s3:PutObject` on `processed/*`), granted S3 invoke permission, and
  configured the `raw/`-prefix-scoped S3 event notification.
- 2026-09-21: Debugged three issues found via direct `aws lambda invoke`
  testing (bypassing the S3 trigger to isolate the failure):
  1. Bucket name typo throughout — actual bucket is **`sadi-quotes-bucket`**
     (not `sadi-qoutes-bucket`). Re-applied every policy/config that
     referenced the bucket ARN.
  2. Lambda `Handler` was stuck on the AWS console default
     (`lambda_function.lambda_handler`) instead of `processing.handler.handler`
     — fixed via `update-function-configuration`.
  3. The function's actual execution role is **`quotes-lambda-role`** (an
     auto-created console role), not `quotes-processing-lambda-role` that
     the CLI steps had been granting permissions to — the S3
     read/write + logs policy had to be re-applied to the correct role.
- 2026-09-21: User confirmed the Lambda now processes successfully and a
  file appears in `processed/`. **Phase 2 complete.**
