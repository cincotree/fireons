import { createHmac } from 'crypto';
import { readFileSync } from 'fs';
import path from 'path';
import pg from 'pg';
import type { Page } from '@playwright/test';

const { Client } = pg;

export const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8020';

function secretKey(): string {
  if (process.env.SECRET_KEY) return process.env.SECRET_KEY;
  const file = readFileSync(path.join(__dirname, '../../../backend/.env.test'), 'utf-8');
  const line = file.split('\n').find((entry) => entry.startsWith('SECRET_KEY='));
  if (!line) throw new Error('SECRET_KEY is not set for the e2e backend');
  return line.slice('SECRET_KEY='.length).trim();
}

function base64Url(value: Buffer | string): string {
  return Buffer.from(value).toString('base64url');
}

function signToken(claims: Record<string, unknown>): string {
  const header = base64Url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = base64Url(JSON.stringify({ ...claims, exp: Math.floor(Date.now() / 1000) + 1800 }));
  const signature = createHmac('sha256', secretKey()).update(`${header}.${payload}`).digest();
  return `${header}.${payload}.${base64Url(signature)}`;
}

export async function createUserToken(prefix = 'member'): Promise<string> {
  const suffix = `${Date.now()}${Math.floor(Math.random() * 100000)}`;
  const username = `${prefix}${suffix}`;
  const email = `${username}@example.com`;
  const databaseUrl = process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/fireons_e2e';
  const client = new Client({ connectionString: databaseUrl.replace('+psycopg', '') });
  await client.connect();
  try {
    const result = await client.query(
      `INSERT INTO users (id, email, username, primary_currency) VALUES (gen_random_uuid(), $1, $2, 'USD') RETURNING id`,
      [email, username]
    );
    return signToken({ sub: result.rows[0].id, username, email });
  } finally {
    await client.end();
  }
}

export async function signIn(page: Page, prefix = 'member'): Promise<string> {
  const token = await createUserToken(prefix);
  await page.addInitScript((value) => {
    if (!window.sessionStorage.getItem('e2e-seeded-token')) {
      window.sessionStorage.setItem('e2e-seeded-token', '1');
      window.localStorage.setItem('token', value);
    }
  }, token);
  return token;
}
