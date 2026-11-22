import { test, expect } from '@playwright/test';
import { signIn } from './support/session';

test.describe('Account Closure - Removed Account No Longer Appears', () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page, 'closureuser');
    await page.goto('/networth');
    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();
  });

  test('closing an account removes it from the summary, charts, and hierarchy without a reload', async ({ page }) => {
    await page.getByRole('button', { name: 'Add Account' }).click();

    // select #0 is the page-level currency picker, #1 is Account Type (in
    // the modal), #2 is Category.
    const categorySelect = page.locator('select').nth(2);
    await categorySelect.selectOption({ label: '+ Create New Category' });
    await page.getByPlaceholder('Category name').fill('Bank');
    await page.getByPlaceholder(/Savings, Checking/).fill('ClosureBugAccount');
    await page.locator('input[type="number"]').fill('500');
    await page.getByRole('button', { name: 'Create Account' }).click();

    await page.waitForTimeout(1000);
    await expect(page.getByText('ClosureBugAccount')).toBeVisible();
    // New accounts default to the page's display currency (INR by default).
    await expect(page.getByText('₹500.00').first()).toBeVisible();

    await page.getByRole('button', { name: 'Edit account' }).click();
    await page.getByRole('button', { name: 'Remove account? click here' }).click();
    await page.getByRole('button', { name: 'Close Account' }).click();

    await page.waitForTimeout(1000);

    // Account Hierarchy no longer lists the closed account.
    await expect(page.getByText('ClosureBugAccount')).not.toBeVisible();
    await expect(page.getByText('No accounts yet.')).toBeVisible();

    // Net Worth Summary reflects the closure, not stale data.
    await expect(page.getByText('No net worth data available.')).toBeVisible();

    // Growth trend and Asset Allocation charts must also clear, not just the
    // hierarchy table (this was the actual bug: charts fetch independently
    // and kept showing the closed account's balance even after it
    // disappeared from the hierarchy).
    await expect(page.getByText('No historical data available.')).toBeVisible();
    await expect(page.getByText('No asset data available.')).toBeVisible();
  });
});
