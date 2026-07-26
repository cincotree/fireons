# Fireons Product Roadmap

## Product Thesis

Fireons (fireons.com) is an anonymous net worth tracker for India and NRIs, paired with a one-stop directory of verified finance professionals and, later, a community. Net worth tracking is the core product for anyone managing wealth across accounts and currencies. Setting a goal (a FIRE number or any other target) is an optional layer on top, and the FIRE number itself comes from a side calculator, not a required step.

FIRE communities remain the first audience and the distribution wedge: they track obsessively, share publicly, and need exactly this tool. But the product works for anyone tracking net worth, and nothing in the core flow assumes a FIRE goal.

The NRI angle fits what is already built: multi-currency accounts, USD/INR conversion, and exchange-rate history are exactly the pain of tracking wealth split across India and abroad.

## Non-Negotiable Guardrails

1. **Outside the securities-advice perimeter.** KYC, risk-profiling, and actual advice happen inside each professional's own registered channel, never on the platform.
2. **Registered-only supply.** SEBI RIA, CA/tax, AMFI MFD, IRDAI. No finfluencers, no unregistered coaches. Tax/CA is the v1 supply lane.
3. **Pull, not push.** Users browse and choose. No algorithmic matching on personal financials.
4. **Verify, not editorialize.** Confirm credentials. No paid prominence, no platform rankings.
5. **Monetization never tied to advice value.** Flat fees only (user booking fee, user verified-profile fee, professional listing fee). All deferred to Phase 5.
6. **Growth is consent-based.** The user or the community initiates; Fireons never acts on someone's data or in someone's space uninvited. No scraping, no unsolicited bots, no auto-created profiles.

## Where the Product Is Today

### Built and working

- **Backend (FastAPI + PostgreSQL):** JWT auth (register, login, me), account CRUD with hierarchy, balance snapshots, net worth summary/history/allocation, exchange rates, currency conversion. Ledger-grade data model (Transaction, Posting, Balance) exists but has no API yet.
- **App (Next.js, port 3000):** Login, register, net worth dashboard with account tree, add-account flow, net worth chart, allocation chart.
- **Marketing site (Next.js, port 3001):** Home, About FIRE, Features, For Professionals, Privacy.

### Marketing site vs reality

The site promises things that do not exist. Each row is either a Phase 1 build item or a copy cut in the truth pass (item 1.6):

| Site claim | Status |
|---|---|
| FIRE target tracking | Not built. Optional goal layer in 1.1; core is tracking itself. |
| Anonymous profiles | Partial. Username exists but email and full_name are collected, no anonymity model. Build in 1.2. |
| Directory of verified professionals | Not built. Build in 1.4. |
| "Join as an Advisor" CTA (`/register?type=professional`) | Dead end. Wire to intake in 1.6. |
| Community, sharing, feedback | Phase 3 by design. Cut from copy for now. |
| Advisor reviews and ratings | Phase 4 by design. Cut from copy for now. |
| "Anonymous consultations" | Reword: anonymous public Q&A comes in Phase 3; formal advice always happens in the professional's registered channel. |
| "End-to-end encryption", "thousands of Fireons" | Not true. Cut. |
| "Fireones" naming on several pages | Decided: Fireons. Fix. |

---

## Phase 1: Launchable v1

**Goal:** a stranger from a FIRE or personal-finance community signs up anonymously, tracks their net worth with minimal friction, optionally sets a goal, and finds a real verified professional in the directory on day one.

### 1.1 Net worth goal and progress (optional layer)

- The dashboard leads with net worth: total, trend, allocation. This works fully with no goal set.
- Optional goal on the user: target amount, currency, optional target date. Any goal, FIRE or otherwise.
- When a goal is set, the dashboard adds percent to goal, trajectory, and projected date.
- The FIRE number calculator (expenses x 25, Lean/Coast/Barista/Fat presets) is a side calculator, public and no-login, that can prefill the goal for logged-in users. It doubles as a growth front door (see growth workstream).

### 1.2 Anonymous profiles

