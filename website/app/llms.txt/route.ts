import { SITE_URL, appRoutes } from '@/lib/config';

export const dynamic = 'force-static';

interface LlmsPage {
  path: string;
  name: string;
  description: string;
}

const CALCULATORS: LlmsPage[] = [
  {
    path: appRoutes.retirementCalculator,
    name: 'Retirement Calculator',
    description:
      'How much to invest monthly to retire on your own terms, based on a full year-by-year accumulation and withdrawal simulation.',
  },
  {
    path: appRoutes.coastFireCalculator,
    name: 'Coast FIRE Calculator',
    description: "Whether you've already saved enough to stop investing and still retire comfortably.",
  },
  {
    path: appRoutes.savingsRateCalculator,
    name: 'Savings Rate Calculator',
    description: 'How many years until financial independence, based on your current savings rate.',
  },
  {
    path: appRoutes.cityFireCalculator,
    name: 'FIRE Number by City',
    description: 'FIRE number adjusted for the cost of living in a specific Indian city or region.',
  },
  {
    path: appRoutes.returnToIndiaCalculator,
    name: 'Return to India Calculator',
    description:
      'For NRIs: FIRE number in rupees and required monthly investment in dollars, accounting for the exchange rate and rupee depreciation.',
  },
  {
    path: appRoutes.epfCalculator,
    name: 'EPF Calculator',
    description: 'Projected Employee Provident Fund corpus at retirement.',
  },
  {
    path: appRoutes.ppfCalculator,
    name: 'PPF Calculator',
    description: 'Projected Public Provident Fund corpus at a target age.',
  },
  {
    path: appRoutes.npsCalculator,
    name: 'NPS Calculator',
    description: 'Projected National Pension System corpus, tax-free lump sum, and monthly pension.',
  },
  {
    path: appRoutes.sipFireCalculator,
    name: 'SIP Calculator for FIRE',
    description: 'Whether a given monthly SIP is enough to reach a FIRE number, and by what age.',
  },
  {
    path: appRoutes.lumpsumFireCalculator,
    name: 'Lumpsum Calculator for FIRE',
    description: 'Whether a one-time investment is enough to reach a FIRE number, and by what age.',
  },
];

const OTHER_PAGES: LlmsPage[] = [
  { path: '/about', name: 'About FIRE', description: 'What the FIRE movement is and how it works.' },
  { path: appRoutes.calculators, name: 'All Calculators', description: 'Full list of free FIRE calculators.' },
  {
    path: appRoutes.getStarted,
    name: 'Get Started',
    description: 'A short quiz that routes to the right calculator for your situation.',
  },
  {
    path: appRoutes.waitlist,
    name: 'Join the Waitlist',
    description: 'Sign up for the Fireons net worth tracking app.',
  },
];

function formatSection(title: string, pages: LlmsPage[]): string {
  const lines = pages.map((page) => `- [${page.name}](${SITE_URL}${page.path}): ${page.description}`);
  return `## ${title}\n\n${lines.join('\n')}`;
}

export function GET(): Response {
  const body = [
    '# Fireons',
    '',
    '> Community for FIRE enthusiasts. Free, browser-only calculators for Financial Independence, Retire Early (FIRE) planning in India — all calculations run client-side, nothing entered is ever sent anywhere.',
    '',
    formatSection('Calculators', CALCULATORS),
    '',
    formatSection('Other pages', OTHER_PAGES),
    '',
  ].join('\n');

  return new Response(body, {
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
}
