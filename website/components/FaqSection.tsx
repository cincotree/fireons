export interface FaqItem {
  question: string;
  answer: string;
}

export default function FaqSection({ items }: { items: FaqItem[] }) {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: items.map((item) => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer,
      },
    })),
  };

  return (
    <section className="py-16 bg-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-8 text-center">
          Frequently asked questions
        </h2>
        <div className="space-y-3">
          {items.map((item) => (
            <details
              key={item.question}
              className="group bg-slate-50 rounded-xl border border-slate-100 px-6 py-4 open:bg-cyan-50/40 open:border-cyan-100"
            >
              <summary className="cursor-pointer font-semibold text-slate-900 list-none flex items-center justify-between gap-4">
                {item.question}
                <span className="text-slate-400 group-open:rotate-45 transition-transform text-xl leading-none">
                  +
                </span>
              </summary>
              <p className="text-slate-600 leading-relaxed mt-3">{item.answer}</p>
            </details>
          ))}
        </div>
      </div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
    </section>
  );
}
