import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import SavingsRateCalculator from '@/components/SavingsRateCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'Savings Rate Calculator - Fireons',
  description: 'Find out how many years until you reach financial independence, based on your savings rate.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Savings Rate Calculator - Fireons',
    description: 'Find out how many years until you reach financial independence, based on your savings rate.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Savings Rate Calculator - Fireons',
    description: 'Find out how many years until you reach financial independence, based on your savings rate.',
  },
};

export default function SavingsRateCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">Savings Rate Calculator</h1>
          <p className="text-xl text-blue-100">
            See how many years until you&apos;re financially independent, based on your savings rate — entirely in your
            browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <SavingsRateCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="savings-rate" title="Savings Rate Calculator" />
      </section>

      {/* Explainer */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-4">How this calculator works</h2>
          <p className="text-slate-600 leading-relaxed">
            Your savings rate — the share of your income you invest rather than spend — is one of the biggest levers
            in how fast you reach financial independence. This calculator uses the classic 25× annual expenses rule
            (a 4% withdrawal rate) as your FI number, then projects how many years it takes your current savings
            rate, compounding at your expected real return (return minus inflation), to get there.
          </p>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'How does my savings rate affect how fast I reach FI?',
            answer:
              'A higher savings rate does double duty: you accumulate investments faster, and you need a smaller total corpus since your expenses, and therefore your FI number, are lower. Small increases in savings rate can meaningfully shorten your timeline, especially at higher percentages.',
          },
          {
            question: 'What return rate should I use?',
            answer:
              "The calculator uses your expected return and inflation together to compute a \"real\" (inflation-adjusted) growth rate, which is what actually determines how fast your purchasing power grows. Use your realistic long-run expected return, not an optimistic best-case number.",
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
