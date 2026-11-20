import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import CityFireCalculator from '@/components/CityFireCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'FIRE Number by City Calculator - Fireons',
  description: 'See your FIRE number based on the cost of living in your city — entirely in your browser, nothing is sent anywhere.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'FIRE Number by City Calculator - Fireons',
    description: 'See your FIRE number based on the cost of living in your city — entirely in your browser, nothing is sent anywhere.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FIRE Number by City Calculator - Fireons',
    description: 'See your FIRE number based on the cost of living in your city — entirely in your browser, nothing is sent anywhere.',
  },
};

export default function CityFireCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">FIRE Number by City</h1>
          <p className="text-xl text-blue-100">
            Your FIRE number depends on where you retire. Pick from popular Indian retirement destinations — Goa,
            the hills, the backwaters — and see what financial independence actually costs there — entirely in your
            browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <CityFireCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="fire-by-city" title="FIRE Number by City Calculator" />
      </section>

      {/* Explainer */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-6">How this calculator works</h2>
          <div className="prose prose-slate max-w-none text-slate-600 leading-relaxed space-y-4">
            <p>
              Unlike a single blanket FIRE number, the cost of living — and therefore how much you need to retire —
              varies enormously across India. This calculator starts from a cost-of-living estimate for the specific
              city or region you pick (editable, since it&apos;s an illustrative average, not a verified survey),
              then applies the classic 4%-rule-style formula: your FIRE number is your annual expenses divided by
              your chosen withdrawal rate, which works out to roughly 25 times your annual expenses at the default
              4% rate.
            </p>
            <p>
              From there, it inflates that number forward to your target retirement age using your expected
              inflation rate, and solves for the monthly SIP — compounding annually at your chosen asset
              allocation&apos;s blended return — that gets you there. Everything runs in your browser; nothing you
              enter is sent anywhere.
            </p>
          </div>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'How is the FIRE number calculated for a specific city?',
            answer:
              "It starts from an illustrative average monthly expense for the city or region you pick, which you can edit, multiplies it by 12 for an annual figure, then divides by your withdrawal rate — the standard way to convert an expense level into a target investment corpus.",
          },
          {
            question: 'What withdrawal rate should I use?',
            answer:
              '4% is the most common default, based on long-running research into how much a diversified portfolio can sustain in annual withdrawals without running out. Retiring earlier than a traditional retirement age means your money needs to last longer, so some people in the FIRE community use a more conservative 3-3.5% instead — you can set your own rate above.',
          },
          {
            question: 'Are the city cost-of-living figures accurate?',
            answer:
              "They're illustrative averages meant as a reasonable starting point, not a verified survey of actual spending in each city. Your own expenses will vary based on lifestyle, housing choices, and family size — always edit the monthly expense field to match your own numbers.",
          },
          {
            question: "Can I retire somewhere that isn't in the list?",
            answer:
              'Yes — pick "Rural / Village (Custom)" under the Region dropdown and enter your own estimated monthly expense directly.',
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
