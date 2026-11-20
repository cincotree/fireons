import { test, expect } from '@playwright/test';

test.describe('Invite-only sign up', () => {
  test('the join page hides the invite field when invites are not required', async ({ page }) => {
    await page.goto('/register');

    await expect(page.getByRole('link', { name: 'Continue with Google' })).toBeVisible();
    await expect(page.getByLabel(/Invite code/i)).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Continue with Google' })).not.toHaveAttribute('href', /invite_code/);
  });

  test('the join page asks for a code when required, prefills it from the link and passes it to the provider', async ({ page }) => {
    await page.route('**/api/auth/registration', (route) => route.fulfill({ json: { invite_required: true } }));

    await page.goto('/register?invite=link-code-123');

    const invite = page.getByLabel(/Invite code/i);
    await expect(invite).toHaveValue('link-code-123');
    await expect(page.getByRole('link', { name: 'Continue with Google' })).toHaveAttribute(
      'href',
      /invite_code=link-code-123/
    );

    await invite.fill('  typed-code  ');
    await expect(page.getByRole('link', { name: 'Continue with Reddit' })).toHaveAttribute(
      'href',
      /invite_code=typed-code$/
    );
  });

  test('a rejected invite returns to login with an explanation', async ({ page }) => {
    await page.goto('/login?error=invite_required');

    await expect(page.getByText(/need an invite code/i)).toBeVisible();
  });
});
