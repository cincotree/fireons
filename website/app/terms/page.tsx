import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes, config } from '@/lib/config';

export const metadata: Metadata = {
  title: 'Terms of Service - Fireons',
  description: 'The terms that apply when you use the Fireons website, calculators and net worth tracker.',
};

const lastUpdated = '22 November 2026';

const sections = [
  {
    title: 'Who we are and what these terms cover',
    body: [
      'Fireons is a free set of financial independence calculators, a net worth tracker and a directory of publicly listed financial professionals. These terms apply to the Fireons website and the Fireons app. By using either, you agree to them.',
      'If you do not agree, please do not use Fireons.',
    ],
  },
  {
    title: 'Not financial advice',
    body: [
      'Everything on Fireons is for information and planning only. Calculator results are estimates based on the numbers and assumptions you enter, and real returns, inflation, taxes and costs will differ.',
      'Fireons is not a registered investment adviser, research analyst, tax adviser or lawyer, and nothing here is a recommendation to buy, sell or hold any investment. Speak to a qualified professional before making financial decisions.',
    ],
  },
  {
    title: 'Your account',
    body: [
      'You sign in with a Google or Reddit account. You are responsible for that account and for everything done through your Fireons session.',
      'You must be at least 18 years old to use the net worth features. Give us accurate information and tell us if you think someone else has access to your account.',
      'We can decline or close an account that does not follow these terms.',
    ],
  },
  {
    title: 'Your data',
    body: [
      'You own the financial information you add or upload, such as account balances and statements. You give Fireons permission to process it only to provide the features you use, including reading the statements you upload and calculating your net worth.',
      'Net worth data is collected only after you agree to our notice, and you can withdraw that agreement at any time from the privacy page in the app. Withdrawing deletes your accounts, balances and uploaded documents. How we handle your information is described in our Privacy Policy.',
      'Only upload documents that belong to you or that you are entitled to share.',
    ],
  },
  {
    title: 'Acceptable use',
    body: [
      'Do not misuse Fireons. In particular, do not break the law, try to access another person\'s data, probe or disrupt the service, upload malware, or use automated tools to copy the service or the professional directory in bulk.',
      'We may limit how much you can upload or how often you can make requests to keep the service fast and fair for everyone.',
    ],
  },
  {
    title: 'Financial professionals directory',
    body: [
      'The directory lists publicly available registration details of financial professionals collected from public registers and other public sources. We try to keep it accurate, but it can be out of date or incomplete, and a listing is not an endorsement, a recommendation or a guarantee of a professional\'s standing.',
      'Check a professional\'s current registration with the relevant regulator before you engage them. Any arrangement is between you and that professional, and Fireons is not a party to it.',
    ],
  },
  {
    title: 'Third-party services',
    body: [
      'Fireons relies on services such as Google and Reddit for sign-in and on AI services to read statements you upload. We do not control these services and they have their own terms.',
      'Calculators that use exchange rates or other external data may show figures that are delayed or wrong.',
    ],
  },
  {
    title: 'Our content',
    body: [
      'The Fireons name, logo, design and the text and code of the service belong to Fireons or its licensors. You may use the calculators and share your own results, but you may not copy or resell the service.',
    ],
  },
  {
    title: 'Availability and changes to the service',
    body: [
      'Fireons is provided as is and as available. We may change, pause or stop any feature, and the service may be interrupted by faults or maintenance. Please keep your own copies of anything important.',
    ],
  },
  {
    title: 'Limits on our responsibility',
    body: [
      'To the extent the law allows, Fireons is not liable for any loss that comes from using or being unable to use the service, including decisions you make based on calculator results, errors in extracted statement data or the directory, or loss of data.',
      'Nothing in these terms limits any right or liability that cannot be limited by law.',
    ],
  },
  {
    title: 'Ending your use',
    body: [
      'You can stop using Fireons at any time and delete your net worth data from the privacy page in the app. We may suspend or end access if you break these terms or if we need to protect the service or other users.',
    ],
  },
  {
    title: 'Changes to these terms',
    body: [
      'We may update these terms. The date at the top shows the latest version, and if a change is significant we will tell you in the app or on the site. Using Fireons after a change means you accept the new terms.',
    ],
  },
  {
    title: 'Governing law',
    body: [
      'These terms are governed by the laws of India, and the courts of India have jurisdiction over any dispute about them.',
    ],
  },
];

export default function Terms() {
  return (
    <div className="bg-white">
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">Terms of Service</h1>
          <p className="text-xl text-blue-100">The rules for using Fireons, in plain language</p>
          <p className="text-sm text-blue-100 mt-4">Last updated {lastUpdated}</p>
        </div>
      </section>

      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-amber-50 border border-amber-200 p-6 rounded-lg mb-12">
          <p className="text-gray-700">
            <strong>Fireons does not give financial advice.</strong> Calculators and tools are for
            planning only. Please see a qualified professional before you act on any result.
          </p>
        </div>

        <div className="space-y-10">
          {sections.map((section, index) => (
            <div key={section.title}>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                {index + 1}. {section.title}
              </h2>
              <div className="space-y-4">
                {section.body.map((paragraph) => (
                  <p key={paragraph} className="text-gray-700">
                    {paragraph}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            {sections.length + 1}. Contact
          </h2>
          <p className="text-gray-700">
            Questions about these terms can be sent to{' '}
            {config.privacyContactEmail ? (
              <a
                href={`mailto:${config.privacyContactEmail}`}
                className="text-cyan-700 underline hover:text-cyan-800"
              >
                {config.privacyContactEmail}
              </a>
            ) : (
              'our support team through the Fireons website'
            )}
            .
          </p>
        </div>

        <p className="text-gray-700 mt-12">
          Read how we handle your information in our{' '}
          <Link href="/privacy" className="text-cyan-700 underline hover:text-cyan-800">
            Privacy Policy
          </Link>
          .
        </p>
      </section>

      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Ready to get started?</h2>
          <p className="text-xl text-gray-600 mb-8">
            Join Fireons and take control of your financial future
          </p>
          <Link
            href={appRoutes.join}
            className="inline-block bg-blue-800 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-900 transition-colors shadow-lg"
          >
            Join Fireons
          </Link>
        </div>
      </section>
    </div>
  );
}
