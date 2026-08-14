import { test, expect, Page } from '@playwright/test';

async function createAccount(page: Page, options: {
  type?: 'Assets' | 'Liabilities';
  category: string;
  name: string;
  currency?: string;
  balance?: number;
  description?: string;
}) {
  const { type = 'Assets', category, name, currency = 'USD', balance, description } = options;

  await page.getByRole('button', { name: 'Add Account' }).click();

  // The modal's <Modal> component renders as plain divs with no role="dialog",
  // so it can't be scoped by ARIA role. Its selects render after the page-level
  // currency selector in DOM order: [0] page currency, [1] Account Type,
  // [2] Category (existing-list) until switched to "+ Create New Category",
  // after which the Category <select> unmounts and Currency becomes [2].
  await page.locator('select').nth(1).selectOption(type);
  await page.locator('select').nth(2).selectOption('_new_');
  await page.getByPlaceholder('Category name').fill(category);
  await page.getByPlaceholder(/e\.g\., Savings, Checking, Home Loan/).fill(name);

  if (currency !== 'USD') {
    await page.locator('select').nth(2).selectOption(currency);
  }

  if (balance !== undefined) {
    await page.getByPlaceholder('0.00').fill(String(balance));
  }

  if (description) {
    await page.getByPlaceholder('Add notes about this account...').fill(description);
  }

  await page.getByRole('button', { name: 'Create Account' }).click();
  await page.waitForTimeout(1000);
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

  test('complete workflow: create asset account, set balance, view net worth', async ({ page }) => {
    await expect(page.getByText('Net Worth Summary')).toBeVisible();

    const accountName = `Checking${Date.now()}`;

    await createAccount(page, {
      type: 'Assets',
      category: 'Bank',
      name: accountName,
      currency: 'USD',
      balance: 10000,
      description: 'My checking account',
    });

    await expect(page.getByText(accountName)).toBeVisible();

    const summarySection = page.locator('.bg-white').filter({ hasText: 'Net Worth Summary' });
    await expect(summarySection.getByText('Assets:')).toBeVisible();
    await expect(summarySection.getByText(/10,000\.00/).first()).toBeVisible();
    await expect(summarySection.getByText('Net Worth:')).toBeVisible();
  });

  test('complete workflow: create liability account and view negative impact on net worth', async ({ page }) => {
    const accountName = `Visa${Date.now()}`;

    await createAccount(page, {
      type: 'Liabilities',
      category: 'CreditCard',
      name: accountName,
      currency: 'USD',
      balance: 5000,
    });

    await expect(page.getByText(accountName)).toBeVisible();

    const summarySection = page.locator('.bg-white').filter({ hasText: 'Net Worth Summary' });
    await expect(summarySection.getByText('Liabilities:')).toBeVisible();
    await expect(summarySection.getByText(/5,000\.00/).first()).toBeVisible();
  });

  test('multi-currency workflow: create accounts in different currencies', async ({ page }) => {
    const timestamp = Date.now();
    const usdName = `USDChecking${timestamp}`;
    const inrName = `INRSavings${timestamp}`;

    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}A`,
      name: usdName,
      currency: 'USD',
      balance: 1000,
    });

    await createAccount(page, {
      type: 'Assets',
      category: `Bank${timestamp}B`,
      name: inrName,
      currency: 'INR',
      balance: 50000,
    });

    await expect(page.getByText(usdName)).toBeVisible();
    await expect(page.getByText(inrName)).toBeVisible();

    await expect(page.getByText('Net Worth Summary (USD)')).toBeVisible();

    const currencySelector = page.locator('select').first();
    await currencySelector.selectOption('INR');
    await expect(page.getByText('Net Worth Summary (INR)')).toBeVisible();
  });

  test('navigation and page load', async ({ page }) => {
    // Already authenticated from beforeEach: the root path's own auth check
    // decides the redirect, so wait for that instead of racing it with an
    // immediate isVisible() check (which can catch the page mid-redirect).
    await page.goto('/');
    await page.waitForURL(/.*networth/, { timeout: 10000 });

    await expect(page.getByText('Net Worth Summary')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Account Hierarchy' })).toBeVisible();
  });

  test('data isolation: users can only see their own accounts', async ({ page }) => {
    const timestamp = Date.now();

    const user1AccountName = `User1Account${timestamp}`;
    await createAccount(page, {
      type: 'Assets',
      category: 'Bank',
      name: user1AccountName,
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

    await expect(page.getByText(user1AccountName)).not.toBeVisible();

    const user2AccountName = `User2Account${timestamp}`;
    await createAccount(page, {
      type: 'Assets',
      category: 'Bank',
      name: user2AccountName,
    });

    await expect(page.getByText(user2AccountName)).toBeVisible();
    await expect(page.getByText(user1AccountName)).not.toBeVisible();
  });
});
