export const config = {
  web3formsAccessKey: process.env.NEXT_PUBLIC_WEB3FORMS_ACCESS_KEY,
};

export const professionalParam = {
  name: 'type',
  value: 'professional',
};

export const appRoutes = {
  waitlist: '/waitlist',
  waitlistProfessional: `/waitlist?${professionalParam.name}=${professionalParam.value}`,
};
