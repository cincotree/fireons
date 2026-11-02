import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import ReturnToIndiaCalculator from '@/components/ReturnToIndiaCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';

export const metadata: Metadata = {
  title: 'Return to India (NRI FIRE) Calculator - Fireons',
  description: 'For NRIs planning to move back to India: see your FIRE number in rupees and how much to invest in dollars to get there — entirely in your browser, nothing is sent anywhere.',
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
