import { test, expect } from '@playwright/test';

test.describe('Invite-only registration', () => {
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