- Username is the public handle everywhere; email is a login credential only.
- Make full_name and location optional at registration; never display them.
- Visibility model: everything private by default, with explicit per-surface opt-in. Public journey pages arrive in Phase 2, so the model must be right now.
- Session: replace the 30-minute hard JWT expiry with refresh or longer expiry.

### 1.3 Statement forwarding address (the automation foundation)

- Unique inbound address per user, shown on the profile (u-handle@statements.fireons.com). The user sets up forwarding from their bank, demat, and MF statement emails.
- Inbound receiving (SES, Mailgun, or similar), attachment extraction, encrypted storage linked to the user.
- Statements inbox in the app: see arrivals, attach a statement to an account, confirm the balance from it. Parsing is manual-assisted in v1; automation is the Phase 2 feature investment.
- Per-sender password storage (Indian statement PDFs are password-protected, typically PAN/DOB patterns).
- Privacy stance: statements carry real names and account numbers. Anonymity is public-facing; private data stays private. Say so in the privacy policy.

### 1.4 Professional directory (discovery and handoff only)

- Professional model: name, registration type (SEBI RIA, CA, AMFI MFD, IRDAI), registration number, specializations, languages, fee disclosure, external contact/booking link, verified flag.
- Verification is manual: founder checks the registration number against the public registry. No self-serve claims until Phase 4.
- Directory UI behind login: browse, filter by category and language. Neutral default ordering (alphabetical or rotation). No rankings, no sponsored slots.
- Professional profile page with the standing disclosure: advice, KYC, and payment happen in the professional's own channel; Fireons only verifies credentials.
- Booking is a handoff: outbound link or contact reveal, recorded as an event for metrics. No in-platform scheduling, chat, or payments.

### 1.5 Supply seeding (ops, launch blocker)

- Hand-recruit 10 to 20 verified professionals before launch, CA/tax lane first. An empty directory kills the reason users show up.
- Pitch: free listing at launch, motivated FIRE clientele, zero interference in their practice.
- Track the pipeline: contacted, interested, verified, live.

### 1.6 Marketing site truth pass

- Fix naming to Fireons everywhere.
- Rewrite copy to what v1 does: anonymous net worth tracking with statement-forwarding automation, optional goals (FIRE or otherwise), browse verified professionals. Lead with tracking; FIRE is the featured use case, not the product definition.
- Localize for India and NRIs: INR-first examples, Indian registration categories on For Professionals (replace CFP/CPA/RIA framing), NRI positioning (wealth across India and abroad in one place).
- Wire the professional CTA to a real intake path (an external form is fine for v1).

### 1.7 Launch hygiene

- Production deployment for backend, app, and site; real SECRET_KEY; database backups with a tested restore.
- Analytics events: signup, account added, balance updated, statement received, goal set, directory viewed, professional profile viewed, handoff clicked.
- Terms and privacy policy reflecting actual data practices and the not-an-adviser position.

### 1.8 Horizontal foundations (launch blockers, backlog milestone X)

Cross-cutting basics the feature milestones assume but nobody scheduled:

- **Account lifecycle:** password reset (does not exist today), account deletion with data export. Deletion and export are non-negotiable for a privacy-branded product and required under India's DPDP Act.
- **Transactional email:** outbound provider for reset/welcome mail (separate concern from the inbound statements pipeline).
- **India-correct display:** lakh/crore number formatting with the Indian digit grouping (1,00,00,000), INR-first currency display.
- **Mobile:** responsive pass across app and site; the audience is mobile-first and journey links will mostly be opened from Reddit on phones.
- **Operability:** error monitoring (Sentry or similar), uptime checks, structured logging.
- **Security hardening:** rate limiting on auth and inbound-email endpoints, standard security headers, dependency audit.
- **Engineering workflow:** CI running backend tests and frontend lint/build on every PR (the PR-by-PR plan depends on this), staging environment, migration discipline.

Deliberately deferred past launch: 2FA, additional languages, native/PWA app, SSO.

### 1.9 DPDP and legal compliance (backlog milestone L)

Full substantive DPDP compliance is required by May 2027; building it in now is cheap, retrofitting is not.

