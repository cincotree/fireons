import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import NpsCalculator from '@/components/NpsCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'NPS Calculator for FIRE - Fireons',
  description: 'See your NPS corpus, tax-free lump sum, and monthly pension at retirement, and how much of your FIRE number it covers — entirely in your browser, nothing is sent anywhere.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'NPS Calculator for FIRE - Fireons',
    description: 'See your NPS corpus, tax-free lump sum, and monthly pension at retirement, and how much of your FIRE number it covers — entirely in your browser, nothing is sent anywhere.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NPS Calculator for FIRE - Fireons',
    description: 'See your NPS corpus, tax-free lump sum, and monthly pension at retirement, and how much of your FIRE number it covers — entirely in your browser, nothing is sent anywhere.',
  },
};

export default function NpsCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">NPS Calculator</h1>
          <p className="text-xl text-blue-100">
            See your NPS corpus, tax-free lump sum, and monthly pension at retirement, and how much of your FIRE
            number it covers — entirely in your browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <NpsCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="nps" title="NPS Calculator for FIRE" />
      </section>

      {/* Explainer */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-4">How this calculator works</h2>
          <p className="text-slate-600 leading-relaxed">
            The National Pension System (NPS) is a market-linked retirement account: your contributions grow at a
            return you choose, but at retirement a minimum 40% of the corpus must be used to buy an annuity (a fixed
            monthly pension), with the rest available as a lump sum. This calculator projects your corpus, then
            splits it into that mandatory annuity portion and your tax-free lump sum.
          </p>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'Why do I have to buy an annuity with part of my NPS corpus?',
            answer:
              "It's a regulatory requirement — NPS is designed to guarantee a baseline retirement income, not just a lump sum. At least 40% of your corpus must go toward purchasing an annuity at retirement; the rest can be withdrawn directly.",
          },
          {
            question: 'What annuity payout rate should I expect?',
            answer:
              "Annuity rates from insurers in India have typically ranged around 5-7% annually, though they vary by provider and plan type. The calculator lets you set your own assumption — check current rates from NPS-empanelled annuity providers for a more precise estimate.",
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
