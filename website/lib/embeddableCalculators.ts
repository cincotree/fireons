import { ComponentType } from 'react';
import RetirementCalculator from '@/components/RetirementCalculator';
import CoastFireCalculator from '@/components/CoastFireCalculator';
import SavingsRateCalculator from '@/components/SavingsRateCalculator';
import CityFireCalculator from '@/components/CityFireCalculator';
import ReturnToIndiaCalculator from '@/components/ReturnToIndiaCalculator';
import EpfCalculator from '@/components/EpfCalculator';
import PpfCalculator from '@/components/PpfCalculator';
import NpsCalculator from '@/components/NpsCalculator';
import SipFireCalculator from '@/components/SipFireCalculator';
import LumpsumFireCalculator from '@/components/LumpsumFireCalculator';

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
  { slug: 'return-to-india', title: 'Return to India (NRI FIRE) Calculator', Component: ReturnToIndiaCalculator },
  { slug: 'epf', title: 'EPF Calculator for FIRE', Component: EpfCalculator },
  { slug: 'ppf', title: 'PPF Calculator for FIRE', Component: PpfCalculator },
  { slug: 'nps', title: 'NPS Calculator for FIRE', Component: NpsCalculator },
  { slug: 'sip-for-fire', title: 'SIP Calculator for FIRE', Component: SipFireCalculator },
  { slug: 'lumpsum-for-fire', title: 'Lumpsum Calculator for FIRE', Component: LumpsumFireCalculator },
];

export function findEmbeddableCalculator(slug: string): EmbeddableCalculator | undefined {
  return EMBEDDABLE_CALCULATORS.find((calculator) => calculator.slug === slug);
}
