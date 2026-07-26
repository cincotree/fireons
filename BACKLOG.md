# Fireons Build Backlog

User stories sized so that each story is one PR. Ordered within milestones; milestones come from the build order in [ROADMAP.md](ROADMAP.md). A and B first (same auth/user surface), C and D in parallel after, E last. Phase 2 stories (F, G) start only after Phase 1 ships.

Status: `[ ]` not started, `[~]` in progress, `[x]` merged.

---

## Milestone A: Optional goal and progress (roadmap 1.1)

Net worth tracking is the core and already works; the goal is an optional layer, and the FIRE number comes from a side calculator.

### [ ] A1. Set an optional net worth goal
As a user, I can optionally set a goal (amount, currency, optional target date), FIRE or otherwise, so my tracking can have a target. The dashboard works fully without one.
- Migration adds goal fields to User; API to set/update/clear the goal; validation (positive amount, supported currency)
- Settings UI to enter or clear the goal
- Touchpoints: `backend/database/models.py`, `backend/alembic`, new `backend/api/goal_api.py` or extend auth/me, `frontend/src/app/networth`

### [ ] A2. See my progress when a goal is set
As a user with a goal, I see percent to goal, trajectory, and projected date on my dashboard; without a goal the dashboard leads with net worth trend and allocation as it does today.
- Progress computed from existing net worth history and the A1 goal; extend `/summary` or add a progress endpoint
- Dashboard progress module renders only when a goal exists
- Touchpoints: `backend/api/account_api.py` (summary), `frontend/src/components/NetWorthDashboard.tsx`

### [ ] A3. FIRE number side calculator (public, launch calculator #1)
As a visitor, I can calculate my FIRE number (annual expenses x 25, Lean/Coast/Barista/Fat presets, INR-first with USD toggle) without logging in; as a logged-in user, one click sets the result as my A1 goal.
- Lives on the marketing site for SEO; shareable result link; "set as my goal" deep link into the app prefilling A1
- Touchpoints: `website/app` (new calculator page), `frontend` goal prefill route

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

### [ ] E2. User analytics
As the founder, I can see the funnel and usage, so Phase 2 validation has data.
- Pick and integrate a product analytics provider (PostHog recommended over GA: event-level funnels, self-serve, EU/India hosting options); wire frontend page/event tracking and backend events
- Events: signup, account added, balance updated, statement received, goal set, calculator used, directory viewed, professional profile viewed, handoff clicked
- Funnel and retention dashboards for the Phase 2 exit criteria

### [ ] E3. Production launch
As a user, I can use Fireons at fireons.com securely.
- Production deploy of backend, app, site; real SECRET_KEY; database backups; terms and privacy policy reflecting actual practices and the not-an-adviser position

## Milestone X: Horizontal foundations (roadmap 1.8, launch blockers)

X1 comes first so every other story lands through CI. The rest can interleave with milestones A through E.

### [ ] X1. CI pipeline
As a developer, every PR runs backend tests and frontend lint/build automatically, so the PR-by-PR plan stays safe.
- GitHub Actions: backend pytest, frontend and website lint plus build; required checks on main
- Touchpoints: `.github/workflows`, existing `backend/tests`, `e2e-tests`

### [ ] X2. Password reset
As a user, I can reset my password by email, so a forgotten password does not lock me out of my financial data forever.
- Outbound transactional email provider (separate from inbound statements); reset token flow; rate limited
- Touchpoints: `backend/api/auth_api.py`, `backend/auth_utils.py`, new frontend reset pages

### [ ] X3. Delete my account and export my data
As a user, I can export my data (accounts, balances, statements) and permanently delete my account, so I stay in control.
- Export as CSV/JSON bundle; hard delete of user data including stored statements; required for the privacy positioning and India DPDP Act
- Touchpoints: `backend/api/auth_api.py`, account/statement repositories, settings UI

### [ ] X4. Indian number formatting
As an Indian user, I see amounts in lakh/crore with Indian digit grouping (1,00,00,000) wherever INR is displayed, so numbers read naturally.
- Shared formatting utility across dashboard, charts, calculators, and journey pages; USD keeps western grouping

### [ ] X5. Mobile responsiveness pass
As a mobile user, the app, site, and public journey pages work well on a phone, since most traffic arrives from Reddit on mobile.
- Audit and fix dashboard, charts, tables, directory, and calculators at small breakpoints

