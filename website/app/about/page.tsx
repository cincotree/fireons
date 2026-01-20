import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';

export const metadata: Metadata = {
  title: 'About FIRE - Fireones',
  description: 'Learn about the FIRE (Financial Independence, Retire Early) movement and how Fireones can help you achieve your financial goals.',
};

export default function About() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-cyan-600 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">
            What is FIRE?
          </h1>
          <p className="text-xl text-blue-100">
            Financial Independence, Retire Early — A movement transforming how people think about money and life
          </p>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="prose prose-lg max-w-none">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">The FIRE Movement</h2>
          <p className="text-gray-700 mb-6">
            FIRE stands for <strong>Financial Independence, Retire Early</strong>. It's a lifestyle movement focused on
            extreme savings and investment that allows people to retire far earlier than traditional budgets and
            retirement plans would permit.
          </p>

          <p className="text-gray-700 mb-8">
            The core principle is simple: by saving and investing 50-70% of your income, you can accumulate enough
            wealth to live off the returns, freeing you from traditional employment and giving you the freedom to
            pursue what truly matters to you.
          </p>

          <h2 className="text-3xl font-bold text-gray-900 mb-6 mt-12">Types of FIRE</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
            <div className="bg-blue-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-blue-900 mb-2">Lean FIRE</h3>
              <p className="text-gray-700">
                Living frugally and retiring with a minimal budget. Typically requires $500K-$1M in savings.
              </p>
            </div>

            <div className="bg-teal-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-teal-900 mb-2">Fat FIRE</h3>
              <p className="text-gray-700">
                Maintaining a comfortable lifestyle in retirement. Usually requires $2.5M-$5M+ in savings.
              </p>
            </div>

            <div className="bg-amber-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-amber-900 mb-2">Barista FIRE</h3>
              <p className="text-gray-700">
                Semi-retirement with part-time work to cover expenses while investments grow.
              </p>
            </div>

            <div className="bg-emerald-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-emerald-900 mb-2">Coast FIRE</h3>
              <p className="text-gray-700">
                Having enough invested that you can stop contributions and let it grow to retirement age.
              </p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-4 mt-12">The 4% Rule</h2>
          <p className="text-gray-700 mb-6">
            A cornerstone of FIRE planning is the <strong>4% rule</strong>: if you withdraw 4% of your portfolio
            annually (adjusted for inflation), your money should last 30+ years. This means you need roughly 25
            times your annual expenses saved to achieve financial independence.
          </p>

          <div className="bg-cyan-50 p-8 rounded-xl mb-12">
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Example Calculation</h3>
            <div className="space-y-2 text-gray-700">
              <p>Annual expenses: $40,000</p>
              <p>Multiply by 25: $40,000 × 25 = <strong className="text-blue-800">$1,000,000</strong></p>
              <p className="mt-4 text-sm">
                With $1M invested, you can withdraw $40,000 annually (4%) to cover your living expenses.
              </p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-4 mt-12">Why Join Fireones?</h2>
          <p className="text-gray-700 mb-6">
            Achieving FIRE is challenging, and having a supportive community makes all the difference. Fireones
            provides:
          </p>

          <ul className="space-y-3 mb-8 text-gray-700">
            <li className="flex items-start">
              <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span><strong>Anonymous tracking</strong> — Share your progress without revealing your identity</span>
            </li>
            <li className="flex items-start">
              <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span><strong>Multi-currency support</strong> — Perfect for international investors and digital nomads</span>
            </li>
            <li className="flex items-start">
              <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span><strong>Community feedback</strong> — Get advice and encouragement from fellow Fireones</span>
            </li>
            <li className="flex items-start">
              <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span><strong>Professional advisors</strong> — Connect with vetted financial professionals who understand FIRE</span>
            </li>
          </ul>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Ready to Start Your FIRE Journey?
          </h2>
          <p className="text-xl text-gray-600 mb-8">
            Join the Fireones community and take control of your financial future
          </p>
          <a
            href={appRoutes.register}
            className="inline-block bg-blue-800 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-900 transition-colors shadow-lg"
          >
            Get Started for Free
          </a>
        </div>
      </section>
    </div>
  );
}
