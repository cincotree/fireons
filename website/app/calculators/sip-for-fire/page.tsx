import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';
import SipFireCalculator from '@/components/SipFireCalculator';
import EmbedCodeSnippet from '@/components/EmbedCodeSnippet';
import FaqSection from '@/components/FaqSection';

export const metadata: Metadata = {
  title: 'SIP Calculator for FIRE - Fireons',
  description: 'See whether your current SIP will actually get you to your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.',
  openGraph: {
    images: ['/opengraph-image'],
    title: 'SIP Calculator for FIRE - Fireons',
    description: 'See whether your current SIP will actually get you to your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'SIP Calculator for FIRE - Fireons',
    description: 'See whether your current SIP will actually get you to your FIRE number, and by what age — entirely in your browser, nothing is sent anywhere.',
  },
};

export default function SipFireCalculatorPage() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">SIP Calculator for FIRE</h1>
          <p className="text-xl text-blue-100">
            You know your SIP amount — see if it&apos;s actually enough to hit your FIRE number, and by what age —
            entirely in your browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Calculator */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <SipFireCalculator />
      </section>

      {/* Embed */}
      <section className="pb-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <EmbedCodeSnippet slug="sip-for-fire" title="SIP Calculator for FIRE" />
      </section>

      {/* Explainer */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mb-4">How this calculator works</h2>
          <p className="text-slate-600 leading-relaxed">
            Most SIP calculators just show you a future value — but the real question is usually whether that amount
            is actually enough. This calculator takes the SIP you&apos;re already investing, or considering, and
            checks it against your FIRE number, telling you the age you&apos;d actually reach financial independence
            at that rate, or how much to increase your SIP by to hit your target age instead.
          </p>
        </div>
      </section>

      <FaqSection
        items={[
          {
            question: 'How is this different from the Retirement Calculator?',
            answer:
              'The Retirement Calculator solves for the SIP you need. This one starts from a SIP you already have in mind and checks whether it\'s enough — a more direct way to answer "will what I\'m already doing actually work?"',
          },
          {
            question: "What if I don't know my FIRE number yet?",
            answer:
              'Work it out first using the Retirement Calculator or the FIRE Number by City calculator, then come back here with that number to check your SIP against it.',
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
