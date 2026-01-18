// Configuration for the Fireones application
export const config = {
  // URL of the main Fireones application
  // In development: http://localhost:3000
  // In production: your deployed app URL
  appUrl: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
};

// Helper function to get app routes
export const appRoutes = {
  login: `${config.appUrl}/login`,
  register: `${config.appUrl}/register`,
  registerProfessional: `${config.appUrl}/register?type=professional`,
  networth: `${config.appUrl}/networth`,
  home: config.appUrl,
};