- Consent and notice at signup: itemized purposes, affirmative consent, consent records, withdrawal as easy as granting.
- 18+ age gate, so parental-consent obligations never apply.
- Published grievance contact and response timelines.
- Statement retention policy: raw files purged after confirmation, deletion reaches PDFs and stored passwords.
- Ops, no PRs: breach runbook (users without delay, Board within 72 hours), processor DPAs per vendor, lawyer pass on all user-facing legal text, current data map.
- Post-launch feature from a DPDP right: nominee access (L5), a genuinely loved feature in Indian finance apps.

### Build order

Dependency-ordered. A and B touch the same auth/user surface, so do them first and together. C is independent and can run in parallel with D. Recruiting (1.5) starts on day one and runs throughout. Each milestone is broken into PR-sized user stories in [BACKLOG.md](BACKLOG.md).

- [ ] **A. Optional goal and progress (1.1):** user model migration for the goal, goal API, dashboard progress when set, side FIRE calculator that prefills it
- [ ] **B. Anonymity and session (1.2):** registration changes, handle-first display, visibility model, JWT refresh
- [ ] **C. Directory (1.4):** professional model and migration, admin verify flag, directory list and filters, profile page with disclosure, handoff event
- [ ] **D. Statements (1.3):** inbound email provisioning and webhook, attachment storage, statements inbox UI, per-sender passwords, manual balance confirm
- [ ] **E. Site and launch (1.6, 1.7):** truth pass, localization, professional intake, analytics, production deploy, terms and privacy
- [ ] **X. Horizontal foundations (1.8):** CI first (everything else lands PR by PR on top of it), then password reset, account deletion/export, lakh/crore formatting, mobile pass, monitoring, rate limiting
- [ ] **L. Compliance (1.9):** consent and notice at signup, 18+ gate, grievance page, statement retention; breach runbook and lawyer pass as ops
- [ ] **Ops throughout (1.5):** recruit and verify 10 to 20 professionals

**Exit criteria:** live product, 15+ verified professionals listed, and a user can complete the full loop: sign up, add accounts, set up statement forwarding, optionally set a goal, browse the directory, click through to a professional.

---

## Phase 2: Validate with Real Users

**Goal:** evidence that both loops work before building the community layer.

### Build (the only feature work of this phase)

- **Public journey links (the growth loop).** Opt-in public page at fireons.com/u/handle: net worth trend, milestones, allocation in percentages, and percent to goal when one is set. No absolute amounts unless separately toggled on. No login to view. Rich OG preview so links unfurl well on Reddit. Quiet "start your own journey" CTA on every page. Built for the r/FIRE_Ind progress-post genre: a live link with a chart beats a screenshot.
- **Paste-your-post onboarding.** Public, no-login page: paste your Reddit progress post or numbers, get a live journey page in 60 seconds, claim it by signing up. Consent by construction: the user acts, not a bot.
- **Automated statement parsing.** Turn the statements inbox into automatic balance updates. Format order: CAMS/KFintech CAS first (MF and demat in one statement), then top banks (HDFC, ICICI, SBI, Axis), then NRI brokerage exports. Parsed balances flow through the existing balance-snapshot pipeline with a user confirm step.
- Small friction fixes only, beyond these three.

### Learn

- **Distribution is the main work of this phase.** Founder shows up daily in FIRE India and NRI communities (see growth workstream).
- Watch the funnel: signup, account added, second net worth update (the retention signal), statement forwarding set up, goal set, directory view, handoff click.
- Talk to every early professional: are handoffs real, are users qualified, would they pay a flat listing fee later.
- Talk to early users: is the tracker sticky weekly, did the directory influence signup, what blocks booking.

**Exit criteria (set the actual numbers before launch):** a meaningful cohort updates net worth in week 2+, directory-to-handoff clicks happen without prompting, a handful of confirmed real engagements between users and professionals, and journey links get shared in FIRE communities by users other than the founder.

**Kill/pivot signal:** users track but never touch the directory, or professionals see zero qualified interest. Either finding changes Phases 3 to 5.

