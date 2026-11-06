import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import ReturnToIndiaCalculator from '@/components/ReturnToIndiaCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'Return to India (NRI FIRE) Calculator - Fireons',
  description: 'For NRIs planning to move back to India: see your FIRE number in rupees and how much to invest in dollars to get there — entirely in your browser, nothing is sent anywhere.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Return to India (NRI FIRE) Calculator - Fireons',
    description: 'For NRIs planning to move back to India: see your FIRE number in rupees and how much to invest in dollars to get there — entirely in your browser, nothing is sent anywhere.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Return to India (NRI FIRE) Calculator - Fireons',
    description: 'For NRIs planning to move back to India: see your FIRE number in rupees and how much to invest in dollars to get there — entirely in your browser, nothing is sent anywhere.',
  },
};

export default function ReturnToIndiaCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">Return to India Calculator</h1>
          <p className="text-xl text-blue-100">
            Earning and saving in dollars, planning to retire in India? See your FIRE number in rupees and how much
            to invest in dollars each month to get there, accounting for the exchange rate — entirely in your
            browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <ReturnToIndiaCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="return-to-india" title="Return to India (NRI FIRE) Calculator" />
      </section>

      {/* Explainer */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-6">How this calculator works</h2>
          <div className="prose prose-slate max-w-none text-slate-600 leading-relaxed space-y-4">
            <p>
              If you&apos;re earning and saving in US dollars but plan to retire in India, your FIRE number
              isn&apos;t a single-currency problem — it&apos;s two. This calculator first works out your FIRE number
              in rupees, the same way the FIRE by City calculator does: your chosen city&apos;s cost of living,
              divided by your withdrawal rate, inflated forward to the age you plan to return. It then converts that
              rupee target into dollars using a projected future exchange rate, which accounts for the fact that the
              rupee has historically lost value against the dollar over time — a dynamic separate from
              India&apos;s domestic inflation.
            </p>
            <p>
              From there, it solves for the monthly dollar SIP — invested in US-market assets at your expected
              return — that gets your dollar savings to that converted target by your return age. The current
              exchange rate field auto-fills with today&apos;s actual rate and stays live on every visit, unless
              you&apos;ve edited it yourself.
            </p>
          </div>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'How does this calculator handle currency conversion?',
            answer:
              "It keeps two separate compounding effects distinct: India's domestic inflation, which grows your rupee expense target over time, and rupee depreciation against the dollar, which separately grows the exchange rate itself over time. Your rupee FIRE number is inflated using India inflation, then converted to dollars using the projected future exchange rate.",
          },
          {
            question: 'Where does the live exchange rate come from?',
            answer:
              "It's fetched from a free, public exchange rate API when you load the page, and shown with the date it's as of. If you've typed in your own rate, your value is kept — it won't be silently overwritten on your next visit.",
          },
          {
            question: 'What is rupee depreciation, and why does it matter separately from inflation?',
            answer:
              "The rupee has historically lost value against the dollar by roughly 2-4% a year, largely because India's inflation runs higher than the US's. For an NRI holding dollar savings, this means a given dollar amount buys more rupees over time — a real tailwind for your plan on top of your investment returns, separate from inflation eating into your rupee expenses.",
          },
          {
            question: 'Why are the return assumptions different here than other calculators?',
            answer:
              'This calculator assumes your savings are invested in US-market assets (US equity and US debt), which have different long-run return characteristics than Indian equity and debt, so the default return fields are set accordingly — though you can adjust them.',
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