### [ ] X6. Monitoring and hardening
As the founder, I know when production breaks and the obvious abuse paths are closed.
- Error monitoring (Sentry or similar) on backend and frontends; uptime check; rate limiting on auth and inbound-email endpoints; security headers; dependency audit

## Milestone L: DPDP and legal compliance (roadmap 1.9, launch blockers except L5)

Engineering side of DPDP readiness; the lawyer pass blesses the words. X3 (deletion/export) and X6 (security safeguards) already carry the heavy items.

### [ ] L1. Consent and notice at signup
As a new user, I see a plain-language, itemized notice of what data is collected and for which purpose, and I consent by clear affirmative action, so processing is lawful under DPDP.
- Separate consent per purpose: tracking, statement ingestion, analytics; no bundling; consent records stored with timestamp and notice version; withdrawal toggles in settings as easy as granting
- Touchpoints: `backend/api/auth_api.py`, User consent fields and migration, `frontend/src/app/register`, settings UI

### [ ] L2. 18+ age gate
As the platform, registration requires confirming 18+, so verifiable parental consent obligations never apply.
- Age confirmation at signup, terms clause, block under-18 declarations

### [ ] L3. Grievance contact and response timelines
As a user, I can find a published grievance contact and stated response timelines, so I know how to exercise my DPDP rights.
- Grievance page on the site, contact routing, documented internal SLA; doubles as the IT Rules grievance surface when Phase 3 community ships

### [ ] L4. Statement retention policy
As a user, raw statement files are deleted automatically after a defined window once balances are confirmed, and X3 account deletion reaches stored PDFs and per-sender passwords, so my most sensitive documents are not retained indefinitely.
- Configurable retention window, scheduled purge job, retention stated in the privacy policy
- Touchpoints: statement storage layer, X3 deletion flow

### [ ] L5. Nominee (post-launch, pairs well with Phase 2)
As a user, I can name a nominee who can exercise my rights if I die or am incapacitated, so my family is not locked out of my financial records.
- DPDP nomination right turned into a product feature; nominee details, verification flow on claim

## Compliance ops (no PRs)

- Breach incident runbook before launch: who assesses, who notifies affected users without delay, who files to the Data Protection Board within 72 hours.
- Processor contracts (DPAs) collected as vendors are chosen: hosting, inbound/outbound email, analytics, error monitoring.
- Lawyer pass before launch: consent notice text, terms, privacy policy, professional listing agreement, calculator disclaimers.
- Data map kept current: what personal data lives where, including cross-border locations.

## Ops throughout (roadmap 1.5, no PRs)

- Recruit 10 to 20 CA/tax professionals; pipeline tracked as contacted, interested, verified, live. Launch blocker: 15+ live before announcing.

---

## Phase 2 build stories (start only after Phase 1 ships)

## Milestone F: Public journey pages

### [ ] F1. Publish my journey
As a user, I can publish an opt-in public page at fireons.com/u/handle showing my net worth trend, milestones, allocation percentages, and percent to goal when I have one, so I can share my progress.
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

## Milestone H: Public calculator suite (growth front doors)

All public and no-login, on the marketing site for SEO, each with a shareable result link and a quiet CTA into the app. The FIRE number calculator (A3) launches with Phase 1; these follow during Phase 2, one PR each.

### [ ] H1. Time-to-goal calculator
As a visitor, I enter current net worth, monthly savings, and expected return, and see when I reach a given target, so I can sanity-check my plan.
- Signed-in follow-up: prefill from my actual numbers

### [ ] H2. Net worth in INR today
As an NRI visitor, I enter balances in multiple currencies and see my consolidated net worth in INR (or USD), so I get instant value before signing up.
- Uses the existing exchange-rate/conversion backend via a public read-only endpoint

### [ ] H3. Two-country FI target
As an NRI visitor, I can model an FI target split across India and my resident country (different expense bases and inflation), so my number reflects where I will actually live.

### [ ] H4. Returning-to-India cost model
As an NRI visitor, I can model what my current corpus supports if I return to India, so I can evaluate the move.
- Ship last; needs the most careful assumptions and disclaimers (educational tool, not advice)
