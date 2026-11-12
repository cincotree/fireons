import { test, expect, Page } from '@playwright/test';
import { execSync } from 'child_process';
import { randomUUID } from 'crypto';
import path from 'path';

const ADMIN_PASSWORD = 'admin-password-123';
let adminUsername = '';

test.beforeAll(() => {
  adminUsername = `e2eadmin${randomUUID().replace(/-/g, '').slice(0, 12)}`;
  execSync(`uv run python -m scripts.create_admin ${adminUsername}`, {
    cwd: path.join(__dirname, '..', '..', 'backend'),
    env: { ...process.env, TESTING: 'true', ADMIN_PASSWORD },
    stdio: 'pipe',
  });
});

async function adminLogin(page: Page, username?: string, password = ADMIN_PASSWORD) {
  await page.goto('/admin/login');
  await page.getByLabel('Username').fill(username ?? adminUsername);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Login' }).click();
}

async function registerRegularUser(page: Page) {
  const username = `plainjobs${Date.now()}`;
  await page.goto('/register');
  await page.getByLabel(/Email/i).fill(`${username}@example.com`);
  await page.getByLabel(/^Username/i).fill(username);
  await page.locator('input[name="password"]').fill('Test123!@#');
  await page.getByRole('button', { name: /Create account/i }).click();
  await page.waitForURL(/.*networth/, { timeout: 5000 });
}

test.describe('Admin jobs', () => {
  test('anonymous visitors are sent to the admin login', async ({ page }) => {
    await page.goto('/admin/jobs');

    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('a signed in regular user has no admin access and sees no admin link', async ({ page }) => {
    await registerRegularUser(page);

    await expect(page.getByRole('link', { name: /jobs/i })).toHaveCount(0);
    await page.goto('/admin/jobs');

    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('wrong password shows an error and stays on the login page', async ({ page }) => {
    await adminLogin(page, undefined, 'not-the-password');

    await expect(page.getByTestId('admin-login-error')).toHaveText('Invalid username or password');
    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('regular user credentials do not work on the admin login', async ({ page }) => {
    await adminLogin(page, 'someregularuser', 'Test123!@#');

    await expect(page.getByTestId('admin-login-error')).toHaveText('Invalid username or password');
  });

  test('admin signs in, launches a job, sees it finish, and signs out', async ({ page }) => {
    await adminLogin(page);

    await expect(page.getByRole('heading', { name: 'Background jobs' })).toBeVisible();
    await expect(page.getByLabel('Job')).toHaveValue('exchange_rate_sync');

    await page.getByRole('button', { name: 'Launch job' }).click();

    const row = page.getByTestId('job-run').first();
    await expect(row).toContainText('exchange_rate_sync');
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

    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page).toHaveURL(/.*admin\/login/);
    await page.goto('/admin/jobs');
    await expect(page).toHaveURL(/.*admin\/login/);
  });

  test('admin sees validation errors for a bad payload', async ({ page }) => {
    await adminLogin(page);
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
    await adminLogin(page);
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
    await adminLogin(page);
    await expect(page.getByRole('heading', { name: 'Background jobs' })).toBeVisible();
    await page.route('**/api/admin/jobs/runs**', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Could not validate credentials' } })
    );

    await page.getByRole('button', { name: 'Refresh' }).click();

    await expect(page).toHaveURL(/.*admin\/login/);
  });
});
