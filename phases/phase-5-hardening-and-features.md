# Phase 5 — Code audit fixes + new features

**Status**: Code complete and verified locally; AWS deployment pending

## Goal
A full-code audit (no git repo, so a direct file audit rather than diff-based)
surfaced correctness/security/efficiency findings across the Python Lambdas.
Fixed all of them, then added four scraping-website-style features to the
dashboard: tag filtering, an Authors view, a scrape-pipeline health panel,
and CSV/JSON export.

## Audit fixes applied

| # | File | Fix |
|---|---|---|
| 1 (High) | `processing/handler.py` | Added an explicit skip-if-`processed/` guard at the top of the loop — defense in depth against the S3→Lambda infinite-loop risk even if the event filter is ever broadened |
| 1b | `processing/s3_objects.py` | `S3ObjectWriter` now preserves the relative path after the `raw/` prefix instead of only the trailing filename (avoids silent overwrites if raw/ ever nests under subfolders) |
| 2 (High) | `auth/login_handler.py` | Login now always runs bcrypt (against a precomputed dummy hash when the username doesn't exist) — closes the username-enumeration timing side-channel |
| 3 (Medium) | `auth/bcrypt_hasher.py` | Added `MAX_PASSWORD_BYTES = 72` check — `hash()` raises `PasswordTooLongError` instead of silently truncating (bcrypt's real 72-byte limit) |
| 4 (Medium) | `processing/quote_cleaner.py` | `.get(key) or default` now handles explicit JSON `null`, not just missing keys; `clean()` wraps each record in try/except so one malformed record no longer fails the whole batch |
| 5 (Medium) | `auth/login_handler.py`, `auth/register_handler.py`, `auth/authorizer_handler.py` | Moved `SsmSecretProvider`/`DynamoDBUserRepository`/`BcryptPasswordHasher` construction to module scope so warm Lambda containers reuse them (and the cached SSM secret) across invocations instead of re-fetching every request |
| 6 (Medium) | `quotes_api/handler.py` | Added a 60s module-level cache for `list_quotes()` so a warm container doesn't re-GET every `processed/` object on every single `/quotes` request |
| 9 (Low) | `auth/register_handler.py`, `auth/login_handler.py` | Usernames now lowercased before use as the DynamoDB key — `Alice`/`alice` are the same account |
| 10 (Low) | `auth/login_handler.py` | Added the same empty-input validation `register_handler.py` already had |

**Left as-is** (per user's own call): JWT stored in `localStorage` on the
frontend — fixing this properly means httpOnly-cookie-based auth, a bigger
architecture change than a patch, not done here.

## New features

- **Tag filter** (`features/quotes/TagFilter.tsx`) — top-14 tags by
  frequency, clickable, combines with search
- **Authors view** (`features/quotes/AuthorsList.tsx`) — new sidebar nav
  item; author cards sorted by quote count, click through to a filtered
  Quotes view (unified `activeFilter` state, shared with tag filtering)
- **Scrape pipeline status panel** (`features/pipeline/` — new feature
  module) — shows raw file count, processed file count, last-scraped and
  last-processed timestamps, and a health chip ("N files pending
  processing" if raw > processed). Backed by a **new `GET /status`
  endpoint**:
  - `quotes_api/interfaces.py` — added `PipelineStatusRepository` ABC
  - `quotes_api/s3_pipeline_status_repository.py` — `S3PipelineStatusRepository`,
    lists (not reads) `raw/` and `processed/`, so only needs `s3:ListBucket`,
    not `s3:GetObject`
  - `quotes_api/status_handler.py` — new thin Lambda entrypoint
- **CSV/JSON export** (`shared/exportData.ts`) — exports the currently
  filtered/searched quotes via a Blob + `<a download>`, no backend needed

Also: `Sidebar`/`AppShell` generalized to accept a `navItems` array (was a
single hardcoded item) to support the new Authors nav entry; `Badge` now
supports an optional `onClick` (renders as a button); extracted
`shared/formatDate.ts` to deduplicate date formatting between the table and
the new pipeline panel.

## Verification so far

Rebuilt (`npm run build`, no TS errors) and tested live against `npm run
dev`: Authors view, author-card click → filtered Quotes view, tag click →
filtered Quotes view (and toggle-off), Clear-filter chip, and both export
buttons (no console errors) all confirmed working. The `/status` panel
correctly shows "Failed to fetch" right now — expected, since the new
Lambda/route isn't deployed yet.

## Remaining — AWS deployment

- [ ] Redeploy `processing` Lambda (code-only change, no new deps)
- [ ] Redeploy `quotes-register`, `quotes-login`, `quotes-authorizer`
      (shared `auth-lambda.zip`, code-only change, no new deps)
- [ ] Redeploy `quotes-api` Lambda (code-only change, no new deps)
- [ ] Create new `quotes-status` Lambda + `quotes-status-lambda-role`
      (least-privilege: `s3:ListBucket` only, on `raw/*` and `processed/*`
      prefixes — no `GetObject` needed since the endpoint only lists
      metadata)
- [ ] Wire `GET /status` into the HTTP API (integration + authorizer-protected
      route + invoke permission)
- [ ] Rebuild and re-sync the frontend to `sadi-quotes-frontend`

## Activity Log
- 2026-09-26: User asked for a full code audit; ran it via the code-review
  skill in a subagent (no git repo — did a full-file audit, not diff-based).
  10 findings returned, ranked by severity. User asked to fix everything
  except the flagged localStorage-JWT tradeoff.
- 2026-09-26: Same message also asked for "features like in scrapy.org" —
  clarified via question to mean generic web-scraping-website-style
  features, not literally scrapy.org's marketing site. User picked all 4
  proposed options: tag filter, author pages, scrape job status panel,
  CSV/JSON export.
- 2026-09-26: Implemented all 10 audit fixes and all 4 features. Verified
  the frontend changes live in-browser. Backend Python changes verified by
  build/import correctness only so far — AWS deployment (steps above) not
  yet run.
- 2026-09-26: Deployed everything. Hit two familiar bugs along the way:
  (1) `quotes-status` created with the console-default handler again —
  fixed via `update-function-configuration`; (2) the `GET /status` route
  was accidentally created as `GET /quotes-status` (copy/paste slip) —
  fixed by deleting the wrong route and creating the correct one;
  (3) `quotes-status` was also missing its `QUOTES_BUCKET` env var — added
  via `update-function-configuration`. **Pipeline status panel now fully
  working end-to-end**, correctly showing raw/processed counts and a
  "pending processing" health flag from real S3 data.
- 2026-09-26: Added **client-side pagination** to the quotes table
  (`shared/ui/Pagination.tsx`) — page-size selector (10/25/50), Previous/Next,
  "Showing X-Y of Z" summary. Page resets to 1 whenever search, the active
  tag/author filter, or the page size changes. Verified live: page
  navigation and page-size switching both work correctly.
- 2026-09-26: User asked about supporting multiple scraping target
  websites with a frontend site-selector. Gave a component-by-component
  breakdown (EC2: new `Scraper` subclass + a second Task Scheduler entry,
  no new instance; IAM: no changes needed, existing wildcards already
  cover nested `raw/<site_id>/*` paths; processing: no change if same
  schema, one new `DataCleaner` + factory if not; quotes_api: needs a
  `?site=` param and a way to discover available sites; frontend: a
  selector + threading `site` through the API calls). **Not yet
  implemented** — paused to let the user decide the second site and
  same-vs-different schema before scoping the actual work.
- 2026-09-26: Fixed a sidebar bug — it scrolled along with the page content
  instead of staying pinned. Root cause: `.sidebar` was a plain flex child
  with no fixed positioning, so it just moved with the document's natural
  scroll. Fixed in `shared/ui/Sidebar.css`: `position: sticky; top: 0;
  height: 100svh; align-self: flex-start` pins it to the viewport, and
  `.sidebar-nav` got `flex: 1; overflow-y: auto` so the nav list — not the
  whole sidebar — scrolls internally if it ever has more items than fit,
  while the brand (top) and user/logout block (bottom) stay fixed in
  place. Added a mobile (`max-width: 720px`) override reverting to normal
  static flow, since the layout already stacks sidebar-above-content at
  that width. Verified live: sidebar and its nav/user block stay
  perfectly still while scrolling the quotes table underneath.
