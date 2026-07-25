# Fireons Build Backlog

User stories sized so that each story is one PR. Ordered within milestones; milestones come from the build order in [ROADMAP.md](ROADMAP.md). A and B first (same auth/user surface), C and D in parallel after, E last. Phase 2 stories (F, G) start only after Phase 1 ships.

Status: `[ ]` not started, `[~]` in progress, `[x]` merged.

---

## Milestone A: FIRE target and progress (roadmap 1.1)

### [ ] A1. Set a FIRE target
As a user, I can set my FIRE target (amount, currency, optional target date) so my tracking has a goal.
- Migration adds target fields to User; API to set/update/clear the target; validation (positive amount, supported currency)
- Settings UI to enter the target
- Touchpoints: `backend/database/models.py`, `backend/alembic`, new `backend/api/fire_target_api.py` or extend auth/me, `frontend/src/app/networth`

### [ ] A2. Derive my target from expenses
As a user, I can derive my FIRE number from annual expenses x 25 with Lean/Coast/Barista/Fat presets, so I do not need to know my number upfront.
- Calculator in the target-setting UI; result prefills the A1 target; presets adjust the multiple/assumptions
- Pure frontend on top of A1

### [ ] A3. See my progress to FI
As a user, I see percent to target, trajectory, and projected FI date on my dashboard, so I know where I stand.
- Progress computed from existing net worth history and the A1 target; new summary endpoint or extension of `/summary`
- Dashboard progress module (headline percent, projected date, trajectory on the existing chart)
- Touchpoints: `backend/api/account_api.py` (summary), `frontend/src/components/NetWorthDashboard.tsx`

## Milestone B: Anonymity and session (roadmap 1.2)

### [ ] B1. Register without identity
As a new user, I can register with only email, handle, and password, so I stay anonymous from the start.
- full_name and location optional in model, API, and register UI; handle uniqueness messaging
- Touchpoints: `backend/api/auth_api.py`, `frontend/src/app/register`

### [ ] B2. Be my handle everywhere
As a user, only my handle ever appears in the UI; my email is a login credential only.
- Audit and fix every display of email/full_name; add visibility fields to User (private by default) ready for Phase 2 public pages
- Touchpoints: `frontend/src/contexts/AuthContext.tsx`, navigation, dashboard

### [ ] B3. Stay logged in
As a user, my session survives longer than 30 minutes so I am not logged out mid-update.
- Refresh token flow (or long-lived token with rotation); logout invalidates
- Touchpoints: `backend/auth_utils.py`, `backend/api/auth_api.py`, `frontend/src/contexts/AuthContext.tsx`

## Milestone C: Professional directory (roadmap 1.4)

### [ ] C1. Professional model and internal verification
As the founder, I can add a professional and mark them verified after checking their registration number, so the directory only ever contains verified supply.
- Professional model: name, registration type (SEBI RIA, CA, AMFI MFD, IRDAI), registration number, specializations, languages, fee disclosure, external contact link, verified flag, active flag; migration
- Admin path for v1: a CLI/seed script is acceptable (no admin UI yet); only verified+active professionals are ever served by the API
- Touchpoints: `backend/database/models.py`, `backend/alembic`, new `backend/api/professionals_api.py`, `backend/scripts`

### [ ] C2. Browse the directory
As a logged-in user, I can browse verified professionals and filter by category and language, so I can find relevant help.
- List endpoint with filters; neutral ordering (alphabetical or rotation); directory page behind auth; empty-state design
- Touchpoints: `backend/api/professionals_api.py`, new `frontend/src/app/professionals`

