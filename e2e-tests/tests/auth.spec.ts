import { test, expect } from '@playwright/test';

test.describe('Authentication Feature - Critical User Journeys', () => {
  const timestamp = Date.now();
  const testUser = {
    email: `testuser${timestamp}@example.com`,
    username: `testuser${timestamp}`,
    password: 'Test123!@#',
    fullName: 'Test User',
    location: 'San Francisco, CA',
    currency: 'USD'
  };

  test('complete workflow: user registration with all fields', async ({ page }) => {
    await page.goto('/register');

    // Verify we're on the registration page
    await expect(page.locator('h2')).toContainText('Create your account');

    // Fill in all registration fields
    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.locator('input[name="confirmPassword"]').fill(testUser.password);
    await page.getByLabel(/Full Name/i).fill(testUser.fullName);
    await page.getByLabel(/Location/i).fill(testUser.location);
    await page.getByLabel(/Primary Currency/i).selectOption(testUser.currency);

    // Submit the form
    await page.getByRole('button', { name: /Create account/i }).click();

    // Should redirect to networth page after successful registration
    await expect(page).toHaveURL(/.*networth/, { timeout: 5000 });

    // Verify user name is displayed in navigation
    await expect(page.getByText(testUser.fullName)).toBeVisible();
    await expect(page.getByRole('button', { name: /Logout/i })).toBeVisible();
  });

  test('complete workflow: user login', async ({ page }) => {
    // First register a user
    await page.goto('/register');
    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.locator('input[name="confirmPassword"]').fill(testUser.password);
    await page.getByRole('button', { name: /Create account/i }).click();
    await page.waitForURL(/.*networth/, { timeout: 5000 });

    // Logout
    await page.getByRole('button', { name: /Logout/i }).click();
    await page.waitForURL(/.*login/, { timeout: 3000 });

    // Now test login
    await page.getByLabel(/Username/i).fill(testUser.username);
    await page.getByLabel(/Password/i).fill(testUser.password);
    await page.getByRole('button', { name: /Sign in/i }).click();

    // Should redirect to networth page after successful login
    await expect(page).toHaveURL(/.*networth/, { timeout: 5000 });

    // Verify user is logged in
    await expect(page.getByText(testUser.username)).toBeVisible();
    await expect(page.getByRole('button', { name: /Logout/i })).toBeVisible();
  });

  test('logout redirects to login page', async ({ page, context }) => {
    // Register and login a user
    await page.goto('/register');
    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.locator('input[name="confirmPassword"]').fill(testUser.password);
    await page.getByRole('button', { name: /Create account/i }).click();
    await page.waitForURL(/.*networth/, { timeout: 5000 });

    // Click logout
    await page.getByRole('button', { name: /Logout/i }).click();

    // Should redirect to login page
    await expect(page).toHaveURL(/.*login/, { timeout: 3000 });

    // Verify logout button is no longer visible
    await expect(page.getByRole('button', { name: /Logout/i })).not.toBeVisible();

    // Verify token is removed from localStorage
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeNull();
  });

  test('protected route redirects unauthenticated user to login', async ({ page }) => {
    // Clear any existing auth tokens
    await page.goto('/login');
    await page.evaluate(() => localStorage.clear());

    // Try to access protected route
    await page.goto('/networth');

    // Should redirect to login page
    await expect(page).toHaveURL(/.*login/, { timeout: 5000 });
  });

  test('authenticated user accessing root redirects to networth', async ({ page }) => {
    // Register a user
    await page.goto('/register');
    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.locator('input[name="confirmPassword"]').fill(testUser.password);
    await page.getByRole('button', { name: /Create account/i }).click();
    await page.waitForURL(/.*networth/, { timeout: 5000 });

    // Go to root URL
    await page.goto('/');

    // Should redirect to networth
    await expect(page).toHaveURL(/.*networth/, { timeout: 3000 });
  });

  test('registration validation: password mismatch', async ({ page }) => {
    await page.goto('/register');

    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill(testUser.password);
    await page.locator('input[name="confirmPassword"]').fill('DifferentPassword123!');
    await page.getByRole('button', { name: /Create account/i }).click();

    // Should show error message
    await expect(page.getByText(/Passwords do not match/i)).toBeVisible();
  });

  test('registration validation: short password', async ({ page }) => {
    await page.goto('/register');

    await page.getByLabel(/Email/i).fill(testUser.email);
    await page.getByLabel(/^Username/i).fill(testUser.username);
    await page.locator('input[name="password"]').fill('12345');
    await page.locator('input[name="confirmPassword"]').fill('12345');
    await page.getByRole('button', { name: /Create account/i }).click();

    // Should show error message
    await expect(page.getByText(/Password must be at least 6 characters/i)).toBeVisible();
  });

  test('login validation: incorrect credentials', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel(/Username/i).fill('nonexistentuser');
    await page.getByLabel(/Password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /Sign in/i }).click();

    // Should show error message
    await expect(page.getByText(/Incorrect username or password/i)).toBeVisible({ timeout: 5000 });
  });

  test('navigation links work correctly', async ({ page }) => {
    // From login to register
    await page.goto('/login');
    await page.getByRole('link', { name: /create a new account/i }).click();
    await expect(page).toHaveURL(/.*register/);

    // From register to login
    await page.getByRole('link', { name: /Sign in/i }).click();
    await expect(page).toHaveURL(/.*login/);
  });

  test('registration with minimal required fields only', async ({ page }) => {
    const minimalUser = {
      email: `minimal${timestamp}@example.com`,
      username: `minimal${timestamp}`,
      password: 'Minimal123!'
    };

    await page.goto('/register');

    // Fill only required fields
    await page.getByLabel(/Email/i).fill(minimalUser.email);
    await page.getByLabel(/^Username/i).fill(minimalUser.username);
    await page.locator('input[name="password"]').fill(minimalUser.password);
    await page.locator('input[name="confirmPassword"]').fill(minimalUser.password);

    // Submit the form
    await page.getByRole('button', { name: /Create account/i }).click();

    // Should redirect to networth page
    await expect(page).toHaveURL(/.*networth/, { timeout: 5000 });

    // Verify username is displayed (since no full name provided)
    await expect(page.getByText(minimalUser.username)).toBeVisible();
  });
});
