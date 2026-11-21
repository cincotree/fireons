import { test, expect } from '@playwright/test';
import { adminLogin, createAdmin } from '../helpers/admin';
import { signIn } from './support/session';

let adminUsername = '';

test.beforeAll(() => {
  adminUsername = createAdmin();
});

test.describe('Admin jobs', () => {
  test('anonymous visitors are sent to the admin login', async ({ page }) => {
    await page.goto('/admin/jobs');

    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('a signed in regular user has no admin access and sees no admin link', async ({ page }) => {
    await signIn(page, 'plainjobs');
    await page.goto('/networth');
    await expect(page.getByRole('button', { name: 'Add Account' })).toBeVisible();

    await expect(page.getByRole('link', { name: /jobs/i })).toHaveCount(0);
    await page.goto('/admin/jobs');

    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('wrong password shows an error and stays on the login page', async ({ page }) => {
    await adminLogin(page, adminUsername, 'not-the-password');

    await expect(page.getByTestId('admin-login-error')).toHaveText('Invalid username or password');
    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('regular user credentials do not work on the admin login', async ({ page }) => {
    await adminLogin(page, 'someregularuser', 'Test123!@#');

    await expect(page.getByTestId('admin-login-error')).toHaveText('Invalid username or password');
  });

  test('admin signs in, launches a job, sees it finish, and signs out', async ({ page }) => {
    await adminLogin(page, adminUsername);

    await expect(page.getByRole('heading', { name: 'Background jobs' })).toBeVisible();
    await expect(page.getByLabel('Job')).toHaveValue('exchange_rate_sync');

    await page.getByRole('button', { name: 'Launch job' }).click();

    const row = page.getByTestId('job-run').first();
    await expect(row).toContainText('exchange_rate_sync');
    await expect(row.getByTestId('job-run-task')).toHaveText(/^local:\d+$/);
    await expect(row.getByTestId('job-run-status')).toHaveText(/succeeded|failed/, { timeout: 30000 });
    const finalStatus = (await row.getByTestId('job-run-status').textContent()) as string;

    await page.getByLabel('Status').selectOption(finalStatus);
    await expect(page.getByTestId('job-run').first()).toBeVisible();
    await expect
      .poll(async () => {
        const statuses = await page.getByTestId('job-run-status').allTextContents();
        return statuses.length > 0 && statuses.every((status) => status === finalStatus);
      })
      .toBe(true);

    await page.getByRole('link', { name: 'Exchange rates' }).click();
    await expect(page).toHaveURL(/.*admin\/exchange-rates/);
    await page.getByRole('link', { name: 'Jobs' }).click();
    await expect(page.getByRole('heading', { name: 'Background jobs' })).toBeVisible();

    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page).toHaveURL(/.*admin\/login/);
    await page.goto('/admin/jobs');
    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('admin sees validation errors for a bad payload', async ({ page }) => {
    await adminLogin(page, adminUsername);
    await expect(page.getByRole('heading', { name: 'Background jobs' })).toBeVisible();
    let launchRequests = 0;
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/api/admin/jobs/runs')) launchRequests += 1;
    });

    await page.getByLabel('Payload (JSON)').fill('{not json');
    await page.getByRole('button', { name: 'Launch job' }).click();
    await expect(page.getByTestId('launch-error')).toHaveText('Payload must be valid JSON');

    await page.getByLabel('Payload (JSON)').fill('[1, 2]');
    await page.getByRole('button', { name: 'Launch job' }).click();
    await expect(page.getByTestId('launch-error')).toHaveText('Payload must be a JSON object');
    expect(launchRequests).toBe(0);
  });

  test('admin sees the API error when launching fails', async ({ page }) => {
    await adminLogin(page, adminUsername);
    await expect(page.getByRole('heading', { name: 'Background jobs' })).toBeVisible();
    await page.route('**/api/admin/jobs/runs', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 502, json: { detail: 'Could not start the job, see the run list for details' } })
        : route.continue()
    );

    await page.getByRole('button', { name: 'Launch job' }).click();

    await expect(page.getByTestId('launch-error')).toHaveText('Could not start the job, see the run list for details');
  });

  test('an expired admin session sends the admin back to login', async ({ page }) => {
    await adminLogin(page, adminUsername);
    await expect(page.getByRole('heading', { name: 'Background jobs' })).toBeVisible();
    await page.route('**/api/admin/jobs/runs**', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Could not validate credentials' } })
    );

    await page.getByRole('button', { name: 'Refresh' }).click();

    await expect(page).toHaveURL(/.*admin\/login/);
  });
});
