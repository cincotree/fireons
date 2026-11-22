'use client';

import { useState } from 'react';
import { shareOrCopy } from '@/lib/share';

interface ShareButtonProps {
  text: string;
  buildUrl: () => string;
}

export default function ShareButton({ text, buildUrl }: ShareButtonProps) {
  const [justCopied, setJustCopied] = useState(false);

  const handleClick = async () => {
    const outcome = await shareOrCopy({ title: 'Fireons Calculator', text, url: buildUrl() });
    if (outcome === 'copied') {
      setJustCopied(true);
      setTimeout(() => setJustCopied(false), 2000);
    }
  };

  return (
    <div className="flex justify-center">
      <button
        type="button"
        onClick={handleClick}
        className="inline-flex items-center gap-2 border border-cyan-600 text-cyan-700 px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-cyan-100 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342a3 3 0 100-2.684M8.684 13.342l6.632 3.316M8.684 10.658l6.632-3.316M15.316 7.342a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684zm0 9.316a3 3 0 105.368-2.684 3 3 0 00-5.368 2.684z" />
        </svg>
        {justCopied ? 'Link copied!' : 'Share this result'}
      </button>
    </div>
  );
}
