# Net worth data: consent notice (drafting notes)

The notice shown to users lives in `frontend/src/components/NetWorthNotice.tsx` and is built as described in CLAUDE.md. This file keeps the longer draft, the outside-India addendum (not built) and the open questions.

Not legal advice. Items in [square brackets] are decisions or facts to fill in before a lawyer reviews this. Written to meet India's DPDP Act 2023 and Rules 2025, the IT Act SPDI Rules 2011 that apply today, and, for users outside India, GDPR and UK GDPR style expectations.

## How it is shown in the app

- Shown once, on its own screen, before the first statement upload or manual balance entry. Not part of the Terms of Service and not implied by signing in.
- One unticked checkbox per purpose, plus an "I agree and continue" button that stays disabled until the required one is ticked.
- The required consent covers only what the net worth feature needs. Everything else is a separate optional checkbox that is off by default.
- Each consent is stored with user id, notice version, purposes ticked, timestamp and the user's country. Withdrawal is stored the same way.
- Shown again when the notice changes in a material way.
- "Withdraw consent" and "Delete my data" are in Settings, one click away, and as easy as agreeing was.

## The notice

**Your net worth data and how Fireons uses it**

[Company legal name] ("Fireons", "we") needs your permission before we collect and process the financial information below. You can use other parts of Fireons without giving it.

**1. What we collect**
- Account details you give us: account names, institution names, masked or full account numbers, balances, holdings, loans, deposits, insurance and retirement figures, and the dates they relate to.
- The documents you upload (for example bank, loan, mutual fund, demat, EPF, NPS or insurance statements) and the figures we extract from them.
- Your sign-in details from Google or Reddit (name, email if provided, and an account identifier) so we know which data is yours.

Statements can contain details of other people, such as joint holders or people you paid. Upload only documents that are yours or that you are entitled to share. We do not ask for passwords to your bank or broker accounts.

**2. Why we collect it**
Only to calculate and show you your own net worth, its breakdown and its change over time. We do not use it to advertise to you, rank or recommend professionals, or for any other purpose without asking you separately.

**3. Who handles it for us**
We use these service providers to run Fireons. They process your data only on our instructions.
- Anthropic, to read document text and extract figures. [Confirm: what is sent (full text or excerpts), whether it is retained or used for training under our agreement, location.]
- Amazon Web Services, [region, currently Singapore], to host the application.
- Neon, [region], to store the database.
- [Any email, logging or analytics provider.]

Some of these are outside India. If you are outside India, your data also moves to and from where you live. [Add safeguards, for example contractual protections, once confirmed.] We do not sell your data and do not share it with advertisers, lenders, insurers or the professionals listed in our directory.

**4. How long we keep it**
- Uploaded files: [deleted after extraction, or kept N days].
- Extracted figures and balances: until you delete them or withdraw consent, then erased within [N] days.
- Records we must keep by law, such as consent logs and security logs, for as long as the law requires, [at least one year for logs under the DPDP Rules].

**5. How we protect it**
[Encryption in transit and at rest, access controls, logging, tested backups. Confirm each before publishing.] If a breach affects your data we will tell you without delay, what happened, what it may mean for you, what we are doing, and who to contact.

**6. Your choices and rights**
- Withdraw consent at any time in Settings > Privacy. We then stop processing and erase your net worth data, unless a law requires us to keep part of it. Withdrawing does not affect what we did before.
- Ask to see, correct, update or erase your data, or to nominate someone to exercise these rights if you die or cannot act. We reply within [30] days and in any case within the period the law sets.
- Complain to us first. If we do not resolve it, you can complain to the Data Protection Board of India. If you live in the EU or UK you can complain to your local data protection authority.

**7. Contact**
[Name or title], [email], [postal address]. [Grievance officer details as required in India. Data Protection Officer details if appointed.]

**8. Age**
Net worth features are for people aged 18 or over.

**9. Notice version**
Version [1.0], effective [date]. Earlier versions are available on request.

## Consent checkboxes

Required:
- [ ] I agree that Fireons may collect and process the financial information and documents I provide, in the ways described in this notice, to calculate and show my net worth. I am 18 or over, and the documents I upload are mine or I am allowed to share them.

Optional, each off by default:
- [ ] Use my de-identified data to improve how statements are read. [Only include if you actually do this.]
- [ ] Email me about my net worth summary. [Only include if you actually do this.]

## Short addendum for users outside India

Show this only when the user's country is not India. Wording to adapt per region with counsel.
- EU and UK: state the legal basis (consent for this feature), name the transfer safeguards for sending data to India and other countries, add the right to restrict processing and to data portability, and name an EU or UK representative if the law requires one.
- US (for example California): say you do not sell or share personal information, and list the rights to know, delete and correct.
- UAE, Singapore and others: confirm local consent and transfer rules before launching to those users.
- NRIs generally: say which country's law you will follow if it gives them stronger rights than this notice.

## Open points for counsel

1. Whether the SPDI Rules consent form requirements (written consent for sensitive financial data) apply until DPDP duties start, and what that means for the checkbox record.
2. Whether any country restriction on transfers has been notified under the DPDP Rules.
3. Which foreign laws actually apply to NRI users given where Fireons is offered and marketed.
4. Whether giving any personalised recommendation from net worth data would bring SEBI investment adviser rules into scope.
5. Retention periods, breach contacts and the exact vendor terms above, which only you can confirm.
