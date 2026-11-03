import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import RetirementCalculator from '@/components/RetirementCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'Retirement Calculator - Fireons',
  description: 'Find out how much you need to invest every month to retire comfortably, based on your own numbers.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Retirement Calculator - Fireons',
    description: 'Find out how much you need to invest every month to retire comfortably, based on your own numbers.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Retirement Calculator - Fireons',
    description: 'Find out how much you need to invest every month to retire comfortably, based on your own numbers.',
  },
};

export default function RetirementCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">Retirement Calculator</h1>
          <p className="text-xl text-blue-100">
            See how much you need to invest every month to retire on your own terms — entirely in your browser,
            nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <RetirementCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="retirement" title="Retirement Calculator" />
      </section>

      {/* Explainer */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-6">How this calculator works</h2>
          <div className="prose prose-slate max-w-none text-slate-600 leading-relaxed space-y-4">
            <p>
              This calculator figures out the exact monthly investment (SIP) you need to retire comfortably on your
              own terms. Rather than relying on the rough &ldquo;25 times annual expenses&rdquo; rule of thumb that
              most FIRE calculators use, it runs a full year-by-year simulation: your monthly investments compound
              annually at a blended equity/debt return based on the asset allocation you choose, until your
              retirement age. From there, it switches to your chosen post-retirement allocation and simulates your
              annual withdrawals — inflating your desired monthly spend every year — all the way out to the age you
              expect your money to need to last.
            </p>
            <p>
              It then searches for the smallest monthly SIP that makes your corpus last exactly that long, instead
              of stopping short or leaving money unnecessarily unspent. All of this runs entirely in your browser —
              none of the numbers you enter are ever sent anywhere.
            </p>
          </div>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'What is a FIRE number?',
            answer:
              "Your FIRE number is the total investment corpus you need at retirement so it can fund your living expenses for the rest of your life, accounting for inflation and investment returns. This calculator computes it for you as \"Corpus needed at retirement,\" based on your expected monthly spend, how long your money needs to last, and your return assumptions.",
          },
          {
            question: 'How is the required monthly SIP calculated?',
            answer:
              'The calculator simulates your investments compounding annually until your retirement age using your chosen asset allocation\'s blended return, then simulates withdrawals (inflation-adjusted each year) from retirement until your life expectancy using your post-retirement allocation. It searches for the lowest monthly SIP that makes your corpus last exactly as long as you need it to, without running out early.',
          },
          {
            question: 'Why does the required SIP change when I change my asset allocation?',
            answer:
              "A more aggressive allocation (higher equity weighting) assumes a higher average return, so it typically needs a smaller monthly investment to reach the same end corpus — but it swings more year to year. A conservative allocation needs a larger monthly investment to compensate for lower expected growth. There's no universally right choice — it depends on your own risk tolerance.",
          },
          {
            question: 'What if I want to stop investing before I retire?',
            answer:
              'Use the "I will invest until age" field to set an earlier age than your retirement age. The calculator will stop your SIP at that age and let the accumulated corpus keep growing untouched, at your pre-retirement return, until you actually retire.',
          },
          {
            question: 'Does this calculator account for inflation?',
            answer:
              "Yes. Your desired monthly spend, entered in today's rupees, is inflated forward to your retirement age, then increased further each year during retirement at your expected inflation rate — so your purchasing power stays roughly constant throughout retirement.",
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
