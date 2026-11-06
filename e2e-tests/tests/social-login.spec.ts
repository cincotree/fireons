import { test, expect } from '@playwright/test';
import { BACKEND_URL, createUserToken } from './support/session';

test.describe('Sign in with Google or Reddit, and the directory behind login', () => {
  test('the directory redirects signed-out visitors to login and returns them after logging in', async ({ page, request }) => {
    const username = `gate${Date.now()}`;
    await request.post(`${BACKEND_URL}/api/auth/register`, {
      data: { username, password: 'Test123!@#', email: `${username}@example.com`, primary_currency: 'USD' },
    });

    await page.goto('/professionals');

    await expect(page).toHaveURL(/\/login/);
    await page.getByLabel('Username').fill(username);
    await page.getByLabel('Password').fill('Test123!@#');
    await page.getByRole('button', { name: 'Login' }).click();

    await expect(page).toHaveURL(/\/professionals/);
    await expect(page.getByRole('heading', { level: 1, name: 'Find a registered financial professional' })).toBeVisible();
  });

  test('the registrations API rejects requests without a token', async ({ request }) => {
    for (const path of ['/api/registrations', '/api/registrations/sources', '/api/registrations/facets']) {
      const response = await request.get(`${BACKEND_URL}${path}`);
      expect([401, 403]).toContain(response.status());
    }
    const bad = await request.get(`${BACKEND_URL}/api/registrations`, { headers: { Authorization: 'Bearer nope' } });
    expect(bad.status()).toBe(401);
  });

  test('login and register pages offer Google and Reddit', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('link', { name: 'Continue with Google' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Continue with Reddit' })).toBeVisible();

    await page.goto('/register');
    await expect(page.getByRole('link', { name: 'Continue with Google' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Continue with Reddit' })).toBeVisible();
  });

  test('the social buttons are hidden when no provider is configured', async ({ page }) => {
    await page.route('**/api/auth/providers', (route) => route.fulfill({ json: { google: false, reddit: false } }));

    await page.goto('/login');

    await expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
    await expect(page.getByRole('link', { name: /Continue with/ })).toHaveCount(0);
  });

  test('the Google button starts the Google flow with this app\'s client id and no secret', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/auth/google/login`, { maxRedirects: 0 });

    expect(response.status()).toBe(302);
    const location = new URL(response.headers()['location']);
    expect(location.host).toBe('accounts.google.com');
    expect(location.searchParams.get('client_id')).toBe('e2e-google-client');
    expect(location.searchParams.get('redirect_uri')).toBe(`${BACKEND_URL}/auth/google/callback`);
    expect(location.toString()).not.toContain('e2e-google-secret');
    expect(response.headers()['set-cookie']).toContain('HttpOnly');
  });

  test('a provider callback with a forged state returns to login with a message', async ({ page }) => {
    await page.goto(`${BACKEND_URL}/api/auth/google/callback?code=abc&state=forged`);

    await expect(page).toHaveURL(/\/login\/?\?error=state_invalid/);
    await expect(page.getByText('That sign-in attempt expired or was not valid')).toBeVisible();
  });

  test('a cancelled sign-in shows a message on the login page', async ({ page }) => {
    await page.goto('/login?error=provider_denied');

    await expect(page.getByText('Sign-in was cancelled.')).toBeVisible();
  });

  test('a valid token from the callback signs the user in and returns to the page they wanted', async ({ page, request }) => {
    const token = await createUserToken(request, 'social');

    await page.goto('/professionals');
    await expect(page).toHaveURL(/\/login/);
    await page.goto(`/auth/callback/#token=${token}`);

    await expect(page).toHaveURL(/\/professionals/);
    await expect(page.getByRole('heading', { level: 1, name: 'Find a registered financial professional' })).toBeVisible();
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBe(token);
    expect(page.url()).not.toContain('token=');
  });

  test('an invalid token from the callback shows an error and leaves the user signed out', async ({ page }) => {
    await page.goto('/auth/callback/#token=not-a-real-token');

    await expect(page.getByText('Sign-in did not complete. Please try again.')).toBeVisible();
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();
    await page.getByRole('link', { name: 'Back to login' }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test('the callback page without a token shows an error', async ({ page }) => {
    await page.goto('/auth/callback/');

    await expect(page.getByText('Sign-in did not complete. Please try again.')).toBeVisible();
  });
});
