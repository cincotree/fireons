'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { config, professionalParam } from '@/lib/config';

const WEB3FORMS_ENDPOINT = 'https://api.web3forms.com/submit';

export default function WaitlistForm() {
  const searchParams = useSearchParams();
  const [isProfessional, setIsProfessional] = useState(
    searchParams.get(professionalParam.name) === professionalParam.value
  );
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    if (formData.get('botcheck')) {
      return;
    }
    if (!config.web3formsAccessKey) {
      setStatus('error');
      setErrorMessage('The waitlist is not available right now. Please try again later.');
      return;
    }
    setStatus('submitting');
    try {
      const response = await fetch(WEB3FORMS_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          access_key: config.web3formsAccessKey,
          email: formData.get('email'),
          user_type: isProfessional ? 'Financial Professional' : 'Individual',
          subject: 'New Fireons waitlist signup',
          from_name: 'Fireons Website',
        }),
      });
      const result = await response.json();
      if (result.success) {
        setStatus('success');
      } else {
        setStatus('error');
        setErrorMessage(result.message || 'Something went wrong. Please try again.');
      }
    } catch {
      setStatus('error');
      setErrorMessage('Something went wrong. Please try again.');
    }
  };

  if (status === 'success') {
    return (
      <div
        role="status"
        className="max-w-xl mx-auto bg-cyan-50 border border-cyan-200 text-cyan-800 rounded-xl px-6 py-5 text-lg font-medium"
      >
        You&apos;re on the waitlist! We&apos;ll email you as soon as Fireons is ready.
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-xl mx-auto">
      <input
        type="checkbox"
        name="botcheck"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        className="hidden"
      />
      <div className="flex flex-col gap-4">
        <input
          type="email"
          name="email"
          required
          placeholder="Enter your email"
          aria-label="Email address"
          className="w-full px-5 py-4 rounded-lg border-2 border-slate-300 text-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 transition-all"
        />
        <label className="flex items-center justify-center gap-2 text-slate-600 cursor-pointer">
          <input
            type="checkbox"
            name="professional"
            checked={isProfessional}
            onChange={(event) => setIsProfessional(event.target.checked)}
            className="w-4 h-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500 accent-cyan-600"
          />
          I&apos;m a financial professional
        </label>
        <button
          type="submit"
          disabled={status === 'submitting'}
          className="w-full bg-cyan-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-cyan-700 transition-all shadow-lg hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {status === 'submitting' ? 'Joining...' : 'Join the Waitlist'}
        </button>
      </div>
      {status === 'error' && (
        <p role="alert" className="mt-3 text-red-600 font-medium">
          {errorMessage}
        </p>
      )}
      <p className="mt-3 text-sm text-slate-500">
        Be the first to know when Fireons launches. No spam, ever.
      </p>
    </form>
  );
}
