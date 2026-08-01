import { Metadata } from 'next';
import { Suspense } from 'react';
import WaitlistForm from '@/components/WaitlistForm';

export const metadata: Metadata = {
  title: 'Join the Waitlist - Fireons',
  description: 'Get early access to Fireons. Join the waitlist and be the first to know when we launch.',
};

export default function Waitlist() {
  return (
    <div className="bg-gradient-to-b from-cyan-50 to-white min-h-[70vh]">
      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-100 text-cyan-700 rounded-full text-sm font-medium mb-8">
          Launching soon (invite-only)
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-slate-900 mb-6">
          Be First in Line
        </h1>
        <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto leading-relaxed">
          We&apos;re building the home for your financial journey: multi-currency net-worth tracking,
          financial tools and access to largest directory of vetted financial professionals. Join
          the waitlist and get early access when we launch.
        </p>
        <Suspense>
          <WaitlistForm />
        </Suspense>
      </section>
    </div>
  );
}
