import Link from 'next/link';
import { appRoutes } from '@/lib/config';

export default function Home() {
  return (
    <div className="bg-white">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-cyan-50 to-white overflow-hidden">
        <div className="absolute inset-0 bg-grid-slate-100 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))] bg-[size:20px_20px]"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32 lg:py-40">
          <div className="text-center max-w-5xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-100 text-cyan-700 rounded-full text-sm font-medium mb-8">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Join thousands pursuing financial independence
            </div>
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-slate-900 mb-6 leading-tight">
              Your Path to <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-cyan-700">Financial Independence</span>
            </h1>
            <p className="mt-6 text-xl sm:text-2xl text-slate-600 max-w-3xl mx-auto leading-relaxed">
              Track your net worth across currencies, connect with the FIRE community, and get guidance from financial professionals.
            </p>
            <div className="mt-12 flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href={appRoutes.register}
                className="group bg-cyan-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-cyan-700 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
              >
                Get Started
                <svg className="inline-block ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </a>
              <Link
                href="/about"
                className="border-2 border-slate-300 text-slate-700 px-8 py-4 rounded-lg text-lg font-semibold hover:border-cyan-600 hover:text-cyan-600 hover:bg-cyan-50 transition-all"
              >
                Learn About FIRE
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20">
            <span className="inline-block px-4 py-2 bg-cyan-100 text-cyan-700 rounded-full text-sm font-medium mb-4">
              Features
            </span>
            <h2 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-6">
              Everything for Your FIRE Journey
            </h2>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto">
              Track, plan, and achieve financial independence with the right tools
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="group bg-white p-8 rounded-2xl shadow-md hover:shadow-2xl transition-all duration-300 border border-slate-100 hover:border-cyan-200 hover:-translate-y-1">
              <div className="w-14 h-14 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Multi-Currency Tracking</h3>
              <p className="text-slate-600 leading-relaxed">
                Track your net worth across multiple currencies with real-time conversion. Perfect for global investors.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group bg-white p-8 rounded-2xl shadow-md hover:shadow-2xl transition-all duration-300 border border-slate-100 hover:border-cyan-200 hover:-translate-y-1">
              <div className="w-14 h-14 bg-gradient-to-br from-slate-600 to-slate-700 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Community Connection</h3>
              <p className="text-slate-600 leading-relaxed">
                Connect with fellow Fireons pursuing financial independence. Share insights and learn from others.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group bg-white p-8 rounded-2xl shadow-md hover:shadow-2xl transition-all duration-300 border border-slate-100 hover:border-cyan-200 hover:-translate-y-1">
              <div className="w-14 h-14 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Progress Visualization</h3>
              <p className="text-slate-600 leading-relaxed">
                Track your journey with clear charts and insights. Monitor your path to financial independence.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="group bg-white p-8 rounded-2xl shadow-md hover:shadow-2xl transition-all duration-300 border border-slate-100 hover:border-cyan-200 hover:-translate-y-1">
              <div className="w-14 h-14 bg-gradient-to-br from-slate-600 to-slate-700 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Financial Professionals</h3>
              <p className="text-slate-600 leading-relaxed">
                Connect with vetted advisors who understand FIRE principles and can guide your strategy.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="group bg-white p-8 rounded-2xl shadow-md hover:shadow-2xl transition-all duration-300 border border-slate-100 hover:border-cyan-200 hover:-translate-y-1">
              <div className="w-14 h-14 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Privacy-Focused</h3>
              <p className="text-slate-600 leading-relaxed">
                Your financial data stays private. Share what you want, when you want, with who you want.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-28 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20">
            <span className="inline-block px-4 py-2 bg-cyan-100 text-cyan-700 rounded-full text-sm font-medium mb-4">
              How It Works
            </span>
            <h2 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-6">
              Start Your FIRE Journey
            </h2>
            <p className="text-xl text-slate-600 max-w-2xl mx-auto">
              Three simple steps to financial independence
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
            <div className="relative">
              <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 h-full border border-slate-100">
                <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-cyan-600 text-white rounded-2xl flex items-center justify-center text-2xl font-bold mb-6 shadow-lg">
                  1
                </div>
                <h3 className="text-2xl font-bold text-slate-900 mb-4">Join Anonymously</h3>
                <p className="text-slate-600 leading-relaxed">
                  Sign up and create your anonymous profile. Your identity stays private while you track your progress.
                </p>
              </div>
              <div className="hidden md:block absolute top-1/2 -right-6 w-12 h-0.5 bg-gradient-to-r from-cyan-200 to-transparent"></div>
            </div>

            <div className="relative">
              <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 h-full border border-slate-100">
                <div className="w-16 h-16 bg-gradient-to-br from-slate-600 to-slate-700 text-white rounded-2xl flex items-center justify-center text-2xl font-bold mb-6 shadow-lg">
                  2
                </div>
                <h3 className="text-2xl font-bold text-slate-900 mb-4">Track & Share</h3>
                <p className="text-slate-600 leading-relaxed">
                  Monitor your net worth across currencies and share your journey with the community for feedback.
                </p>
              </div>
              <div className="hidden md:block absolute top-1/2 -right-6 w-12 h-0.5 bg-gradient-to-r from-cyan-200 to-transparent"></div>
            </div>

            <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 h-full border border-slate-100">
              <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-cyan-600 text-white rounded-2xl flex items-center justify-center text-2xl font-bold mb-6 shadow-lg">
                3
              </div>
              <h3 className="text-2xl font-bold text-slate-900 mb-4">Connect & Grow</h3>
              <p className="text-slate-600 leading-relaxed">
                Get advice from professionals, learn from others, and achieve financial independence together.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* For Professionals CTA */}
      <section className="relative py-28 bg-gradient-to-br from-cyan-600 to-cyan-700 overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMzLjMxNCAwIDYgMi42ODYgNiA2cy0yLjY4NiA2LTYgNi02LTIuNjg2LTYtNiAyLjY4Ni02IDYtNnoiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLW9wYWNpdHk9Ii4xIi8+PC9nPjwvc3ZnPg==')] opacity-20"></div>
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl sm:text-5xl font-bold mb-6 text-white">
            Are You a Financial Professional?
          </h2>
          <p className="text-xl text-cyan-50 mb-10 max-w-2xl mx-auto">
            Connect with motivated clients who are serious about achieving financial independence
          </p>
          <Link
            href="/for-professionals"
            className="inline-flex items-center gap-2 bg-white text-cyan-700 px-8 py-4 rounded-xl text-lg font-semibold hover:bg-cyan-50 transition-all shadow-2xl hover:shadow-xl hover:-translate-y-0.5"
          >
            Learn More
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-28 bg-slate-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-3xl shadow-2xl p-12 md:p-16 text-center border border-slate-100">
            <h2 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-6">
              Ready to Start Your FIRE Journey?
            </h2>
            <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto">
              Join thousands of Fireons working towards financial independence
            </p>
            <a
              href={appRoutes.register}
              className="inline-flex items-center gap-2 bg-cyan-600 text-white px-10 py-5 rounded-xl text-lg font-semibold hover:bg-cyan-700 transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
            >
              Get Started for Free
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
