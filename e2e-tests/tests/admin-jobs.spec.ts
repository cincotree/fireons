import { test, expect, Page } from '@playwright/test';
import pg from 'pg';

const databaseUrl =
  process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/fireons_e2e';

async function makeAdmin(username: string) {
  const client = new pg.Client({ connectionString: databaseUrl.replace('+psycopg', '') });
  await client.connect();
  try {
    await client.query('UPDATE users SET is_admin = true WHERE username = $1', [username]);
  } finally {
    await client.end();
  }
}

async function register(page: Page, prefix: string) {
  const username = `${prefix}${Date.now()}`;
  await page.goto('/register');
  await page.getByLabel(/Email/i).fill(`${username}@example.com`);
  await page.getByLabel(/^Username/i).fill(username);
  await page.locator('input[name="password"]').fill('Test123!@#');
  await page.getByRole('button', { name: /Create account/i }).click();
  await page.waitForURL(/.*networth/, { timeout: 5000 });
  return username;
}

test.describe('Admin jobs', () => {
  test('regular users get no Jobs link and a denied page', async ({ page }) => {
    await register(page, 'plainjobs');

    await expect(page.getByRole('link', { name: 'Jobs' })).toHaveCount(0);
    await page.goto('/admin/jobs');

    await expect(page.getByText('Admin access required')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Launch job' })).toHaveCount(0);
  });

  test('anonymous visitors are sent to login', async ({ page }) => {
    await page.goto('/admin/jobs');

    await expect(page).toHaveURL(/.*login/);
  });

  test('admin launches a job and sees it finish in the run list', async ({ page }) => {
    const username = await register(page, 'rootjobs');
    await makeAdmin(username);
    await page.reload();

    await page.getByRole('link', { name: 'Jobs' }).click();
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
  });

  test('admin sees validation errors for a bad payload', async ({ page }) => {
    const username = await register(page, 'badpayload');
    await makeAdmin(username);
    await page.goto('/admin/jobs');

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
    const username = await register(page, 'failjobs');
    await makeAdmin(username);
    await page.goto('/admin/jobs');
    await page.route('**/api/admin/jobs/runs', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 502, json: { detail: 'Could not start the job, see the run list for details' } })
        : route.continue()
    );

    await page.getByRole('button', { name: 'Launch job' }).click();

    await expect(page.getByTestId('launch-error')).toHaveText('Could not start the job, see the run list for details');
  });
});
