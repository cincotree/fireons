import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import PpfCalculator from '@/components/PpfCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'PPF Calculator for FIRE - Fireons',
  description: 'See how much your PPF (Public Provident Fund) alone will grow to, and how much of your FIRE number it covers — entirely in your browser, nothing is sent anywhere.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'PPF Calculator for FIRE - Fireons',
    description: 'See how much your PPF (Public Provident Fund) alone will grow to, and how much of your FIRE number it covers — entirely in your browser, nothing is sent anywhere.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'PPF Calculator for FIRE - Fireons',
    description: 'See how much your PPF (Public Provident Fund) alone will grow to, and how much of your FIRE number it covers — entirely in your browser, nothing is sent anywhere.',
  },
};

export default function PpfCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">PPF Calculator</h1>
          <p className="text-xl text-blue-100">
            See how much your PPF alone will grow to, and how much of your FIRE number it covers — entirely in your
            browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <PpfCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="ppf" title="PPF Calculator for FIRE" />
      </section>

      {/* Explainer */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-4">How this calculator works</h2>
          <p className="text-slate-600 leading-relaxed">
            The Public Provident Fund (PPF) is a government-backed savings scheme with a fixed 15-year lock-in
            (extendable in 5-year blocks), a government-declared interest rate, and an annual contribution cap. This
            calculator projects your PPF balance forward using your planned annual contribution and the current
            interest rate, compounding annually.
          </p>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'What is the maximum I can contribute to PPF each year?',
            answer:
              '₹1,50,000 per financial year — the calculator automatically caps your input at that limit if you enter more.',
          },
          {
            question: 'Can I withdraw from PPF before 15 years?',
            answer:
              "Partial withdrawals are allowed from the 7th year onward under specific conditions, and the account can be extended in 5-year blocks after maturity. This calculator doesn't model partial withdrawals — it assumes contributions continue undisturbed to your target age.",
          },
        ]}
      />

      {/* CTA */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Want to track your actual progress?</h2>
          <p className="text-xl text-gray-600 mb-8">
            Join Fireons to track your real net worth toward this goal, not just a one-time estimate
          </p>
          <Link
            href={appRoutes.waitlist}
            className="inline-block bg-blue-800 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-900 transition-colors shadow-lg"
          >
            Join the Waitlist
          </Link>
        </div>
      </section>
    </div>
  );
}
