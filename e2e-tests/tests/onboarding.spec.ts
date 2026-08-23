import { test, expect } from '@playwright/test';
import path from 'path';

const HDFC_PASSWORD = 'Fireons-Eval-Test-1234';
const HDFC_FIXTURE = path.join(__dirname, '../fixtures/onboarding-hdfc.pdf');
const ICICI_FIXTURE = path.join(__dirname, '../fixtures/onboarding-icici.pdf');
const SGB_FIXTURE = path.join(__dirname, '../fixtures/onboarding-sgb.pdf');

async function registerAndLogin(page: import('@playwright/test').Page) {
  const timestamp = Date.now() + Math.floor(Math.random() * 1000);
  const testUser = {
    email: `onboarding${timestamp}@example.com`,
    username: `onboarding${timestamp}`,
    password: 'Test123!@#',
  };

  await page.goto('/register');
  await page.getByLabel(/Email/i).fill(testUser.email);
  await page.getByLabel(/^Username/i).fill(testUser.username);
  await page.locator('input[name="password"]').fill(testUser.password);
  await page.getByRole('button', { name: /Create account/i }).click();
  await page.waitForURL(/.*networth/, { timeout: 5000 });
}

test.describe('Onboarding — statement import', () => {
  test.beforeEach(async ({ page }) => {
    await registerAndLogin(page);
    await page.goto('/onboarding');
  });

  test('multi-file upload: password requested only for the file that needs one, import succeeds, positions show on the dashboard', async ({ page }) => {
    await page.locator('input[type="file"]').setInputFiles([HDFC_FIXTURE, SGB_FIXTURE]);
    await page.getByRole('button', { name: 'Continue' }).click();

    // HDFC is encrypted — its row gets a password field.
    const hdfcRow = page.getByTestId('file-row-onboarding-hdfc.pdf');
    await expect(hdfcRow.getByPlaceholder('Password for this file')).toBeVisible();

    // The SGB confirmation is unencrypted — no password field, just a note.
    const sgbRow = page.getByTestId('file-row-onboarding-sgb.pdf');
    await expect(sgbRow.getByText('no password needed')).toBeVisible();
    await expect(sgbRow.getByPlaceholder('Password for this file')).not.toBeVisible();

    // Start Import is disabled until the required password is filled in.
    await expect(page.getByRole('button', { name: 'Start Import' })).toBeDisabled();
    await hdfcRow.getByPlaceholder('Password for this file').fill(HDFC_PASSWORD);
    await expect(page.getByRole('button', { name: 'Start Import' })).toBeEnabled();

    await page.getByRole('button', { name: 'Start Import' }).click();

    await expect(page.getByText(/Processing your 2 document/)).toBeVisible();
    await expect(page.getByText(/Imported \d+ position\(s\) from 2 document\(s\)/)).toBeVisible({
      timeout: 15000,
    });

    await page.getByRole('link', { name: 'Go to your net worth dashboard' }).click();
    await page.waitForURL(/.*networth/, { timeout: 5000 });
    await expect(page.getByText('HDFC').first()).toBeVisible();
  });

  test('no files need a password: the check step has nothing to fill in', async ({ page }) => {
    await page.locator('input[type="file"]').setInputFiles([SGB_FIXTURE]);
    await page.getByRole('button', { name: 'Continue' }).click();

    await expect(page.getByText('no password needed')).toBeVisible();
    await expect(page.getByPlaceholder('Password for this file')).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Start Import' })).toBeEnabled();
  });

  test('wrong password for one file: that file is quarantined with a warning, the rest of the batch still imports', async ({ page }) => {
    await page.locator('input[type="file"]').setInputFiles([HDFC_FIXTURE, ICICI_FIXTURE]);
    await page.getByRole('button', { name: 'Continue' }).click();

    const hdfcRow = page.getByTestId('file-row-onboarding-hdfc.pdf');
    const iciciRow = page.getByTestId('file-row-onboarding-icici.pdf');
    await hdfcRow.getByPlaceholder('Password for this file').fill('wrong-password');
    await iciciRow.getByPlaceholder('Password for this file').fill(HDFC_PASSWORD);

    await page.getByRole('button', { name: 'Start Import' }).click();

    await expect(page.getByText(/Imported \d+ position\(s\) from 2 document\(s\)/)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText('Warnings:')).toBeVisible();
    await expect(page.getByText(/onboarding-hdfc\.pdf.*password/)).toBeVisible();
  });

  test('choosing no files disables Continue with an inline message', async ({ page }) => {
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByText('Choose at least one statement PDF.')).toBeVisible();
  });
});

test.describe('Onboarding — statement import from the net worth dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await registerAndLogin(page);
  });

  test('Import Statement opens the same flow in place, without navigating away from /networth', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();

    // Still on /networth — this is a modal, not a page navigation.
    await expect(page).toHaveURL(/.*networth/);
    await expect(page.getByRole('heading', { name: 'Import your statements' })).toBeVisible();

    await page.locator('input[type="file"]').setInputFiles([SGB_FIXTURE]);
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByRole('button', { name: 'Start Import' })).toBeEnabled();
    await page.getByRole('button', { name: 'Start Import' }).click();

    await expect(page.getByText(/Imported \d+ position\(s\) from 1 document\(s\)/)).toBeVisible({
      timeout: 15000,
    });

    // "Done" closes the modal in place — no navigation link here, unlike the
    // standalone /onboarding page's "Go to your net worth dashboard" link.
    await page.getByRole('button', { name: 'Done' }).click();
    await expect(page).toHaveURL(/.*networth/);
    await expect(page.getByRole('heading', { name: 'Import your statements' })).not.toBeVisible();
    await expect(page.getByText('SGB').first()).toBeVisible();
  });
});
