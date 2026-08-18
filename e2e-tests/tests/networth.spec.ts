import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8020';

function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

async function seedExchangeRate(
  request: import('@playwright/test').APIRequestContext,
  fromCurrency: string,
  toCurrency: string,
  rate: number
) {
  const response = await request.post(`${BACKEND_URL}/api/exchange-rates`, {
    data: { from_currency: fromCurrency, to_currency: toCurrency, rate },
  });
  expect(response.ok()).toBeTruthy();
}

test.describe('Net Worth Feature - Critical User Journeys', () => {
  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const testUser = {
      email: `networthuser${timestamp}@example.com`,
      username: `networthuser${timestamp}`,
      password: 'Test123!@#'
    };

    await page.goto('/register');
    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.getByRole('button', { name: /Create account/i }).click();

    await page.waitForURL(/.*networth/, { timeout: 5000 });
  });

  // Account creation and its initial balance are now one combined step in a
  // single modal — there is no separate "Set Balance" flow to drive
  // afterwards. A brand-new user also has no existing categories yet, so
  // every creation must go through "+ Create New Category".
  async function createAccount(
    page: import('@playwright/test').Page,
    opts: { type: 'Assets' | 'Liabilities'; category: string; name: string; currency: string; balance: string }
  ) {
    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.getByTestId('account-type-select').selectOption(opts.type);
    await page.getByTestId('account-category-select').selectOption('_new_');
    await page.getByTestId('account-category-new-input').fill(opts.category);
    await page.getByTestId('account-name-input').fill(opts.name);
    await page.getByTestId('account-currency-select').selectOption(opts.currency);
    await page.getByTestId('account-balance-input').fill(opts.balance);
    await page.getByRole('button', { name: 'Create Account' }).click();
    await page.waitForTimeout(1000);
  }

  test('complete workflow: create asset account with an initial balance and view net worth', async ({ page }) => {
    const timestamp = Date.now();
    const accountName = `Checking${timestamp}`;

    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}`,
      name: accountName,
      currency: 'USD',
      balance: '10000',
    });

    await expect(page.getByText(accountName)).toBeVisible();

    await page.getByTestId('display-currency-select').selectOption('USD');
    await page.waitForTimeout(500);

    const summary = page.getByTestId('networth-summary');
    await expect(summary.getByText(/Assets:/)).toBeVisible();
    await expect(summary.getByText(/Net Worth:/)).toBeVisible();
    await expect(summary.getByText('$10,000.00').first()).toBeVisible();
  });

  test('complete workflow: create liability account and view negative impact on net worth', async ({ page }) => {
    const timestamp = Date.now();
    const accountName = `Visa${timestamp}`;

    await createAccount(page, {
      type: 'Liabilities',
      category: `CreditCard${timestamp}`,
      name: accountName,
      currency: 'USD',
      balance: '5000',
    });

    await expect(page.getByText(accountName)).toBeVisible();

    await page.getByTestId('display-currency-select').selectOption('USD');
    await page.waitForTimeout(500);

    const summary = page.getByTestId('networth-summary');
    await expect(summary.getByText(/Liabilities:/)).toBeVisible();
    // Net worth goes negative when the only account is a liability.
    await expect(summary.getByText('-$5,000.00')).toBeVisible();
  });

  test('display currency dropdown defaults to INR on a fresh dashboard load', async ({ page }) => {
    await expect(page.getByTestId('display-currency-select')).toHaveValue('INR');
  });

  test('multi-currency workflow: switching display currency converts every row, not just totals', async ({ page, request }) => {
    const timestamp = Date.now();
    const usdAccount = `USD${timestamp}`;
    const inrAccount = `INR${timestamp}`;
    const rate = 83;

    await seedExchangeRate(request, 'USD', 'INR', rate);

    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}`,
      name: usdAccount,
      currency: 'USD',
      balance: '1000',
    });
    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}`,
      name: inrAccount,
      currency: 'INR',
      balance: '50000',
    });

    await expect(page.getByText(usdAccount)).toBeVisible();
    await expect(page.getByText(inrAccount)).toBeVisible();
    // Dashboard defaults to INR — the USD account's row should already be
    // shown converted, not in raw USD digits.
    await expect(page.getByText(formatCurrency(1000 * rate, 'INR'))).toBeVisible();
    await expect(page.getByText(formatCurrency(50000, 'INR'))).toBeVisible();

    const summary = page.getByTestId('networth-summary');
    await expect(summary.getByText('Net Worth Summary (INR)')).toBeVisible();
    await expect(summary.getByText(/Net Worth:/)).toBeVisible();

    // Switching to USD must convert the INR row too, and leave the USD row
    // unchanged (same-currency short circuit).
    await page.getByTestId('display-currency-select').selectOption('USD');
    await page.waitForTimeout(500);
    await expect(page.getByText(formatCurrency(1000, 'USD'))).toBeVisible();
    await expect(page.getByText(formatCurrency(50000 / rate, 'USD'))).toBeVisible();
    await expect(summary.getByText('Net Worth Summary (USD)')).toBeVisible();
  });

  test('triangulated conversion: no direct rate between two currencies still converts via USD', async ({ page, request }) => {
    const timestamp = Date.now();
    const eurAccount = `EUR${timestamp}`;

    // Only USD-anchored legs are seeded — no direct or inverse EUR<->JPY
    // rate exists anywhere. Conversion can only succeed by triangulating
    // EUR -> USD -> JPY.
    await seedExchangeRate(request, 'USD', 'EUR', 0.5);
    await seedExchangeRate(request, 'USD', 'JPY', 100);

    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}`,
      name: eurAccount,
      currency: 'EUR',
      balance: '100',
    });

    await expect(page.getByText(eurAccount)).toBeVisible();

    await page.getByTestId('display-currency-select').selectOption('JPY');
    await page.waitForTimeout(500);

    // 100 EUR -> USD (via inverse of 0.5) -> JPY (via 100) = 20,000 JPY.
    await expect(page.getByText(formatCurrency(20000, 'JPY')).first()).toBeVisible();
    await expect(page.getByText('rate unavailable', { exact: true })).not.toBeVisible();
  });

  test('rate unavailable: switching to a currency with no conversion path flags the row instead of guessing', async ({ page }) => {
    const timestamp = Date.now();
    const accountName = `NoRate${timestamp}`;

    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}`,
      name: accountName,
      currency: 'GBP',
      balance: '100',
    });

    await expect(page.getByText(accountName)).toBeVisible();

    // No GBP<->CAD rate, direct/inverse/USD-bridged, is ever seeded in this
    // suite (no test seeds USD->GBP), so this must surface as unavailable
    // rather than silently showing a wrong number.
    await page.getByTestId('display-currency-select').selectOption('CAD');
    await page.waitForTimeout(500);

    await expect(page.getByText('rate unavailable', { exact: true })).toBeVisible();
    const summary = page.getByTestId('networth-summary');
    await expect(summary.getByText(/exchange rate unavailable/i)).toBeVisible();
  });

  test('navigation and page load', async ({ page }) => {
    // "/" redirects an authenticated user to "/networth" — go there directly
    // and confirm it lands and renders correctly, rather than racing the
    // redirect via a conditional nav-link click.
    await page.goto('/');
    await page.waitForURL(/.*networth/, { timeout: 5000 });

    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Account Hierarchy' })).toBeVisible();
    await expect(page.getByTestId('networth-summary')).toBeVisible();
  });

  test('data isolation: users can only see their own accounts', async ({ page }) => {
    const timestamp = Date.now();

    const user1AccountName = `User1Account${timestamp}`;
    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}`,
      name: user1AccountName,
      currency: 'USD',
      balance: '100',
    });
    await expect(page.getByText(user1AccountName)).toBeVisible();

    await page.getByRole('button', { name: /Logout/i }).click();
    await page.waitForURL(/.*login/, { timeout: 3000 });

    const user2 = {
      email: `networthuser2${timestamp}@example.com`,
      username: `networthuser2${timestamp}`,
      password: 'Test123!@#'
    };

    await page.goto('/register');
    await page.getByLabel(/Email/i).fill(user2.email);
    await page.getByLabel(/^Username/i).fill(user2.username);
    await page.locator('input[name="password"]').fill(user2.password);
    await page.getByRole('button', { name: /Create account/i }).click();
    await page.waitForURL(/.*networth/, { timeout: 5000 });

    // User 2 should NOT see User 1's account.
    await expect(page.getByText(user1AccountName)).not.toBeVisible();

    const user2AccountName = `User2Account${timestamp}`;
    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}`,
      name: user2AccountName,
      currency: 'USD',
      balance: '200',
    });

    await expect(page.getByText(user2AccountName)).toBeVisible();
    await expect(page.getByText(user1AccountName)).not.toBeVisible();
  });
});
