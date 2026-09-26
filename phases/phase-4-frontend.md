# Phase 4 — React frontend + AWS hosting

**Status**: In progress — deployed and fully working over HTTP; CloudFront (HTTPS) blocked on AWS account verification

## Goal
Vite + React login/register + quotes dashboard, deployed to S3 static
hosting behind CloudFront (fixes HTTP/HTTPS mixed-content issue — see
plan's Architecture Review #5).

## Resources
- Vite + React app
- Second S3 bucket (static website hosting)
- CloudFront distribution

## IAM
S3 bucket policy: public `s3:GetObject` scoped to that one hosting bucket
only. No new Lambda roles.

## Checklist
- [x] Scaffold Vite + React (TypeScript) app in `frontend/`:
      `src/shared/apiClient.ts` (fetch wrapper, base URL + auth header injection)
- [x] `src/features/auth/` — LoginForm, RegisterForm, useAuth hook, authApi.ts
- [x] `src/features/quotes/` — QuotesDashboard, useQuotes hook, quotesApi.ts
- [x] `.env` with `VITE_API_URL=https://gfoyhnaxh3.execute-api.eu-north-1.amazonaws.com`
- [x] Configure CORS on the HTTP API for `localhost` (dev) — done via
      `apigatewayv2 update-api --cors-configuration`. CloudFront domain
      still to be added to `AllowOrigins` once that distribution exists.
- [x] `npm run build`; sync `dist/` to the S3 hosting bucket
- [ ] Create CloudFront distribution pointed at the S3 bucket — **blocked**:
      AWS requires account verification before allowing new CloudFront
      resources on this account; support case filed
- [x] Verify: `vite dev` locally against deployed API works end-to-end —
      login, dashboard (real quotes render), logout, and register all
      confirmed working in a real browser (Chrome via automation).
      **Also verified on the actual deployed S3 site** (login + dashboard
      with real quotes) over the plain HTTP website endpoint. CloudFront
      HTTPS check still pending the AWS support case.

## Activity Log
- 2026-09-26: Phase 3 complete — HTTP API live at
  `https://gfoyhnaxh3.execute-api.eu-north-1.amazonaws.com` with working
  `/register`, `/login`, and authorizer-protected `/quotes`. Ready to
  start Phase 4. Known values carried over: region `eu-north-1`, account
  `ACCOUNT_ID`, bucket `sadi-quotes-bucket`.
- 2026-09-26: Scaffolded `frontend/` with `npm create vite@latest -- --template react-ts`,
  built out the SOLID module structure (`shared/apiClient.ts`,
  `features/auth/*`, `features/quotes/*`), and rewrote `App.tsx` to wire
  login/register/dashboard. `npm run build` succeeds with no TypeScript
  errors.
- 2026-09-26: Ran `npm run dev` and tested live in a real Chrome browser
  (via claude-in-chrome automation) against the deployed API. First
  attempt hit a CORS block (`Failed to fetch`) — expected, since CORS
  wasn't configured yet. Fixed with
  `aws apigatewayv2 update-api --cors-configuration` (AllowOrigins:
  `http://localhost:5173`). A transient `503` on the next attempt cleared
  up on retry (confirmed via a direct `curl.exe` preflight — CORS headers
  came back correctly: `204`, right `Access-Control-Allow-*` headers).
  **Full flow now verified working in-browser**: login → dashboard (real
  quotes rendered) → logout → register, all against the live AWS backend.
  **Next**: S3 static website hosting bucket + `npm run build` + sync +
  CloudFront distribution, then add the CloudFront domain to the API's
  CORS `AllowOrigins`.
- 2026-09-26: Created `sadi-quotes-frontend` bucket, enabled static website
  hosting, opened public `s3:GetObject` (the one intentionally-public
  bucket in this project — it's the static site itself). First manual
  upload attempt uploaded the `dist` folder itself instead of its
  contents, nesting everything under a `dist/` prefix and causing a `404`
  (index.html wasn't at bucket root) — user fixed by re-uploading the
  folder's *contents* directly to the bucket root. Verified via browser:
  site now loads correctly at
  `http://sadi-quotes-frontend.s3-website.eu-north-1.amazonaws.com`.
  Note: API calls from this page won't work yet since CORS only allows
  `http://localhost:5173` — going straight to CloudFront next rather than
  adding this temporary HTTP origin, then updating CORS with the final
  CloudFront domain.
- 2026-09-26: `aws cloudfront create-distribution` failed with
  `AccessDenied: Your account must be verified before you can add new
  CloudFront resources` — a common restriction on newer AWS accounts.
  User filed an AWS Support case to lift it. **Interim fix**: added
  `http://sadi-quotes-frontend.s3-website.eu-north-1.amazonaws.com` to the
  HTTP API's CORS `AllowOrigins` (alongside `localhost:5173`) instead of
  waiting on CloudFront — mixed-content blocking doesn't apply here since
  the direction is HTTP page → HTTPS API (browsers only block the
  opposite: HTTPS page → HTTP resource), so CORS was the only real gate.
  **Confirmed working end-to-end on the live deployed site**: login →
  dashboard with real quotes rendered, via browser automation against
  `http://sadi-quotes-frontend.s3-website.eu-north-1.amazonaws.com`.
  **Remaining**: swap in CloudFront + its HTTPS domain once the AWS
  support case resolves (re-run the CloudFront creation steps saved
  earlier in this file, then update CORS `AllowOrigins` again).
- 2026-09-26: **Professional ERP-style redesign.** User asked for a
  polished, ERP-like UI (this was scoped/considered up front, not an
  afterthought). Design tokens added to `index.css` — palette (accent
  `#2f5fde`, semantic success/warning/danger, light+dark via
  `prefers-color-scheme`), typography (Manrope for headings, Inter for
  body/data, both via Google Fonts), consistent radius/shadow scale.
  Built reusable presentational primitives under `shared/ui/`: `Sidebar`,
  `TopBar`, `AppShell`, `StatCard`, `Badge`, `AuthLayout` — each with its
  own colocated CSS file, keeping the SOLID/modular structure (these are
  pure presentation, no business logic, reusable across features).
  Redesigned: split-screen login/register (`AuthLayout` + restyled
  `LoginForm`/`RegisterForm`), and the quotes view is now a real ERP shell
  — dark sidebar with user info + logout, sticky top bar with a live
  client-side search (by text/author/tag), 3 stat cards (Total Quotes,
  Authors, Tags — computed from real data, not hardcoded), and a proper
  data table (`QuotesTable`: truncated quote text with hover title, tag
  badges with overflow `+N`, formatted dates). Added `shared/jwt.ts` to
  decode the JWT payload client-side (username for the sidebar display
  only — the token is already server-verified, this is purely cosmetic).
  Removed the unused default Vite template `App.css`.
  **Verified live in the browser**: full login → search → filtered
  results flow all confirmed working with the new design.
