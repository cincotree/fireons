const CONTACT_EMAIL = process.env.NEXT_PUBLIC_PRIVACY_CONTACT_EMAIL;

export function NetWorthNotice({ version }: { version: string }) {
  return (
    <div className="space-y-5 text-sm text-gray-700" data-testid="net-worth-notice">
      <section>
        <h3 className="font-semibold text-gray-900">1. What we collect</h3>
        <ul className="mt-1 list-disc pl-5 space-y-1">
          <li>
            Account details you give us: account and institution names, account numbers, balances,
            holdings, loans, deposits, insurance and retirement figures, and the dates they relate to.
          </li>
          <li>
            The documents you upload (for example bank, loan, mutual fund, demat, EPF, NPS or
            insurance statements) and the figures we extract from them.
          </li>
          <li>Your sign-in details from Google or Reddit, so we know which data is yours.</li>
        </ul>
        <p className="mt-2">
          Statements can contain details of other people, such as joint holders or people you paid.
          Upload only documents that are yours or that you are allowed to share. We never ask for
          the passwords to your bank or broker accounts.
        </p>
      </section>

      <section>
        <h3 className="font-semibold text-gray-900">2. Why we collect it</h3>
        <p className="mt-1">
          Only to calculate and show you your own net worth, its breakdown and how it changes over
          time. We do not use it to advertise to you, to rank or recommend professionals, or for any
          other purpose without asking you separately.
        </p>
      </section>

      <section>
        <h3 className="font-semibold text-gray-900">3. Who handles it for us</h3>
        <ul className="mt-1 list-disc pl-5 space-y-1">
          <li>Anthropic, directly or through OpenRouter, to read the text of documents you upload and extract figures from it.</li>
          <li>Amazon Web Services, to host the application.</li>
          <li>Neon, to store the database.</li>
        </ul>
        <p className="mt-2">
          They process your data only to run Fireons for us. Some of them are outside India, and if
          you live outside India your data also travels between your country and theirs. We do not
          sell your data and do not share it with advertisers, lenders, insurers or the professionals
          listed in our directory.
        </p>
      </section>

      <section>
        <h3 className="font-semibold text-gray-900">4. How long we keep it</h3>
        <p className="mt-1">
          Uploaded files are deleted as soon as they have been read. The figures extracted from them
          and the balances you enter stay until you delete them or withdraw consent. When you
          withdraw, we erase them straight away. Copies in backups disappear as the backups expire.
          We keep a record of your consent choices, without any financial data, as proof of what you
          agreed to.
        </p>
      </section>

      <section>
        <h3 className="font-semibold text-gray-900">5. Your choices and rights</h3>
        <ul className="mt-1 list-disc pl-5 space-y-1">
          <li>
            You can withdraw consent at any time on the Privacy page. We then stop processing and
            erase your net worth data. What we did before you withdrew stays lawful.
          </li>
          <li>
            You can ask to see, correct or erase your data, or to nominate someone to act for you.
            We reply within 30 days.
          </li>
          <li>
            If we do not resolve a complaint, you can take it to the Data Protection Board of India.
            If you live in the EU or UK you can also complain to your local data protection
            authority.
          </li>
        </ul>
      </section>

      <section>
        <h3 className="font-semibold text-gray-900">6. Security and breaches</h3>
        <p className="mt-1">
          Data is encrypted in transit and access is limited to what running Fireons needs. If a
          breach affects your data we will tell you without delay what happened, what it may mean
          for you and what we are doing about it.
        </p>
      </section>

      <section>
        <h3 className="font-semibold text-gray-900">7. Contact and age</h3>
        <p className="mt-1">
          {CONTACT_EMAIL ? (
            <>
              Questions, requests and complaints: <a className="text-blue-600 underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.{" "}
            </>
          ) : null}
          Net worth features are for people aged 18 or over.
        </p>
      </section>

      <p className="text-xs text-gray-500">Notice version {version}.</p>
    </div>
  );
}
