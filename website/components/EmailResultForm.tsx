'use client';

import { useState } from 'react';
import { config } from '@/lib/config';

const WEB3FORMS_ENDPOINT = 'https://api.web3forms.com/submit';

interface Props {
  calculatorTitle: string;
  resultSummary: string;
}

export default function EmailResultForm({ calculatorTitle, resultSummary }: Props) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!config.web3formsAccessKey) {
      setStatus('error');
      setErrorMessage('Email delivery is not available right now. Please try again later.');
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
          email,
          subject: `Your ${calculatorTitle} result`,
          from_name: 'Fireons Calculators',
          message: resultSummary,
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
      <p role="status" className="text-sm text-emerald-700 text-center">
        Sent! Check your inbox for your {calculatorTitle} result.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 justify-center items-center">
      <input
        type="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        placeholder="you@example.com"
        aria-label="Email address"
        className="px-4 py-2 rounded-lg border-2 border-slate-300 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100 transition-all sm:w-64"
      />
      <button
        type="submit"
        disabled={status === 'submitting'}
        className="inline-flex items-center justify-center gap-2 bg-cyan-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-cyan-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed whitespace-nowrap"
      >
        {status === 'submitting' ? 'Sending...' : 'Email me this result'}
      </button>
      {status === 'error' && (
        <p role="alert" className="text-xs text-red-600 text-center basis-full">
          {errorMessage}
        </p>
      )}
    </form>
  );
}
