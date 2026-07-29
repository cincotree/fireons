import { test, expect } from '@playwright/test';
import path from 'path';

const HDFC_TEST_PASSWORD = 'Fireons-Test-1234';
const VALID_FIXTURE = path.join(__dirname, '../fixtures/hdfc-statement-sample.pdf');
const NON_PDF_FIXTURE = path.join(__dirname, '../fixtures/not-a-pdf.txt');

test.describe('Bank Statement Import - HDFC', () => {
  test.beforeEach(async ({ page }) => {
    const timestamp = Date.now();
    const testUser = {
      email: `statementimport${timestamp}@example.com`,
      username: `statementimport${timestamp}`,
      password: 'Test123!@#'
    };

    await page.goto('/register');
    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.getByRole('button', { name: /Create account/i }).click();

    await page.waitForURL(/.*networth/, { timeout: 5000 });
  });

  test('upload HDFC statement, preview extracted data, edit, and confirm creates account with balance', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Bank Statement/i }).click();

    await page.locator('input[type="file"]').setInputFiles(VALID_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill(HDFC_TEST_PASSWORD);
    await page.getByRole('button', { name: 'Parse Statement' }).click();

    // Preview step shows the extracted data.
    const textInputs = page.locator('input[type="text"]');
    const accountNameInput = textInputs.nth(0);
    await expect(accountNameInput).toHaveValue('Assets:Bank:HDFC:6789');
    await expect(page.locator('input[type="number"]')).toHaveValue('128456.78');
    await expect(textInputs.nth(1)).toHaveValue('50100123456789'); // Account Number
    await expect(textInputs.nth(2)).toHaveValue('MR. TEST USER'); // Account Holder Name

    // The Account Hierarchy tree renders only the leaf segment of a
    // colon-delimited account name, not the full path, so assert on that.
    const uniqueLeaf = `Import${Date.now()}`;
    await accountNameInput.fill(`Assets:Bank:HDFC:${uniqueLeaf}`);

    await page.getByRole('button', { name: 'Create Account' }).click();
    await page.waitForTimeout(1000);

    await expect(page.getByText(uniqueLeaf)).toBeVisible();
    await expect(page.getByText('128,456.78').first()).toBeVisible();

    const summarySection = page.locator('.bg-white').filter({ hasText: 'Net Worth Summary' });
    await expect(summarySection.getByText(/Net Worth:/)).toBeVisible();
  });

  test('wrong password shows an inline error and allows retry', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Bank Statement/i }).click();

    await page.locator('input[type="file"]').setInputFiles(VALID_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill('wrong-password');
    await page.getByRole('button', { name: 'Parse Statement' }).click();

    await expect(page.getByText('Incorrect password for the uploaded PDF.')).toBeVisible();
    // The preview step must not have been reached.
    await expect(page.getByRole('button', { name: 'Create Account' })).not.toBeVisible();

    // Retry with the correct password succeeds.
    await page.getByPlaceholder('Password used to open the PDF').fill(HDFC_TEST_PASSWORD);
    await page.getByRole('button', { name: 'Parse Statement' }).click();

    await expect(page.locator('input[type="number"]')).toHaveValue('128456.78');
  });

  test('non-PDF file upload surfaces an inline error instead of crashing', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Bank Statement/i }).click();

    await page.locator('input[type="file"]').setInputFiles(NON_PDF_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill('irrelevant');
    await page.getByRole('button', { name: 'Parse Statement' }).click();

    await expect(page.getByText(/Could not read PDF/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create Account' })).not.toBeVisible();
  });

  test('editing the closing balance and statement date before confirming persists the edited values', async ({ page }) => {
    await page.getByRole('button', { name: 'Import Statement' }).click();
    await page.getByRole('button', { name: /Bank Statement/i }).click();

    await page.locator('input[type="file"]').setInputFiles(VALID_FIXTURE);
    await page.getByPlaceholder('Password used to open the PDF').fill(HDFC_TEST_PASSWORD);
    await page.getByRole('button', { name: 'Parse Statement' }).click();

    await expect(page.locator('input[type="number"]')).toHaveValue('128456.78');

    await page.locator('input[type="number"]').fill('99999.99');
    await page.locator('input[type="date"]').fill('2025-04-15');

    await page.getByRole('button', { name: 'Create Account' }).click();
    await page.waitForTimeout(1000);

    await expect(page.getByText('99,999.99').first()).toBeVisible();
    await expect(page.getByText('128,456.78')).not.toBeVisible();
  });
});
