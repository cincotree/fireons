import { test, expect, type Page } from '@playwright/test';
import pg from 'pg';

const { Client } = pg;

const FILLER_COUNT = 28;
const TOTAL = 32;

interface SeedRegistration {
  name: string;
  number: string;
  city: string;
  state: string;
  status?: string;
  validUntil?: string | null;
  email?: string | null;
  phone?: string | null;
}

const NAMED: SeedRegistration[] = [
  { name: 'Rohan Mehta', number: 'INA900000001', city: 'Mumbai', state: 'Maharashtra', email: 'new-mehta@example.com', phone: '910000000001' },
  { name: 'Priya Shah', number: 'INA900000002', city: 'Ahmedabad', state: 'Gujarat', email: 'priya@example.com' },
  { name: 'Old Timer', number: 'INA900000003', city: 'Pune', state: 'Maharashtra', status: 'expired', validUntil: '2024-01-01' },
];

async function connect() {
  const client = new Client({
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432'),
    database: process.env.POSTGRES_DB || 'fireons_test',
    user: process.env.POSTGRES_USER || 'postgres',
    password: process.env.POSTGRES_PASSWORD || 'postgres',
  });
  await client.connect();
  return client;
}

async function insertRegistration(client: pg.Client, sourceId: string, runId: string, row: SeedRegistration) {
  const professional = await client.query(
    `INSERT INTO financial_professionals (id, display_name, name_normalized, kind)
     VALUES (gen_random_uuid(), $1, $2, 'individual') RETURNING id`,
    [row.name, row.name.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()]
  );
  const registration = await client.query(
    `INSERT INTO professional_registrations
       (id, professional_id, source_id, profession_type, registration_number, status, valid_from, valid_until,
        validity_raw, city, state, pincode, address_raw, email, phone, contact_person, attributes,
        source_url, content_hash, missing_runs)
     VALUES (gen_random_uuid(), $1, $2, 'investment_adviser', $3, $4, '2022-01-01', $5, 'Jan 01, 2022 - Perpetual', $6, $7,
        '400001', '1 Test Road', $8, $9, $10, '{}'::jsonb, 'https://example.test/list', $11, 0)
     RETURNING id`,
    [
      professional.rows[0].id,
      sourceId,
      row.number,
      row.status ?? 'active',
      row.validUntil ?? null,
      row.city,
      row.state,
      row.email ?? null,
      row.phone ?? null,
      row.name,
      row.number.padEnd(64, '0'),
    ]
  );
  return registration.rows[0].id as string;
}

