import { test, expect } from '@playwright/test';
import path from 'path';
import { BACKEND_URL, createUserToken, expireSession, signIn } from './support/session';


test.describe('Net worth consent', () => {
  test('a new user sees the notice instead of the dashboard and agree stays disabled until the box is ticked', async ({ page }) => {
    await signIn(page, 'consentnew', false);
    await page.goto('/networth');

    await expect(page.getByTestId('consent-gate')).toBeVisible();
    await expect(page.getByTestId('net-worth-notice')).toContainText('What we collect');
    await expect(page.getByRole('button', { name: 'Add Account' })).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'I agree and continue' })).toBeDisabled();

    await page.getByRole('checkbox').check();
    await expect(page.getByRole('button', { name: 'I agree and continue' })).toBeEnabled();
  });

  test('agreeing opens the dashboard and the choice is remembered on reload', async ({ page }) => {
    await signIn(page, 'consentagree', false);
    await page.goto('/networth');

    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'I agree and continue' }).click();

    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();
    await expect(page.getByTestId('consent-gate')).not.toBeVisible();
  });

  test('the statement import page is gated too', async ({ page }) => {
    await signIn(page, 'consentimport', false);
    await page.goto('/onboarding');

    await expect(page.getByTestId('consent-gate')).toBeVisible();
    await expect(page.locator('input[type="file"]')).toHaveCount(0);

    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'I agree and continue' }).click();
    await expect(page.locator('input[type="file"]')).toBeAttached();
  });

  test('without consent the API refuses an upload even if the UI is bypassed', async ({ page, request }) => {
    const token = await signIn(page, 'consentapi', false);

    const response = await request.post(`${BACKEND_URL}/ingestion/upload`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: { files: { name: 'sgb.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4') } },
    });

    expect(response.status()).toBe(403);
    expect((await response.json()).detail).toBe('consent_required');
  });

  test('a failed save shows an error and keeps the user on the notice', async ({ page }) => {
    await signIn(page, 'consentfail', false);
    await page.route('**/api/consent/net-worth', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({ status: 500, body: '{}' });
      } else {
        await route.continue();
      }
    });
    await page.goto('/networth');

    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'I agree and continue' }).click();

    await expect(page.getByText('Could not save your consent. Please try again.')).toBeVisible();
    await expect(page.getByTestId('consent-gate')).toBeVisible();
  });

  test('opening Net Worth after the session expired asks to sign in and then returns there', async ({ page }) => {
    await signIn(page, 'consentexpired');
    await page.goto('/privacy');
    await expect(page.getByTestId('consent-status')).toContainText('You agreed to notice version 1.0');

    await expireSession(page);
    await page.getByRole('link', { name: 'Net Worth' }).click();

    await expect(page).toHaveURL(/\/login\/?$/);
    await expect(page.getByText('Could not load your consent status')).not.toBeVisible();
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();

    const freshToken = await createUserToken('consentreturn');
    await page.goto(`/auth/callback/#token=${freshToken}`);
    await expect(page).toHaveURL(/\/networth\/?$/);
    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();
  });

  test('saving after the session expired on an open dashboard asks to sign in', async ({ page }) => {
    await signIn(page, 'consentidle');
    await page.goto('/networth');
    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.locator('select').nth(2).selectOption({ label: '+ Create New Category' });
    await page.getByPlaceholder('Category name').fill('Bank');
    await page.getByPlaceholder(/Savings, Checking/).fill('IdleTabAccount');

    await expireSession(page);
    await page.getByRole('button', { name: 'Create Account' }).click();

    await expect(page).toHaveURL(/\/login\/?$/);
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();
  });

  test('withdrawing on the Privacy page erases the data and gates the dashboard again', async ({ page }) => {
    await signIn(page, 'consentwithdraw', false);
    await page.goto('/networth');
    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'I agree and continue' }).click();
    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();

    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.locator('select').nth(2).selectOption({ label: '+ Create New Category' });
    await page.getByPlaceholder('Category name').fill('Bank');
    await page.getByPlaceholder(/Savings, Checking/).fill('ConsentEraseAccount');
    await page.locator('input[type="number"]').fill('250');
    await page.getByRole('button', { name: 'Create Account' }).click();
    await expect(page.getByText('ConsentEraseAccount')).toBeVisible();

    await page.getByRole('link', { name: 'Privacy' }).click();
    await expect(page.getByTestId('consent-status')).toContainText('You agreed to notice version 1.0');
    await page.getByRole('button', { name: 'Withdraw consent and delete my net worth data' }).click();
    await page.getByRole('button', { name: 'Keep my data' }).click();
    await expect(page.getByTestId('consent-status')).toContainText('You agreed to notice version 1.0');

    await page.getByRole('button', { name: 'Withdraw consent and delete my net worth data' }).click();
    await page.getByRole('button', { name: 'Yes, erase everything' }).click();
    await expect(page.getByRole('status')).toContainText('We erased 1 account(s)');
    await expect(page.getByTestId('consent-status')).toContainText('You have not given consent');

    await page.goto('/networth');
    await expect(page.getByTestId('consent-gate')).toBeVisible();
    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'I agree and continue' }).click();
    await expect(page.getByText('ConsentEraseAccount')).not.toBeVisible();
  });
});
