export const config = {
  web3formsAccessKey: process.env.NEXT_PUBLIC_WEB3FORMS_ACCESS_KEY,
  privacyContactEmail: process.env.NEXT_PUBLIC_PRIVACY_CONTACT_EMAIL,
  appUrl: (process.env.NEXT_PUBLIC_APP_URL || 'https://app.fireons.com').replace(/\/$/, ''),
};

export const professionalParam = {
  name: 'type',
  value: 'professional',
};

export const appRoutes = {
  join: `${config.appUrl}/register`,
  signIn: `${config.appUrl}/login`,
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
