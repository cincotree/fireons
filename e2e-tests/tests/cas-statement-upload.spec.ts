import { test, expect } from '@playwright/test';
import path from 'path';

const CAS_TEST_PASSWORD = 'Fireons-CAS-Test-1234';
const VALID_FIXTURE = path.join(__dirname, '../fixtures/cas-statement-sample.pdf');
const REUPLOAD_BEFORE_FIXTURE = path.join(__dirname, '../fixtures/cas-statement-reupload-before.pdf');
const REUPLOAD_AFTER_FIXTURE = path.join(__dirname, '../fixtures/cas-statement-reupload-after.pdf');
const NON_PDF_FIXTURE = path.join(__dirname, '../fixtures/not-a-pdf.txt');

test.describe('Mutual Fund CAS Import', () => {
  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const testUser = {
      email: `casimport${timestamp}@example.com`,
      username: `casimport${timestamp}`,
      password: 'Test123!@#'
    };

    await page.goto('/register');
    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.getByRole('button', { name: /Create account/i }).click();

    await page.waitForURL(/.*networth/, { timeout: 5000 });
  });

  test('upload CAS statement, preview holdings, uncheck and edit, and confirm creates accounts', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Mutual Fund CAS/i }).click();

    await page.locator('input[type="file"]').setInputFiles(VALID_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill(CAS_TEST_PASSWORD);
    await page.getByRole('button', { name: 'Parse CAS' }).click();

    // Preview step shows all four synthetic holdings.
    const schemeNameInputs = page.locator('table input[type="text"]');
    await expect(schemeNameInputs).toHaveCount(4);
    await expect(page.getByText('4 of 4 selected')).toBeVisible();

    // Uncheck one holding (won't be imported).
    await page.locator('table input[type="checkbox"]').nth(0).uncheck();
    await expect(page.getByText('3 of 4 selected')).toBeVisible();

    // Edit another holding's market value.
    const marketValueInputs = page.locator('table input[type="number"]');
    await marketValueInputs.nth(1).fill('99999.99');

    await page.getByRole('button', { name: /Import 3 Holdings/ }).click();
    await expect(page.getByText(/Created 3, updated 0/)).toBeVisible();
    await page.waitForTimeout(1500);

    await expect(page.getByText('Alpha Small Cap Fund - Direct Growth')).toBeVisible();
    await expect(page.getByText('99,999.99').first()).toBeVisible();

    const summarySection = page.locator('.bg-white').filter({ hasText: 'Net Worth Summary' });
    await expect(summarySection.getByText(/Net Worth:/)).toBeVisible();
  });

  test('re-uploading the same folio and scheme updates the existing account instead of duplicating', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Mutual Fund CAS/i }).click();

    await page.locator('input[type="file"]').setInputFiles(REUPLOAD_BEFORE_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill(CAS_TEST_PASSWORD);
    await page.getByRole('button', { name: 'Parse CAS' }).click();

    await expect(page.getByText('New account')).toBeVisible();
    await page.getByRole('button', { name: /Import 1 Holdings/ }).click();
    await expect(page.getByText(/Created 1, updated 0/)).toBeVisible();
    await page.waitForTimeout(1500);

    await expect(page.getByText('Gamma Growth Fund')).toBeVisible();
    const leafCountBefore = await page.getByText('Gamma Growth Fund').count();

    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Mutual Fund CAS/i }).click();

    await page.locator('input[type="file"]').setInputFiles(REUPLOAD_AFTER_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill(CAS_TEST_PASSWORD);
    await page.getByRole('button', { name: 'Parse CAS' }).click();

    await expect(page.getByText(/Will update/)).toBeVisible();
    await page.getByRole('button', { name: /Import 1 Holdings/ }).click();
    await expect(page.getByText(/Created 0, updated 1/)).toBeVisible();
    await page.waitForTimeout(1500);

    await expect(await page.getByText('Gamma Growth Fund').count()).toBe(leafCountBefore);
    await expect(page.getByText('60,500.00').first()).toBeVisible();
  });

  test('wrong password shows an inline error and allows retry', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Mutual Fund CAS/i }).click();

    await page.locator('input[type="file"]').setInputFiles(VALID_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill('wrong-password');
    await page.getByRole('button', { name: 'Parse CAS' }).click();

    await expect(page.getByText('Incorrect password for the uploaded PDF.')).toBeVisible();
    await expect(page.getByRole('button', { name: /Import \d+ Holdings/ })).not.toBeVisible();

    await page.getByPlaceholder('Password used to open the PDF').fill(CAS_TEST_PASSWORD);
    await page.getByRole('button', { name: 'Parse CAS' }).click();

    await expect(page.locator('table input[type="text"]')).toHaveCount(4);
  });

  test('non-PDF file upload surfaces an inline error instead of crashing', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Mutual Fund CAS/i }).click();

    await page.locator('input[type="file"]').setInputFiles(NON_PDF_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill('irrelevant');
    await page.getByRole('button', { name: 'Parse CAS' }).click();

    await expect(page.getByText(/Could not read PDF/)).toBeVisible();
    await expect(page.getByRole('button', { name: /Import \d+ Holdings/ })).not.toBeVisible();
  });
});
