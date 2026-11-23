import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import LumpsumFireCalculator from '@/components/LumpsumFireCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'Lumpsum Calculator for FIRE - Fireons',
  description: 'See whether a one-time lumpsum investment will actually get you to your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Lumpsum Calculator for FIRE - Fireons',
    description: 'See whether a one-time lumpsum investment will actually get you to your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Lumpsum Calculator for FIRE - Fireons',
    description: 'See whether a one-time lumpsum investment will actually get you to your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.',
  },
};

export default function LumpsumFireCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">Lumpsum Calculator for FIRE</h1>
          <p className="text-xl text-blue-100">
            Got a one-time lumpsum to invest — a bonus, an inheritance, an ESOP payout? See if it&apos;s enough to
            hit your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <LumpsumFireCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="lumpsum-for-fire" title="Lumpsum Calculator for FIRE" />
      </section>

      {/* Explainer */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-4">How this calculator works</h2>
          <p className="text-slate-600 leading-relaxed">
            If you&apos;ve got a one-time sum to invest — a bonus, an inheritance, an ESOP payout — this calculator
            checks whether investing it today, left to compound with no further contributions, is enough to reach
            your FIRE number by your target age. It also tells you the age you&apos;d actually reach FI at that
            amount, or how much you&apos;d need to invest today instead to hit your target age exactly.
          </p>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: "Does this assume I'll add more money later?",
            answer:
              "No — it assumes a single one-time investment today with no further contributions, compounding purely from growth. If you're also planning to invest monthly on top of this, check the SIP-for-FIRE calculator for that scenario, or combine the two amounts in the Retirement Calculator's current savings field.",
          },
          {
            question: "What if I don't know my FIRE number yet?",
            answer:
              'Work it out first using the Retirement Calculator or the FIRE Number by City calculator, then come back here with that number to check your lumpsum against it.',
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
