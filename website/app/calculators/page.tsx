import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';

export const metadata: Metadata = {
  title: 'Free FIRE Calculators - Fireons',
  description: 'Free, interactive calculators for your FIRE journey — entirely in your browser, nothing is sent anywhere.',
};

export default function Calculators() {
  return (
    <div className="bg-white">
      {/* Header */}
      <section className="py-12 text-center">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-3">Free FIRE Calculators</h1>
          <p className="text-lg text-slate-600">
            See your numbers in under a minute — entirely in your browser, nothing is sent anywhere.
          </p>
        </div>
      </section>

      {/* Not sure where to start? */}
      <section className="pb-8">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link
            href={appRoutes.getStarted}
            className="group flex items-center justify-between gap-4 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-2xl px-6 py-5 transition-colors"
          >
            <span className="font-semibold text-amber-900">
              Not sure where to start? Answer a few quick questions and we&apos;ll point you to the right calculator.
            </span>
            <span className="text-amber-700 font-semibold whitespace-nowrap group-hover:underline">Get started →</span>
          </Link>
        </div>
      </section>

      {/* Calculator grid */}
      <section className="pb-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Link
              href={appRoutes.retirementCalculator}
              className="group bg-cyan-50/60 hover:bg-cyan-50 p-8 rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 border border-cyan-100 hover:-translate-y-1"
            >
              <div className="w-14 h-14 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <span className="text-2xl font-bold text-white">₹</span>
              </div>
              <p className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-2">Retirement Calculator</p>
              <h3 className="text-xl font-bold text-slate-900 mb-3">What&apos;s my FIRE number?</h3>
              <p className="text-slate-600 leading-relaxed mb-4">
                See how much to invest monthly to retire on your own terms.
              </p>
              <span className="text-cyan-700 font-semibold group-hover:underline">Try it now →</span>
            </Link>

            <Link
              href={appRoutes.coastFireCalculator}
              className="group bg-emerald-50/60 hover:bg-emerald-50 p-8 rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 border border-emerald-100 hover:-translate-y-1"
            >
              <div className="w-14 h-14 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3v18h2v-7h13l-3-4 3-4H5V3H3z" />
                </svg>
              </div>
              <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-2">Coast FIRE Calculator</p>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Can I stop investing today?</h3>
              <p className="text-slate-600 leading-relaxed mb-4">
                Find out if you&apos;ve already saved enough to coast to retirement.
              </p>
              <span className="text-emerald-700 font-semibold group-hover:underline">Try it now →</span>
            </Link>

            <Link
              href={appRoutes.savingsRateCalculator}
              className="group bg-indigo-50/60 hover:bg-indigo-50 p-8 rounded-2xl shadow-sm hover:shadow-xl transition-all duration-300 border border-indigo-100 hover:-translate-y-1"
            >
              <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-2">Savings Rate Calculator</p>
              <h3 className="text-xl font-bold text-slate-900 mb-3">How many years to freedom?</h3>
              <p className="text-slate-600 leading-relaxed mb-4">
                See how fast your savings rate gets you to financial independence.
              </p>
              <span className="text-indigo-700 font-semibold group-hover:underline">Try it now →</span>
            </Link>
          </div>

          <p className="text-center text-slate-500 mt-12">More tools on the way.</p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Want to track your actual progress?</h2>
          <p className="text-xl text-gray-600 mb-8">
            Join Fireons to track your real net worth, not just a one-time estimate
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
