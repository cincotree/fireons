import Link from 'next/link';
import { Metadata } from 'next';
import { appRoutes } from '@/lib/config';

export const metadata: Metadata = {
  title: 'Privacy & Security - Fireones',
  description: 'Learn how Fireones protects your privacy and keeps your financial data secure with anonymity-first design.',
};

export default function Privacy() {
  return (
    <div className="bg-white">
      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-900 to-teal-700 text-white py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold mb-6">
            Your Privacy is Our Priority
          </h1>
          <p className="text-xl text-blue-100">
            We're committed to protecting your financial data and maintaining your complete anonymity
          </p>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-16 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="prose prose-lg max-w-none">

          <h2 className="text-3xl font-bold text-gray-900 mb-6">Anonymity by Design</h2>
          <p className="text-gray-700 mb-6">
            At Fireones, we believe your financial journey is personal. That's why we've built our platform
            from the ground up with anonymity as a core principle, not an afterthought.
          </p>

          <div className="bg-gradient-to-r from-blue-50 to-teal-50 p-8 rounded-xl mb-12">
            <h3 className="text-2xl font-bold text-gray-900 mb-4">What We Mean by Anonymous</h3>
            <ul className="space-y-3 text-gray-700">
              <li className="flex items-start">
                <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>No real names required — use any username you choose</span>
              </li>
              <li className="flex items-start">
                <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Optional profile information — share only what you're comfortable with</span>
              </li>
              <li className="flex items-start">
                <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Community interactions remain anonymous unless you choose otherwise</span>
              </li>
              <li className="flex items-start">
                <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Your financial data is never shared with third parties</span>
              </li>
            </ul>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-6 mt-12">Data Security</h2>
          <p className="text-gray-700 mb-6">
            We employ industry-standard security measures to protect your information:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
            <div className="bg-blue-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-blue-900 mb-2">Encryption</h3>
              <p className="text-gray-700">
                All data is encrypted in transit (TLS) and at rest using industry-standard encryption protocols.
              </p>
            </div>

            <div className="bg-teal-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-teal-900 mb-2">Secure Authentication</h3>
              <p className="text-gray-700">
                Password hashing with bcrypt and JWT-based authentication with short token expiration.
              </p>
            </div>

            <div className="bg-amber-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-amber-900 mb-2">Data Isolation</h3>
              <p className="text-gray-700">
                Your financial data is isolated and accessible only to you and professionals you choose to consult.
              </p>
            </div>

            <div className="bg-emerald-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold text-emerald-900 mb-2">Regular Audits</h3>
              <p className="text-gray-700">
                We conduct regular security audits and updates to protect against emerging threats.
              </p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-6 mt-12">What We Collect</h2>
          <p className="text-gray-700 mb-6">
            We collect only the minimum information necessary to provide our services:
          </p>

          <div className="space-y-4 mb-8">
            <div className="border-l-4 border-blue-800 pl-4">
              <h3 className="font-semibold text-gray-900 mb-1">Account Information</h3>
              <p className="text-gray-600">Email address (for account recovery and important updates), username, and encrypted password.</p>
            </div>

            <div className="border-l-4 border-teal-600 pl-4">
              <h3 className="font-semibold text-gray-900 mb-1">Financial Data</h3>
              <p className="text-gray-600">Net worth information and currency preferences that you choose to track. This data is private to you.</p>
            </div>

            <div className="border-l-4 border-amber-500 pl-4">
              <h3 className="font-semibold text-gray-900 mb-1">Usage Information</h3>
              <p className="text-gray-600">Basic analytics to improve our service (anonymized and aggregated).</p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-6 mt-12">What We Don't Do</h2>
          <div className="bg-red-50 border border-red-200 p-8 rounded-xl mb-12">
            <ul className="space-y-3 text-gray-700">
              <li className="flex items-start">
                <svg className="w-6 h-6 text-red-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span><strong>We never sell your data</strong> to advertisers or third parties</span>
              </li>
              <li className="flex items-start">
                <svg className="w-6 h-6 text-red-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span><strong>We don't share your financial details</strong> with anyone without your explicit consent</span>
              </li>
              <li className="flex items-start">
                <svg className="w-6 h-6 text-red-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span><strong>We don't require real names</strong> or identifying information to use our platform</span>
              </li>
              <li className="flex items-start">
                <svg className="w-6 h-6 text-red-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span><strong>We don't use tracking cookies</strong> for advertising purposes</span>
              </li>
            </ul>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-6 mt-12">Working with Financial Professionals</h2>
          <p className="text-gray-700 mb-6">
            When you choose to consult with a financial professional through Fireones:
          </p>

          <ul className="space-y-3 mb-8 text-gray-700">
            <li className="flex items-start">
              <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>You control what financial information you share with them</span>
            </li>
            <li className="flex items-start">
              <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>You can remain anonymous throughout the consultation process</span>
            </li>
            <li className="flex items-start">
              <svg className="w-6 h-6 text-teal-600 mr-2 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Professionals are bound by our privacy policies and their own professional ethics</span>
            </li>
          </ul>

          <h2 className="text-3xl font-bold text-gray-900 mb-6 mt-12">Your Rights</h2>
          <p className="text-gray-700 mb-6">
            You have complete control over your data:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-800 mr-2 mt-1 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-gray-700">Access your data at any time</span>
            </div>
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-800 mr-2 mt-1 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-gray-700">Export your financial data</span>
            </div>
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-800 mr-2 mt-1 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-gray-700">Delete your account and data</span>
            </div>
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-800 mr-2 mt-1 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-gray-700">Control sharing preferences</span>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg mb-8">
            <h3 className="text-lg font-semibold text-blue-900 mb-2">Questions About Privacy?</h3>
            <p className="text-gray-700">
              If you have any questions about how we protect your privacy, please contact our support team.
              We're committed to transparency and will gladly answer any concerns.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Trust Built on Transparency
          </h2>
          <p className="text-xl text-gray-600 mb-8">
            Join Fireones and take control of your financial future with complete peace of mind
          </p>
          <a
            href={appRoutes.register}
            className="inline-block bg-blue-800 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-900 transition-colors shadow-lg"
          >
            Get Started Anonymously
          </a>
        </div>
      </section>
    </div>
  );
}
