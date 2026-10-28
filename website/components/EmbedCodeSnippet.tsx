'use client';

import { useEffect, useState } from 'react';

interface Props {
  slug: string;
  title: string;
}

export default function EmbedCodeSnippet({ slug, title }: Props) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [origin, setOrigin] = useState('');

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOrigin(window.location.origin);
  }, []);

  const embedUrl = `${origin}/embed/${slug}`;
  const code = `<iframe src="${embedUrl}" width="100%" height="900" style="border:none;max-width:640px;" title="${title}"></iframe>`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard permission errors
    }
  };

  return (
    <div className="border border-slate-200 rounded-xl bg-slate-50 p-6">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex items-center justify-between w-full text-left font-semibold text-slate-900"
      >
        Embed this calculator on your blog
        <span className="text-slate-400">{open ? '−' : '+'}</span>
      </button>

      {open && (
        <div className="mt-4 space-y-3">
          <p className="text-sm text-slate-600">
            Paste this snippet into your blog post or page. Feel free to adjust the width and height.
          </p>
          <pre className="bg-slate-900 text-slate-100 text-xs p-4 rounded-lg overflow-x-auto">
            <code>{code}</code>
          </pre>
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-2 border border-cyan-600 text-cyan-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-cyan-100 transition-colors"
          >
            {copied ? 'Copied!' : 'Copy code'}
          </button>
        </div>
      )}
    </div>
  );
}
