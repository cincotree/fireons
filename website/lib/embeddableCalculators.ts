import { ComponentType } from 'react';
import RetirementCalculator from '@/components/RetirementCalculator';
import CoastFireCalculator from '@/components/CoastFireCalculator';
import SavingsRateCalculator from '@/components/SavingsRateCalculator';
import CityFireCalculator from '@/components/CityFireCalculator';

export interface EmbeddableCalculator {
  slug: string;
  title: string;
  Component: ComponentType;
}

export const EMBEDDABLE_CALCULATORS: EmbeddableCalculator[] = [
  { slug: 'retirement', title: 'Retirement Calculator', Component: RetirementCalculator },
  { slug: 'coast-fire', title: 'Coast FIRE Calculator', Component: CoastFireCalculator },
  { slug: 'savings-rate', title: 'Savings Rate Calculator', Component: SavingsRateCalculator },
  { slug: 'fire-by-city', title: 'FIRE Number by City Calculator', Component: CityFireCalculator },
];

export function findEmbeddableCalculator(slug: string): EmbeddableCalculator | undefined {
  return EMBEDDABLE_CALCULATORS.find((calculator) => calculator.slug === slug);
}
