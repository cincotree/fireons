import { test, expect, Page } from '@playwright/test';
import pg from 'pg';

const DATABASE_URL = (
  process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/fireons_e2e'
).replace('+psycopg', '');

async function promoteToSuperadmin(username: string) {
  const client = new pg.Client({ connectionString: DATABASE_URL });
  await client.connect();
  try {
    await client.query('UPDATE users SET is_superadmin = true WHERE username = $1', [username]);
  } finally {
    await client.end();
  }
}

async function registerUser(page: Page, prefix: string) {
  const stamp = Date.now();
  const user = {
    email: `${prefix}${stamp}@example.com`,
    username: `${prefix}${stamp}`,
    password: 'Test123!@#',
  };
  await page.goto('/register');
  await page.getByLabel(/Email/i).fill(user.email);
  await page.getByLabel(/^Username/i).fill(user.username);
  await page.locator('input[name="password"]').fill(user.password);
  await page.getByRole('button', { name: /Create account/i }).click();
  await expect(page).toHaveURL(/.*networth/, { timeout: 5000 });
  return user;
}

test.describe('Invite-only registration', () => {
  test('regular users have no Invites link and are told they are not authorized', async ({ page }) => {
    await registerUser(page, 'plain');

    await expect(page.getByRole('link', { name: 'Invites' })).toHaveCount(0);
    await page.goto('/admin/invites');
    await expect(page.getByText('Not authorized')).toBeVisible();
  });

  test('superadmin generates an invite, sees the code once, and revokes it', async ({ page }) => {
    const admin = await registerUser(page, 'admin');
    await promoteToSuperadmin(admin.username);
    await page.reload();

    await page.getByRole('link', { name: 'Invites' }).click();
    await expect(page).toHaveURL(/.*admin\/invites/);
    await expect(page.getByText('No invites yet')).toBeVisible();

    await page.getByLabel('Label').fill('for Asha');
    await page.getByLabel('Max uses').fill('2');
    await page.getByRole('button', { name: 'Generate invite' }).click();

    const code = await page.getByTestId('new-invite-code').innerText();
    expect(code.length).toBeGreaterThanOrEqual(12);
    await expect(page.getByTestId('new-invite-link')).toContainText(`/register?invite=${code}`);

    const row = page.getByTestId('invite-row').filter({ hasText: 'for Asha' });
    await expect(row).toContainText('active');
    await expect(row).toContainText('0/2');

    await page.reload();
    await expect(page.getByTestId('new-invite-code')).toHaveCount(0);
    await expect(page.getByText(code)).toHaveCount(0);

    await page.getByTestId('invite-row').filter({ hasText: 'for Asha' }).getByRole('button', { name: 'Revoke' }).click();
    await expect(page.getByTestId('invite-row').filter({ hasText: 'for Asha' })).toContainText('revoked');
    await expect(page.getByRole('button', { name: 'Revoke' })).toHaveCount(0);
  });

  test('out of range invite settings are not submitted', async ({ page }) => {
    const admin = await registerUser(page, 'adminbad');
    await promoteToSuperadmin(admin.username);
    await page.goto('/admin/invites');
    await expect(page.getByText('No invites yet')).toBeVisible();

    await page.getByLabel('Max uses').fill('5000');
    await page.getByRole('button', { name: 'Generate invite' }).click();

    await expect(page.getByTestId('new-invite-code')).toHaveCount(0);
    await expect(page.getByText('No invites yet')).toBeVisible();
  });

  test('a server rejection while generating an invite is shown to the admin', async ({ page }) => {
    const admin = await registerUser(page, 'adminfail');
    await promoteToSuperadmin(admin.username);
    await page.route('**/api/admin/invites', (route) =>
      route.request().method() === 'POST'
        ? route.fulfill({ status: 403, json: { detail: 'Superadmin access required' } })
        : route.continue()
    );
    await page.goto('/admin/invites');

    await page.getByRole('button', { name: 'Generate invite' }).click();

    await expect(page.getByText('Superadmin access required')).toBeVisible();
    await expect(page.getByTestId('new-invite-code')).toHaveCount(0);
  });

  test('register page hides the invite field when invites are not required', async ({ page }) => {
    await page.goto('/register');

    await expect(page.getByLabel(/Invite code/i)).toHaveCount(0);
  });

  test('register page asks for a code when required, prefills it from the link, and shows rejection', async ({ page }) => {
    await page.route('**/api/auth/registration', (route) =>
      route.fulfill({ json: { invite_required: true } })
    );
    let submitted: Record<string, unknown> | null = null;
    await page.route('**/api/auth/register', (route) => {
      submitted = route.request().postDataJSON();
      return route.fulfill({ status: 400, json: { detail: 'Invalid or expired invite code' } });
    });

    await page.goto('/register?invite=link-code-123');

    const invite = page.getByLabel(/Invite code/i);
    await expect(invite).toHaveValue('link-code-123');

    await invite.fill('  typed-code  ');
    await page.getByLabel(/Email/i).fill('nobody@example.com');
    await page.getByLabel(/^Username/i).fill('nobody_user');
    await page.locator('input[name="password"]').fill('Test123!@#');
    await page.getByRole('button', { name: /Create account/i }).click();

    await expect(page.getByText('Invalid or expired invite code')).toBeVisible();
    expect(submitted).toMatchObject({ invite_code: 'typed-code', username: 'nobody_user' });
    await expect(page).toHaveURL(/.*register/);
  });
});
