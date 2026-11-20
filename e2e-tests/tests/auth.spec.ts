import { test, expect } from '@playwright/test';
import { signIn } from './support/session';

test.describe('Authentication Feature - Critical User Journeys', () => {
  test('a signed-in user sees their name in the navigation and can log out', async ({ page }) => {
    await signIn(page, 'logoutuser');

    await page.goto('/networth');

    await expect(page.getByText(/logoutuser/)).toBeVisible();
    await page.getByRole('button', { name: /Logout/i }).click();
    await expect(page).toHaveURL(/.*login/);
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();

    await page.goto('/networth');
    await expect(page).toHaveURL(/.*login/);
  });

  test('protected route redirects unauthenticated user to login', async ({ page }) => {
    await page.goto('/networth');

    await expect(page).toHaveURL(/.*login/);
  });

  test('authenticated user accessing root redirects to networth', async ({ page }) => {
    await signIn(page, 'rootuser');

    await page.goto('/');

    await expect(page).toHaveURL(/.*networth/, { timeout: 10000 });
  });

  test('unauthenticated user accessing root redirects to login', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveURL(/.*login/, { timeout: 10000 });
  });

  test('an invalid stored token is discarded and the user is sent to login', async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem('token', 'not-a-real-token'));

    await page.goto('/networth');

    await expect(page).toHaveURL(/.*login/);
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();
  });

  test('the login page has no username or password fields', async ({ page }) => {
    await page.goto('/login');

    await expect(page.getByRole('link', { name: 'Continue with Google' })).toBeVisible();
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await expect(page.getByLabel('Username')).toHaveCount(0);
  });

  test('the old password endpoints no longer exist', async ({ request }) => {
    const backend = process.env.BACKEND_URL || 'http://localhost:8020';

    const login = await request.post(`${backend}/api/auth/login`, { data: { username: 'a', password: 'b' } });
    const register = await request.post(`${backend}/api/auth/register`, {
      data: { username: 'a', password: 'bbbbbb', email: 'a@example.com' },
    });

    expect(login.status()).toBe(404);
    expect(register.status()).toBe(404);
  });

  test('navigation links between login and join work', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('link', { name: 'Join Fireons' }).click();
    await expect(page).toHaveURL(/.*register/);

    await page.getByRole('link', { name: 'Login' }).click();
    await expect(page).toHaveURL(/.*login/);
  });
});
