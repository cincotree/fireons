import { APIRequestContext, Page } from '@playwright/test';

export const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8020';

export async function createUserToken(request: APIRequestContext, prefix = 'member'): Promise<string> {
  const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const credentials = { username: `${prefix}${suffix}`, password: 'Test123!@#' };
  const registered = await request.post(`${BACKEND_URL}/api/auth/register`, {
    data: { ...credentials, email: `${credentials.username}@example.com`, primary_currency: 'USD' },
  });
  if (!registered.ok()) throw new Error(`register failed: ${registered.status()}`);
  const login = await request.post(`${BACKEND_URL}/api/auth/login`, { data: credentials });
  return (await login.json()).access_token as string;
}

export async function signIn(page: Page, prefix = 'member'): Promise<string> {
  const token = await createUserToken(page.request, prefix);
  await page.addInitScript((value) => window.localStorage.setItem('token', value), token);
  return token;
}