test.describe('Professionals directory - public listing, filters and change history', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(async () => {
    const client = await connect();
    try {
      await client.query(`DELETE FROM professional_registrations`);
      await client.query(`DELETE FROM financial_professionals`);
      await client.query(`DELETE FROM scrape_runs`);
      await client.query(`DELETE FROM data_sources`);

      const source = await client.query(
        `INSERT INTO data_sources (id, key, name, regulator, default_profession_type, base_url, is_enabled)
         VALUES (gen_random_uuid(), 'sebi_ria', 'SEBI Registered Investment Advisers', 'SEBI', 'investment_adviser',
                 'https://example.test/list', true) RETURNING id`
      );
      const sourceId = source.rows[0].id as string;
      const run = await client.query(
        `INSERT INTO scrape_runs (id, source_id, trigger, status, started_at, finished_at, records_seen, expected_total,
          pages_fetched, inserted, updated, unchanged, parse_errors, marked_delisted)
         VALUES (gen_random_uuid(), $1, 'scheduled', 'succeeded', now() - interval '2 minutes', now() - interval '1 minute',
                 $2, $2, 2, 0, 0, 0, 0, 0) RETURNING id`,
        [sourceId, NAMED.length + FILLER_COUNT]
      );
      const runId = run.rows[0].id as string;
      const nextRun = await client.query(
        `INSERT INTO scrape_runs (id, source_id, trigger, status, started_at, finished_at,
          pages_fetched, records_seen, inserted, updated, unchanged, parse_errors, marked_delisted)
         VALUES (gen_random_uuid(), $1, 'scheduled', 'succeeded', now(), now(), 0, 0, 0, 0, 0, 0, 0) RETURNING id`,
        [sourceId]
      );

      for (const row of NAMED) {
        const registrationId = await insertRegistration(client, sourceId, runId, row);
        if (row.name === 'Rohan Mehta') {
          await client.query(
            `INSERT INTO registration_versions (id, registration_id, run_id, scraped_at, content_hash, snapshot)
             VALUES (gen_random_uuid(), $1, $2, now() - interval '7 days', $4, $5::jsonb),
                    (gen_random_uuid(), $1, $3, now(), $6, $7::jsonb)`,
            [
              registrationId,
              runId,
              nextRun.rows[0].id,
              'a'.repeat(64),
              JSON.stringify({ email: 'old-mehta@example.com', phone: '910000000001', validity_raw: 'Jan 01, 2022 - Perpetual' }),
              'b'.repeat(64),
              JSON.stringify({ email: 'new-mehta@example.com', phone: '910000000001', validity_raw: 'Jan 01, 2022 - Perpetual' }),
            ]
          );
        }
      }
      const otherSource = await client.query(
        `INSERT INTO data_sources (id, key, name, regulator, default_profession_type, base_url, is_enabled)
         VALUES (gen_random_uuid(), 'other_register', 'Other Register of Advisers', 'OTHER', 'investment_adviser',
                 'https://example.test/other', true) RETURNING id`
      );
      await insertRegistration(client, otherSource.rows[0].id as string, runId, {
        name: 'Zulu Otherperson',
        number: 'INA900000099',
        city: 'Delhi',
        state: 'Delhi',
      });
      for (let index = 1; index <= FILLER_COUNT; index++) {
        await insertRegistration(client, sourceId, runId, {
          name: `Zeta Filler ${String(index).padStart(2, '0')}`,
          number: `INA9100000${String(index).padStart(2, '0')}`,
          city: 'Chennai',
          state: 'Tamil Nadu',
        });
      }
    } finally {
      await client.end();
    }
  });

  const searchBox = (page: Page) => page.getByRole('searchbox');
  const filter = (page: Page, label: string) => page.getByRole('combobox', { name: label, exact: true });
  const filtersButton = (page: Page) => page.getByRole('button', { name: /^Filters/ });
  const openFilters = async (page: Page) => {
    await filtersButton(page).click();
    await expect(filter(page, 'State')).toBeVisible();
  };
  const historyButton = (page: Page, name: string) =>
    page.getByRole('button', { name: `View history for ${name}` });

  test('anyone can browse the directory without logging in', async ({ page }) => {
    await page.goto('/professionals');

    await expect(page).toHaveTitle('Find a registered financial professional | Fireons');
    await expect(page.getByRole('heading', { level: 1, name: 'Find a registered financial professional' })).toBeVisible();
    await expect(page.getByText(`Showing 1–25 of ${TOTAL}`)).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(page.getByRole('link', { name: 'new-mehta@example.com' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'SEBI' }).first()).toHaveAttribute('href', 'https://example.test/list');
    await expect(page.getByRole('link', { name: 'Find professionals' })).toBeVisible();
  });

  test('the table shows only name, registration, location, contact and source', async ({ page }) => {
    await page.goto('/professionals');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();

    await expect(page.getByRole('columnheader')).toHaveText([
      'Name',
      'Registration no.',
      'Location',
      'Contact',
      'Source',
    ]);
    await expect(page.getByText('on record')).toHaveCount(0);
    await expect(page.getByText('Last updated')).toHaveCount(0);
  });

  test('there is a single search box and the filters stay hidden until the Filters button is clicked', async ({ page }) => {
    await page.goto('/professionals');

    await expect(page.getByRole('searchbox')).toHaveCount(1);
    await expect(page.getByRole('searchbox')).toHaveAttribute(
      'placeholder',
      'Search by name, registration number, city, state, or source...'
    );
    await expect(page.getByRole('combobox')).toHaveCount(0);

    await openFilters(page);

    await expect(page.getByRole('combobox')).toHaveCount(3);
    await expect(filter(page, 'Source')).toBeVisible();
    await expect(filter(page, 'State')).toBeVisible();
    await expect(filter(page, 'City')).toBeVisible();
    await expect(page.getByRole('combobox', { name: 'Status' })).toHaveCount(0);
    await expect(filter(page, 'Source').locator('option').first()).toHaveText('All sources');
    await expect(filter(page, 'State').locator('option').first()).toHaveText('All states');
    await expect(filter(page, 'City').locator('option').first()).toHaveText('All cities');
  });

  test('the Filters button toggles the panel and counts active filters', async ({ page }) => {
    await page.goto('/professionals');
    await expect(filtersButton(page)).toHaveText('Filters');

    await openFilters(page);
    await filter(page, 'State').selectOption('Gujarat');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(filtersButton(page)).toHaveText('Filters (1)');

    await filtersButton(page).click();
    await expect(page.getByRole('combobox')).toHaveCount(0);
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);
    await expect(filtersButton(page)).toHaveText('Filters (1)');

    await filtersButton(page).click();
    await filter(page, 'State').selectOption('');
    await expect(filtersButton(page)).toHaveText('Filters');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
  });

  test('search narrows results and an unmatched search shows the empty state', async ({ page }) => {
    await page.goto('/professionals');

    await searchBox(page).fill('mehta');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(historyButton(page, 'Priya Shah')).toHaveCount(0);

    await searchBox(page).fill('zzzz-no-such-adviser');
    await expect(page.getByText('No professionals match your filters.')).toBeVisible();
  });

  test('search by registration number finds the exact adviser', async ({ page }) => {
    await page.goto('/professionals');

    await searchBox(page).fill('INA900000002');

    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);
  });

  test('search is fuzzy: a misspelt name still finds the adviser', async ({ page }) => {
    await page.goto('/professionals');

    await searchBox(page).fill('mehata');

    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(historyButton(page, 'Priya Shah')).toHaveCount(0);
  });

  test('search matches a location, even misspelt', async ({ page }) => {
    await page.goto('/professionals');

    await searchBox(page).fill('ahmadabad');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);

    await searchBox(page).fill('gujarat');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
  });

  test('search combines a name word with a location word', async ({ page }) => {
    await page.goto('/professionals');

    await searchBox(page).fill('rohan mumbai');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();

    await searchBox(page).fill('rohan pune');
    await expect(page.getByText('No professionals match your filters.')).toBeVisible();
  });

  test('search matches the source name', async ({ page }) => {
    await page.goto('/professionals');

    await searchBox(page).fill('other register');

    await expect(historyButton(page, 'Zulu Otherperson')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);
  });

  test('source filter shows only that source', async ({ page }) => {
    await page.goto('/professionals');

    await openFilters(page);
    await filter(page, 'Source').selectOption({ label: 'Other Register of Advisers' });

    await expect(historyButton(page, 'Zulu Otherperson')).toBeVisible();
    await expect(page.getByText('Showing 1–1 of 1')).toBeVisible();
  });

  test('state filter narrows results and scopes the city options', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);

    await filter(page, 'State').selectOption('Maharashtra');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(historyButton(page, 'Priya Shah')).toHaveCount(0);

    const cityOptions = filter(page, 'City').locator('option');
    await expect(cityOptions).toHaveText(['All cities', 'Mumbai', 'Pune']);

    await filter(page, 'City').selectOption('Pune');
    await expect(historyButton(page, 'Old Timer')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);
  });

  test('changing the state clears a city that no longer applies', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);
    await filter(page, 'State').selectOption('Maharashtra');
    await filter(page, 'City').selectOption('Pune');
    await expect(page.getByText('Showing 1–1 of 1')).toBeVisible();

    await filter(page, 'State').selectOption('Gujarat');

    await expect(filter(page, 'City')).toHaveValue('');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
  });

  test('search and filters work together', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);

    await filter(page, 'State').selectOption('Maharashtra');
    await searchBox(page).fill('timer');
    await expect(historyButton(page, 'Old Timer')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);

    await searchBox(page).fill('mehta');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(historyButton(page, 'Old Timer')).toHaveCount(0);

    await filter(page, 'State').selectOption('Gujarat');
    await expect(page.getByText('No professionals match your filters.')).toBeVisible();
  });

  test('pagination moves between pages of results', async ({ page }) => {
    await page.goto('/professionals');

    await expect(page.getByText(`Showing 1–25 of ${TOTAL}`)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Previous' })).toBeDisabled();

    await page.getByRole('button', { name: 'Next' }).click();

    await expect(page.getByText(`Showing 26–${TOTAL} of ${TOTAL}`)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  test('clicking a name opens the change history with before and after values', async ({ page }) => {
    await page.goto('/professionals');

    await page.getByRole('button', { name: 'View history for Rohan Mehta' }).click();

    await expect(page.getByRole('heading', { name: 'Rohan Mehta' })).toBeVisible();
    const history = page.getByRole('list', { name: 'Change history' });
    await expect(history.getByText('First recorded')).toBeVisible();
    await expect(history.getByText('Changed', { exact: true })).toBeVisible();
    await expect(history.getByText('old-mehta@example.com')).toBeVisible();
    await expect(history.getByText('new-mehta@example.com')).toBeVisible();

    await page.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByRole('heading', { name: 'Rohan Mehta' })).toHaveCount(0);
  });

  test('a listing failure shows an error and recovers on retry', async ({ page }) => {
    await page.route(/\/api\/registrations\?/, (route) => route.fulfill({ status: 500, body: 'boom' }));
    await page.goto('/professionals');

    await expect(page.getByRole('alert').filter({ hasText: 'Could not load professionals' })).toBeVisible();

    await page.unroute(/\/api\/registrations\?/);
    await page.getByRole('button', { name: 'Retry' }).click();

    await expect(page.getByText('Could not load professionals')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'View history for Rohan Mehta' })).toBeVisible();
  });

  test('being rate limited tells the user to wait', async ({ page }) => {
    await page.route(/\/api\/registrations\?/, (route) =>
      route.fulfill({ status: 429, headers: { 'Retry-After': '30' }, body: '{}' })
    );
    await page.goto('/professionals');

    await expect(page.getByRole('alert').filter({ hasText: 'Too many requests' })).toBeVisible();
  });

  test('a history failure shows an error inside the dialog', async ({ page }) => {
    await page.route(/\/history$/, (route) => route.fulfill({ status: 500, body: 'boom' }));
    await page.goto('/professionals');

    await page.getByRole('button', { name: 'View history for Rohan Mehta' }).click();

    await expect(page.getByRole('alert').filter({ hasText: 'Could not load history' })).toBeVisible();
  });
});
