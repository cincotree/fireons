export const config = {
  web3formsAccessKey: process.env.NEXT_PUBLIC_WEB3FORMS_ACCESS_KEY,
};

export const SITE_URL = 'https://www.fireons.com';

export const professionalParam = {
  name: 'type',
  value: 'professional',
};

export const appRoutes = {
  waitlist: '/waitlist',
  waitlistProfessional: `/waitlist?${professionalParam.name}=${professionalParam.value}`,
  calculators: '/calculators',
  getStarted: '/get-started',
  retirementCalculator: '/calculators/retirement',
  coastFireCalculator: '/calculators/coast-fire',
  savingsRateCalculator: '/calculators/savings-rate',
  cityFireCalculator: '/calculators/fire-by-city',
  returnToIndiaCalculator: '/calculators/return-to-india',
  epfCalculator: '/calculators/epf',
  ppfCalculator: '/calculators/ppf',
  npsCalculator: '/calculators/nps',
  sipFireCalculator: '/calculators/sip-for-fire',
  lumpsumFireCalculator: '/calculators/lumpsum-for-fire',
};
