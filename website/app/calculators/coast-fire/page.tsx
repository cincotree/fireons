import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import CoastFireCalculator from '@/components/CoastFireCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'Coast FIRE Calculator - Fireons',
  description: 'Find out if you already have enough saved to coast to retirement, with no further contributions.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'Coast FIRE Calculator - Fireons',
    description: 'Find out if you already have enough saved to coast to retirement, with no further contributions.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Coast FIRE Calculator - Fireons',
    description: 'Find out if you already have enough saved to coast to retirement, with no further contributions.',
  },
};

export default function CoastFireCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">Coast FIRE Calculator</h1>
          <p className="text-xl text-blue-100">
            Find out if you already have enough saved to stop investing and still retire comfortably — entirely in
            your browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <CoastFireCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="coast-fire" title="Coast FIRE Calculator" />
      </section>

      {/* Explainer */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-4">How this calculator works</h2>
          <p className="text-slate-600 leading-relaxed">
            Coast FIRE is the point where you&apos;ve already saved enough that, left untouched, compound growth
            alone will carry you to a full retirement corpus by your target retirement age — without investing
            another rupee. This calculator works backward from your retirement age, expenses, and life expectancy to
            find that &ldquo;coast number,&rdquo; then compares it to what you&apos;ve actually saved to tell you
            whether you&apos;ve reached it, or how much more you need.
          </p>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'What is Coast FIRE?',
            answer:
              "It's the savings threshold at which you no longer need to add new investments — your existing portfolio, given enough time and compound growth, will reach your full retirement number on its own by the time you retire.",
          },
          {
            question: 'How is my Coast FIRE number different from my regular FIRE number?',
            answer:
              'Your FIRE number is the corpus you need at retirement. Your Coast FIRE number is smaller — it\'s how much you\'d need today, with no further contributions, so that growth alone gets you to that same FIRE number by your retirement age.',
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
