import { notFound } from 'next/navigation';
import { Metadata } from 'next';
import { EMBEDDABLE_CALCULATORS, findEmbeddableCalculator } from '@/lib/embeddableCalculators';

interface Props {
  params: Promise<{ calculator: string }>;
}

export function generateStaticParams() {
  return EMBEDDABLE_CALCULATORS.map((calculator) => ({ calculator: calculator.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { calculator: slug } = await params;
  const calculator = findEmbeddableCalculator(slug);
  return {
    title: calculator ? `${calculator.title} - Fireons` : 'Calculator - Fireons',
  };
}

export default async function EmbedCalculatorPage({ params }: Props) {
  const { calculator: slug } = await params;
  const calculator = findEmbeddableCalculator(slug);

  if (!calculator) {
    notFound();
  }

  const { Component } = calculator;

  return (
    <div className="bg-white min-h-screen px-4 py-6">
      <div className="max-w-2xl mx-auto">
        <Component />
        <div className="text-center mt-6">
          <a
            href={`/calculators/${calculator.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-slate-400 hover:text-cyan-600 transition-colors"
          >
            Powered by Fireons →
          </a>
        </div>
      </div>
    </div>
  );
}