---

## Phase 3: Anonymous Community Layer

**Goal:** turn tracking into a social loop, only after Phase 2 shows usage.

- Bring the public journey pages inside: on-platform discussion, comments, and encouragement attached to journeys users already share externally.
- Reddit-style threads: milestones, strategy questions, progress updates, community comments and voting.
- **Professionals participate in public threads** under their real, badged identity, responding to anonymously posted questions with general guidance that doubles as their pitch. Discovery earned through useful answers, not paid placement.
- The safety line, stated on every thread a professional joins and enforced: public responses stay general and educational; anything personalized to an individual's financials moves to the professional's registered channel (KYC, risk profiling, formal advice all live there).
- Moderation from day one of this phase: no unregistered users giving investment advice, spam and shill controls, report flow.
- IT Rules 2021 intermediary duties arrive with user content: published community rules, grievance officer with 24-hour acknowledgment and 15-day resolution, takedown process. The L3 grievance surface extends to cover this.
- Cohort views, opt-in and aggregated: compare progress against similar targets without exposing individuals.

**Exit criteria:** sharing and discussion happen weekly without founder prompting; moderation load is understood.

---

## Phase 4: Grow and Curate Professional Supply

**Goal:** from hand-recruited supply to a scalable, still-curated marketplace.

- Self-serve professional onboarding: registration-number intake, document upload, verification queue with an internal review tool. Verification stays a human decision; automation assists.
- Re-verification cadence: annually and on registry changes.
- Reviews and ratings, carefully: verified-engagement reviews only (requires a recorded handoff), anonymous reviewer handles, professional right of reply. Neutral display: no composite rankings, no "top advisor" lists; filter and sort by objective facts only.
- Richer profiles: specialization taxonomy, self-declared expertise tags labeled as self-declared.
- Expand supply lanes beyond CA/tax in the order Phase 2 demand data suggests.
- Structured "request contact" handoff with user consent, still pull-based, still outside the advice perimeter.
- Resolve the deferred lawyer questions before reviews and scaled onboarding ship.

**Exit criteria:** professionals join and get verified without founder involvement; directory breadth covers what users actually search for.

---

## Phase 5: Monetization

**Goal:** revenue from the three mapped non-advice streams.

1. **Professional flat listing fee** first: simplest, clearest value. Same price within a tier, no placement benefits, founding professionals grandfathered.
2. **User booking fee**: flat, user-side, per structured handoff (requires Phase 4 handoff flow).
3. **User verified-profile fee**: optional paid verification of the user's own profile for community credibility.

Pricing validated in the Phase 2/4 professional conversations before any billing is built. Fees collected through a licensed payment aggregator (Fireons never handles the flow directly); GST registration for platform fees.

**Exit criteria:** paying professionals renew; fees do not distort directory neutrality.

---

## Standing Workstream: Distribution and Growth

Runs through every phase, and is explicitly the hard part. Every idea here passes guardrail 6: the user or the community initiates, never Fireons uninvited.

### Foundation (Phase 1-2)

- Founder shows up daily as a genuine member in r/FIRE_Ind, r/FIREIndia, r/IndiaInvestments, NRI forums, and X/Twitter FIRE circles, building in public with his own journey page and monthly progress posts.
- Public journey links are the core loop: users post their own progress with a live Fireons link instead of a screenshot. Respect each subreddit's self-promotion rules.
- Paste-your-post onboarding collapses the gap between "I posted my update" and "I have a Fireons page."
- The directory is the differentiator in every pitch: the one place with only registered, verified professionals.

### Free tools as front doors (no login, shareable results)

- FIRE number calculator (the 1.1 side calculator): expenses x 25, Lean/Coast/Barista/Fat presets, INR-first with USD toggle; prefills the in-app goal for logged-in users. Ships with Phase 1 (backlog A3).
- Phase 2 suite (backlog H1-H4): time-to-goal, net worth in INR today (reuses the conversion backend), two-country FI target, returning-to-India cost model. Underserved NRI niche, high shareability.
- Every tool output is a shareable card and link with a quiet "track this for real" CTA. These pages are also the SEO surface.

