import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import LumpsumFireCalculator from '@/components/LumpsumFireCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';

export const metadata: Metadata = {
  title: 'Lumpsum Calculator for FIRE - Fireons',
  description: 'See whether a one-time lumpsum investment will actually get you to your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.',
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
