import { MetadataRoute } from 'next';
import { SITE_URL, appRoutes } from '@/lib/config';

export const dynamic = 'force-static';

const CALCULATOR_PATHS = [
  appRoutes.calculators,
  appRoutes.retirementCalculator,
  appRoutes.coastFireCalculator,
  appRoutes.savingsRateCalculator,
  appRoutes.cityFireCalculator,
  appRoutes.returnToIndiaCalculator,
  appRoutes.epfCalculator,
  appRoutes.ppfCalculator,
  appRoutes.npsCalculator,
  appRoutes.sipFireCalculator,
  appRoutes.lumpsumFireCalculator,
];

const OTHER_PATHS = ['/about', '/features', '/for-professionals', '/privacy', appRoutes.waitlist, appRoutes.getStarted];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  return [
    { url: SITE_URL, lastModified, changeFrequency: 'monthly', priority: 1 },
    ...CALCULATOR_PATHS.map((path) => ({
      url: `${SITE_URL}${path}`,
      lastModified,
      changeFrequency: 'monthly' as const,
      priority: 0.9,
    })),
    ...OTHER_PATHS.map((path) => ({
      url: `${SITE_URL}${path}`,
      lastModified,
      changeFrequency: 'monthly' as const,
      priority: 0.6,
    })),
  ];
}