### [ ] C3. View a professional and hand off
As a user, I can open a professional's profile, see credentials and fees, and reach their own channel, so I can engage them formally off-platform.
- Profile page with registration details and the standing disclosure (advice, KYC, payment happen in the professional's channel; Fireons only verifies credentials)
- Contact reveal / outbound link records a handoff event
- Touchpoints: `frontend/src/app/professionals/[id]`, handoff event endpoint

### [ ] C4. Apply as a professional
As a professional, I can submit my details for verification, so I can get listed.
- v1: external form (Typeform or similar) linked from the marketing site CTA; submissions land in the C1 pipeline manually
- Touchpoints: `website/app/for-professionals`, `website/lib/config.ts`

## Milestone D: Statement forwarding (roadmap 1.3)

### [ ] D1. Get my forwarding address
As a user, I see my unique statement-forwarding address (u-handle@statements.fireons.com) with setup instructions for my banks, so I can automate updates.
- Address provisioning per user, shown in profile/settings with per-institution forwarding instructions
- Decide inbound provider here (SES vs Mailgun, roadmap open question 4)

### [ ] D2. Receive and store statements
As a user, statements forwarded to my address appear in Fireons, so nothing gets lost.
- Inbound webhook, sender-to-user routing, attachment extraction, encrypted storage, reject/quarantine mail to unknown addresses
- Touchpoints: new `backend/api/inbound_email_api.py`, storage layer, `backend/statements` conventions

### [ ] D3. Statements inbox
As a user, I can see arrived statements, attach one to an account, and confirm the balance from it, so my net worth updates from real documents.
- Inbox UI: list with sender/date/status; attach-to-account; manual balance entry prefilled where possible; done/dismiss states
- Touchpoints: new `frontend/src/app/statements`, balance endpoints in `backend/api/account_api.py`

### [ ] D4. Unlock protected PDFs
As a user, I can store per-sender statement passwords (PAN/DOB patterns), so password-protected PDFs open automatically.
- Per-sender password store (encrypted at rest), unlock on ingest, clear failure state when the password is wrong

## Milestone E: Site and launch (roadmap 1.6, 1.7)

### [ ] E1. Marketing site truth pass
As a visitor, the site describes only what the product actually does, in India/NRI terms.
- Fireons naming everywhere; copy rewritten per the roadmap gaps table; INR-first examples; Indian registration categories on For Professionals; NRI positioning
- Touchpoints: all pages under `website/app`

### [ ] E2. Analytics events
As the founder, I can see the funnel, so Phase 2 validation has data.
- Events: signup, target set, account added, balance updated, statement received, directory viewed, professional profile viewed, handoff clicked
- Pick a lightweight provider (PostHog or similar); wire frontend and backend events

### [ ] E3. Production launch
As a user, I can use Fireons at fireons.com securely.
- Production deploy of backend, app, site; real SECRET_KEY; database backups; terms and privacy policy reflecting actual practices and the not-an-adviser position

## Ops throughout (roadmap 1.5, no PRs)

- Recruit 10 to 20 CA/tax professionals; pipeline tracked as contacted, interested, verified, live. Launch blocker: 15+ live before announcing.

---

## Phase 2 build stories (start only after Phase 1 ships)

## Milestone F: Public journey pages

### [ ] F1. Publish my journey
As a user, I can publish an opt-in public page at fireons.com/u/handle showing percent to target, trajectory, milestones, and allocation percentages, so I can share my progress.
- No login to view; no absolute amounts by default; publish/unpublish toggle with one-click unpublish
- Builds on the B2 visibility model

### [ ] F2. Make the link unfurl
As a user, my shared link shows a rich preview card on Reddit and X, so it beats a screenshot.
- OG image generation per journey page; "start your own journey" CTA on the page

### [ ] F3. Show absolute amounts if I choose
As a user, I can separately toggle absolute amounts on my public page, so sharing real numbers is my explicit choice.

### [ ] F4. Paste-your-post onboarding
As a Redditor, I can paste my progress post or numbers on a public page and get a live journey page in 60 seconds, claimable by signing up.
- No-login draft page from parsed numbers; claim converts to a real account and journey page; unclaimed drafts expire

## Milestone G: Automated statement parsing

### [ ] G1. Parse CAS statements
As a user, my forwarded CAMS/KFintech CAS updates my MF and demat balances automatically after my confirmation.
- CAS parser; parsed balances flow through the existing Balance pipeline; confirm-before-write UI in the D3 inbox

### [ ] G2. Parse top bank statements
As a user, my HDFC/ICICI/SBI/Axis statements update my bank balances automatically after confirmation.
- Per-bank parsers behind a common interface; same confirm flow as G1

### [ ] G3. Parse NRI brokerage exports
As an NRI user, my foreign brokerage statements update my balances, so my whole net worth stays current.
- Format order decided by early-user demand (roadmap open question 3)
