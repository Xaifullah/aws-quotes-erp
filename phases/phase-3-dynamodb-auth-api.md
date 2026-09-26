# Phase 3 — DynamoDB + Auth API + protected Quotes API

**Status**: Complete

## Goal
DynamoDB-backed register/login (bcrypt + JWT), and a Lambda-authorizer-
protected `GET /quotes` that reads from `processed/`.

## Resources
- DynamoDB `Users` table — PK `username` (String), no sort key
- SSM `SecureString` parameter holding the JWT signing secret (not Secrets
  Manager — see plan's Architecture Review #2)
- 4 Lambdas: `register`, `login`, `authorizer`, `quotes`
- One HTTP API (API Gateway v2) with 3 routes

## IAM
- `register`/`login` Lambdas: `dynamodb:PutItem`/`GetItem` scoped to the
  table ARN only; `ssm:GetParameter` on the JWT secret's ARN only
- `authorizer` Lambda: `ssm:GetParameter` on the JWT secret's ARN only
- `quotes` Lambda: `s3:GetObject` on `.../processed/*` only

## Checklist
- [x] Create `Users` table — PK `username` (String), provisioned 1 RCU/1 WCU
- [x] Generate JWT signing secret, store as SSM `SecureString` (`/quotes-app/jwt-secret`)
- [x] Implement `auth/interfaces.py` (`UserRepository`, `PasswordHasher`, `TokenService`, `SecretProvider` ABCs)
- [x] Implement `auth/dynamodb_user_repository.py`, `auth/bcrypt_hasher.py`,
      `auth/jwt_token_service.py`, `auth/ssm_secret_provider.py`
- [x] Implement `auth/register_handler.py`
- [x] Implement `auth/login_handler.py`
- [x] Implement `auth/authorizer_handler.py` (Lambda REQUEST authorizer, HTTP API 2.0 simple response)
- [x] Implement `quotes_api/interfaces.py` (`QuoteRepository` ABC), `quotes_api/s3_quote_repository.py`, `quotes_api/handler.py`
- [x] Create HTTP API: `POST /register`, `POST /login` (open), `GET /quotes` (authorizer attached)
- [x] Verify: `register` → `login` → `quotes` via curl; `/quotes` returns
      401 with no token, 200 with a valid one (rejecting expired/tampered
      tokens follows from the same JWT verification path, not separately
      curl-tested)

## Activity Log
- 2026-09-21: Implemented `auth/` (interfaces, `DynamoDBUserRepository`,
  `BcryptPasswordHasher`, `JwtTokenService`, `SsmSecretProvider`,
  `register_handler.py`, `login_handler.py`, `authorizer_handler.py` — HTTP
  API 2.0 simple `{isAuthorized: bool}` response format) and `quotes_api/`
  (`QuoteRepository`, `S3QuoteRepository`, `handler.py`).
  `auth/requirements.txt` = `bcrypt` + `PyJWT` (need packaging with deps,
  unlike Phase 2's Lambda — see bcrypt manylinux-wheel gotcha in the plan).
  `quotes_api` needs no extra deps (boto3 only).
  **Next**: user creates the DynamoDB table, SSM secret, IAM roles, deploys
  all 4 Lambdas, and wires up the HTTP API + authorizer.
- 2026-09-21: Learned from Phase 2 troubleshooting — going forward, always
  verify the deployed function's actual `Role` and `Handler` via
  `get-function-configuration` after creation, since console-created
  resources can silently diverge from what CLI commands assume.
- 2026-09-21: Hit `AccessDeniedException` on `ssm:PutParameter` — not a
  Lambda role issue this time, the user's own IAM user (`sadi`) lacked SSM
  permissions. Fixed with a scoped inline policy
  (`quotes-app-ssm-access`) on the user, limited to
  `arn:aws:ssm:eu-north-1:ACCOUNT_ID:parameter/quotes-app/*`.
- 2026-09-22: Deployed `quotes-register`, `quotes-login`, `quotes-authorizer`
  — all via CLI (not console) with explicit `--runtime python3.12` to avoid
  a repeat of the Phase 2 handler/role mismatch. Two roles:
  `quotes-auth-lambda-role` (register+login: DynamoDB + JWT secret) and
  `quotes-authorizer-lambda-role` (authorizer: JWT secret only). User
  verified all three via `get-function-configuration`.
  **Next**: deploy `quotes-api` Lambda, then wire up the HTTP API + routes
  + authorizer.
- 2026-09-22: Deployed `quotes-api` Lambda (role `quotes-api-lambda-role`:
  `s3:GetObject` + `s3:ListBucket` scoped to `processed/*`). Direct-invoke
  test hit a bug: `S3QuoteRepository.list_quotes` tried to JSON-parse a
  zero-byte S3 "folder marker" object at key `processed/` (auto-created by
  the console when browsing the bucket) and crashed with
  `JSONDecodeError`. Fixed by skipping keys ending in `/` or with
  `Size == 0` in `quotes_api/s3_quote_repository.py`. Redeployed via
  `update-function-code`, confirmed working.
- 2026-09-22: **Paused for the day.** All 4 Lambdas deployed and verified
  (`quotes-register`, `quotes-login`, `quotes-authorizer`, `quotes-api`).
  DynamoDB table and SSM secret in place. **Remaining for Phase 3**: HTTP
  API creation (see "Resume Point" section below) — API + 3 integrations +
  2 open routes + authorizer + 1 protected route + 4 invoke permissions +
  stage + curl verification. Exact commands saved below so this can resume
  cold, even in a brand-new session.
- 2026-09-26: Created HTTP API `quotes-app-api` (`API_ID = gfoyhnaxh3`) and
  its 3 Lambda integrations: `quotes-register` = `xqtzhr9`,
  `quotes-login` = `cxg98gk`, `quotes-api` = `4dyv0x8`. Created open routes
  for `/register`/`/login` and the `quotes-jwt-authorizer` authorizer
  (`AUTHORIZER_ID = 146rv0`). Created protected `/quotes` route, granted
  all 4 invoke permissions, deployed `$default` stage. **API endpoint**:
  `https://gfoyhnaxh3.execute-api.eu-north-1.amazonaws.com`.
- 2026-09-26: Fixed the PowerShell `curl` alias issue (`Invoke-WebRequest`
  doesn't support `-H`/`-d`) and a `\"`-quote-escaping bug identical to the
  earlier `schtasks` one — fixed by using `curl.exe` with single-quoted
  JSON bodies. Then hit the **same handler-default bug as Phase 2**
  (`lambda_function.lambda_handler` instead of `auth.register_handler.handler`)
  on `quotes-register` — fixed via `update-function-configuration`. User
  confirmed register now works: user created in DynamoDB with a bcrypt
  hash.
- 2026-09-26: Login kept 500ing even after the handler fix — root cause
  was that the **inline quoted JSON body itself was unreliable in
  PowerShell**: neither `\"`-escaped nor single-quoted `-d` values survive
  PowerShell → native-exe argument passing intact. Standing fix adopted:
  write JSON payloads to a file with `Set-Content` and pass them via
  `curl.exe --data "@file.json"` (and the same `file://` pattern for any
  AWS CLI parameter that takes inline JSON, e.g. `dynamodb --key`) — see
  memory note for the general rule. The corrupted `password_hash` this
  produced for the original `testuser` record (`ValueError: Invalid salt`
  in bcrypt) was cleaned up by deleting that DynamoDB item and
  re-registering with the reliable file-based method. **Login now
  confirmed working** — returns a valid JWT.
- 2026-09-26: Confirmed `quotes-authorizer` handler was already correct.
  Final verification: `GET /quotes` with no token → `401 Unauthorized`;
  with a valid token → `200` with the full quotes array (91 quotes) read
  from `processed/`. **Phase 3 complete.**

## Resume Point — HTTP API Setup (not yet run)

Known values: region `eu-north-1`, account `ACCOUNT_ID`, bucket
`sadi-quotes-bucket`, DynamoDB table `Users`, JWT secret parameter
`/quotes-app/jwt-secret`, Lambdas `quotes-register`/`quotes-login`/
`quotes-authorizer`/`quotes-api` (all confirmed working via direct invoke).

**Step 8 — Create the HTTP API**
```bash
aws apigatewayv2 create-api --name quotes-app-api --protocol-type HTTP --region eu-north-1 --query "ApiId" --output text
```
Save as `<API_ID>`.

**Step 9 — Create the three Lambda integrations**
```bash
aws apigatewayv2 create-integration --api-id <API_ID> --integration-type AWS_PROXY --integration-uri arn:aws:lambda:eu-north-1:ACCOUNT_ID:function:quotes-register --payload-format-version 2.0 --region eu-north-1 --query "IntegrationId" --output text

aws apigatewayv2 create-integration --api-id <API_ID> --integration-type AWS_PROXY --integration-uri arn:aws:lambda:eu-north-1:ACCOUNT_ID:function:quotes-login --payload-format-version 2.0 --region eu-north-1 --query "IntegrationId" --output text

aws apigatewayv2 create-integration --api-id <API_ID> --integration-type AWS_PROXY --integration-uri arn:aws:lambda:eu-north-1:ACCOUNT_ID:function:quotes-api --payload-format-version 2.0 --region eu-north-1 --query "IntegrationId" --output text
```
Save as `<REGISTER_INT_ID>`, `<LOGIN_INT_ID>`, `<QUOTES_INT_ID>`.

**Step 10 — Open routes**
```bash
aws apigatewayv2 create-route --api-id <API_ID> --route-key "POST /register" --target integrations/<REGISTER_INT_ID> --region eu-north-1

aws apigatewayv2 create-route --api-id <API_ID> --route-key "POST /login" --target integrations/<LOGIN_INT_ID> --region eu-north-1
```

**Step 11 — Create the Lambda authorizer**
```bash
aws apigatewayv2 create-authorizer --api-id <API_ID> --authorizer-type REQUEST --authorizer-uri arn:aws:apigateway:eu-north-1:lambda:path/2015-03-31/functions/arn:aws:lambda:eu-north-1:ACCOUNT_ID:function:quotes-authorizer/invocations --identity-source '$request.header.Authorization' --authorizer-payload-format-version 2.0 --authorizer-result-ttl-in-seconds 0 --name quotes-jwt-authorizer --region eu-north-1 --query "AuthorizerId" --output text
```
Save as `<AUTHORIZER_ID>`.

**Step 12 — Protected route (`/quotes`, authorizer attached)** ✅ values filled in: `API_ID=gfoyhnaxh3`, `QUOTES_INT_ID=4dyv0x8`, `AUTHORIZER_ID=146rv0`
```bash
aws apigatewayv2 create-route --api-id gfoyhnaxh3 --route-key "GET /quotes" --target integrations/4dyv0x8 --authorization-type CUSTOM --authorizer-id 146rv0 --region eu-north-1
```

**Step 13 — Let API Gateway invoke all four Lambdas**
```bash
aws lambda add-permission --function-name quotes-register --statement-id apigw-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:eu-north-1:ACCOUNT_ID:gfoyhnaxh3/*/*/register" --region eu-north-1
```
```bash
aws lambda add-permission --function-name quotes-login --statement-id apigw-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:eu-north-1:ACCOUNT_ID:gfoyhnaxh3/*/*/login" --region eu-north-1
```
```bash
aws lambda add-permission --function-name quotes-api --statement-id apigw-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:eu-north-1:ACCOUNT_ID:gfoyhnaxh3/*/*/quotes" --region eu-north-1
```
```bash
aws lambda add-permission --function-name quotes-authorizer --statement-id apigw-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:eu-north-1:ACCOUNT_ID:gfoyhnaxh3/authorizers/146rv0" --region eu-north-1
```

**Step 14 — Deploy stage**
```bash
aws apigatewayv2 create-stage --api-id gfoyhnaxh3 --stage-name '$default' --auto-deploy --region eu-north-1
```
```bash
aws apigatewayv2 get-api --api-id gfoyhnaxh3 --region eu-north-1 --query "ApiEndpoint" --output text
```

**Step 15 — Verify end-to-end**
On Windows PowerShell, use `curl.exe` explicitly — plain `curl` is aliased
to `Invoke-WebRequest`, which doesn't understand `-H`/`-d` flags. Also use
**single quotes** around the JSON body (not `\"`-escaped double quotes) —
PowerShell mangles backslash-escaped quotes when passing args to native
exes, same class of bug as the earlier `schtasks` quoting issue.
```bash
curl.exe -X POST https://gfoyhnaxh3.execute-api.eu-north-1.amazonaws.com/register -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass123"}'
curl.exe -X POST https://gfoyhnaxh3.execute-api.eu-north-1.amazonaws.com/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass123"}'
curl.exe -i https://gfoyhnaxh3.execute-api.eu-north-1.amazonaws.com/quotes
curl.exe https://gfoyhnaxh3.execute-api.eu-north-1.amazonaws.com/quotes -H "Authorization: Bearer <TOKEN>"
```
First `/quotes` call should be `401`/`403` (no token), second should be
`200` with quotes JSON. CORS setup is deferred to Phase 4 (need the
CloudFront domain first).
