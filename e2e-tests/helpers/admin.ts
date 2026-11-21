import { Page } from '@playwright/test';
import { execSync } from 'child_process';
import { randomUUID } from 'crypto';
import path from 'path';
import pg from 'pg';

export const ADMIN_PASSWORD = 'admin-password-123';

export function createAdmin(): string {
  const username = `e2eadmin${randomUUID().replace(/-/g, '').slice(0, 12)}`;
  execSync(`uv run python -m scripts.create_admin ${username}`, {
    cwd: path.join(__dirname, '..', '..', 'backend'),
    env: { ...process.env, TESTING: 'true', ADMIN_PASSWORD },
    stdio: 'pipe',
  });
  return username;
}

export async function adminLogin(page: Page, username: string, password = ADMIN_PASSWORD) {
  await page.goto('/admin/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Login' }).click();
}

export async function signInAsAdmin(page: Page, username: string) {
  await adminLogin(page, username);
  await page.waitForURL(/.*admin\/jobs/);
}

export async function seedExchangeRate(date: string, from: string, to: string, rate: string, source: string) {
  const databaseUrl =
    process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/fireons_e2e';
  const client = new pg.Client({ connectionString: databaseUrl.replace('+psycopg', '') });
  await client.connect();
  try {
    await client.query(
      `INSERT INTO exchange_rates (id, date, from_currency, to_currency, rate, source)
       VALUES (gen_random_uuid(), $1, $2, $3, $4, $5)
       ON CONFLICT (date, from_currency, to_currency) DO NOTHING`,
      [date, from, to, rate, source]
    );
  } finally {
    await client.end();
  }
}