### Content engine: blog (from Phase 1-2, compounds forever)

- Blog at fireons.com/blog targeting FIRE India and NRI keywords.
- Topic discovery from Reddit, writing always original: recurring sub questions are the headline map ("How much do I need to FIRE in India?", "Should NRIs count a US 401k in their India FI number?"). Quote threads briefly with attribution; never republish an individual's story or numbers as the post.
- Featured journeys by permission: DM the poster, get a yes, tell the story properly, offer them a journey page.
- Content mix over time: evergreen SEO guides first, thread-roundup commentary as presence grows, data posts from opted-in aggregates after Phase 3, educational guest posts by verified professionals (visibility earned by writing; general education, never advice).
- Every post exits to a relevant tool or the journey-page flow, not a generic signup pitch.

### Share mechanics (Phase 2-3)

- Progress card image generator for subs where image posts beat links, watermarked fireons.com.
- Milestone cards at 10/25/50/75 percent of target: a ready-to-post Reddit draft the user can share or ignore.
- Opt-in benchmark stat ("ahead of X percent of Fireons with similar targets") once the base is big enough for it to be honest.
- Claim-your-handle scarcity at launch: short anonymous handles go to early signups.

### Community-earned presence (Phase 3-4)

- Founder-posted anonymized aggregate insights (median savings rate of NRI Fireons, allocation trends by age band), sourced only from opted-in aggregates.
- Mod-sanctioned tools: once traction is real, offer the journey-page generator and calculators to subreddit mods as community resources. Sanctioned beats stealth.
- Verified professionals share their public Q&A threads with their own audiences.

## Deliberately Not Building

- Any advice, recommendations, or portfolio suggestions inside the platform.
- Algorithmic matching of users to professionals based on their financials.
- Paid placement, sponsored profiles, or platform rankings.
- In-platform KYC, risk profiling, payments for advice, or advice chat.
- Account aggregation/bank linking. Statement forwarding is the chosen path: user-controlled, credential-free, and it covers NRI foreign accounts that the Indian AA ecosystem does not. Revisit only if forwarding proves insufficient.
- Growth bots or scraping: no auto-created profiles from others' posts, no unsolicited bot comments. Considered and rejected; it inverts the trust the brand depends on and burns the communities distribution relies on.

## Open Questions

1. Phase 2 success thresholds: pick the actual numbers (signups, week-2 retention, handoff clicks) before launch.
2. Deferred lawyer questions: resolve no later than the start of Phase 4. Add to the list: boundary rules for professionals posting general guidance in public threads (Phase 3).
3. Statement parsing order in Phase 2: confirm with early users whether CAS or bank statements matter more (assumed CAS first; one statement covers MF and demat).
4. Inbound email provider for 1.3 (SES vs Mailgun vs alternative): decide when building milestone D.

## Risk Register

| Risk | Phase | Mitigation |
|---|---|---|
| Empty directory at launch | 1 | Supply seeding is a launch blocker, not a fast follow |
| DPDP/privacy obligations unmet at launch | 1 | Milestone L (consent, age gate, grievance, retention) plus X3 deletion/export; full compliance deadline May 2027 |
| Marketing site overpromises | 1 | Truth pass before any distribution push |
| Statement inbox holds sensitive documents | 1 | Encrypted storage, strict access controls, clear privacy policy, delete on request |
| Tracker retention weak (manual entry fatigue) | 1-2 | Forwarding address in Phase 1, automated parsing in Phase 2 |
| Public journey pages leak identity | 2 | Opt-in only, anonymous handle, no absolute amounts by default, one-click unpublish |
| Professional replies drift into personalized advice | 3 | General-guidance rule stated on every thread and enforced; personalized advice moves to the registered channel |
| Community becomes an unregistered advice channel | 3 | Moderation rules and enforcement ship with the feature |
| Reviews drift into editorializing/rankings | 4 | Verified-engagement reviews, neutral display, no composite rankings |
| Monetization distorts neutrality | 5 | Flat fees only, no placement benefits, grandfathered founders |
