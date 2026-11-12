import { test, expect } from '@playwright/test';
import { createAdmin, seedExchangeRate, signInAsAdmin } from '../helpers/admin';

let adminUsername = '';

test.beforeAll(async () => {
  adminUsername = createAdmin();
  await seedExchangeRate('2020-01-01', 'ZZA', 'ZZB', '12.345678', 'e2e-source');
  await seedExchangeRate('2020-01-02', 'ZZA', 'ZZC', '2.5', 'e2e-source');
});

test.describe('Admin exchange rates', () => {
  test('anonymous visitors are sent to the admin login', async ({ page }) => {
    await page.goto('/admin/exchange-rates');

    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('admin sees exchange rates in a table, newest first', async ({ page }) => {
    await signInAsAdmin(page, adminUsername);
    await page.getByRole('link', { name: 'Exchange rates' }).click();

    await expect(page.getByRole('heading', { name: 'Exchange rates' })).toBeVisible();
    await page.getByLabel('From').fill('zza');
    const rows = page.getByTestId('rate-row');
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0)).toContainText('2020-01-02');
    await expect(rows.nth(0)).toContainText('ZZA/ZZC');
    await expect(rows.nth(1)).toContainText('2020-01-01');
    await expect(rows.nth(1)).toContainText('ZZA/ZZB');
    await expect(rows.nth(1)).toContainText('12.3457');
    await expect(rows.nth(1)).toContainText('e2e-source');
  });

  test('filtering by both currencies narrows the table, and no match shows an empty message', async ({ page }) => {
    await signInAsAdmin(page, adminUsername);
    await page.goto('/admin/exchange-rates');

    await page.getByLabel('From').fill('ZZA');
    await page.getByLabel('To').fill('ZZB');
    await expect(page.getByTestId('rate-row')).toHaveCount(1);
    await expect(page.getByTestId('rate-row').first()).toContainText('ZZA/ZZB');

    await page.getByLabel('To').fill('QQQ');
    await expect(page.getByTestId('rate-row')).toHaveCount(0);
    await expect(page.getByText('No exchange rates found')).toBeVisible();
  });

  test('admin sees an error when the rates cannot be loaded', async ({ page }) => {
    await signInAsAdmin(page, adminUsername);
    await page.route('**/api/admin/exchange-rates**', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Database unavailable' } })
    );
    await page.goto('/admin/exchange-rates');

    await expect(page.getByTestId('rates-error')).toHaveText('Database unavailable');
  });

  test('an expired admin session sends the admin back to login', async ({ page }) => {
    await signInAsAdmin(page, adminUsername);
    await page.route('**/api/admin/exchange-rates**', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Could not validate credentials' } })
    );
    await page.goto('/admin/exchange-rates');

    await expect(page).toHaveURL(/.*admin\/login/);
  });
});
