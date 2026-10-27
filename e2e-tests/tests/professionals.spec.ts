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
  const databaseUrl =
    process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/fireons_e2e';
  const client = new Client({ connectionString: databaseUrl.replace('+psycopg', '') });
  await client.connect();
  return client;
}

async function insertNri(
  client: pg.Client,
  registrationId: string,
  domain: string,
  signals: { confidence: string; text: string; reviewStatus?: string; location?: string }[]
) {
  const professional = await client.query(
    `SELECT professional_id FROM professional_registrations WHERE id = $1`,
    [registrationId]
  );
  const professionalId = professional.rows[0].professional_id as string;
  const website = await client.query(
    `INSERT INTO professional_websites
       (id, professional_id, domain, url, derived_from, check_status, pages_checked, last_checked_at)
     VALUES (gen_random_uuid(), $1, $2, $3, 'email_domain', 'checked', 2, now()) RETURNING id`,
    [professionalId, domain, `https://${domain}/`]
  );
  for (const [index, signal] of signals.entries()) {
    await client.query(
      `INSERT INTO nri_signals
         (id, website_id, professional_id, page_url, signal_type, matched_text, text_hash, location, confidence,
          review_status)
       VALUES (gen_random_uuid(), $1, $2, $3, 'nri_mention', $4, $5, $6, $7, $8)`,
      [
        website.rows[0].id,
        professionalId,
        `https://${domain}/nri-${index}`,
        signal.text,
        `${domain}-${index}`.padEnd(64, '0'),
        signal.location ?? 'heading',
        signal.confidence,
        signal.reviewStatus ?? 'pending',
      ]
    );
  }
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
          await insertNri(client, registrationId, 'mehta-wealth.example.com', [
            { confidence: 'high', text: 'Wealth advisory for NRIs and overseas Indians' },
            { confidence: 'low', text: 'We understand FEMA rules', location: 'body' },
          ]);
        }
        if (row.name === 'Priya Shah') {
          await insertNri(client, registrationId, 'shah-invest.example.com', [
            { confidence: 'medium', text: 'We also serve NRI clients', reviewStatus: 'confirmed', location: 'body' },
          ]);
        }
        if (row.name === 'Old Timer') {
          await insertNri(client, registrationId, 'oldtimer.example.com', [
            { confidence: 'high', text: 'Rejected NRI claim', reviewStatus: 'rejected' },
          ]);
        }
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
  const option = (page: Page, name: string) => page.getByRole('option', { name, exact: true });
  const choose = async (page: Page, label: 'State' | 'City', ...values: string[]) => {
    await filter(page, label).click();
    for (const value of values) await option(page, value).click();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('listbox')).toHaveCount(0);
  };
  const chip = (page: Page, value: string, kind: string) =>
    page.getByRole('button', { name: `Remove ${value} ${kind} filter` });
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

  test('the table shows name, registration, location, contact, NRI signals and source', async ({ page }) => {
    await page.goto('/professionals');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();

    await expect(page.getByRole('columnheader')).toHaveText([
      'Name',
      'Registration no.',
      'Location',
      'Contact',
      'NRI',
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

    await expect(page.getByRole('combobox')).toHaveCount(4);
    await expect(filter(page, 'Source')).toBeVisible();
    await expect(filter(page, 'NRI signals')).toBeVisible();
    await expect(filter(page, 'State')).toBeVisible();
    await expect(filter(page, 'City')).toBeVisible();
    await expect(page.getByRole('combobox', { name: 'Status' })).toHaveCount(0);
    await expect(filter(page, 'Source').locator('option').first()).toHaveText('All sources');
    await expect(filter(page, 'State')).toHaveText('All states');
    await expect(filter(page, 'City')).toHaveText('All cities');
  });

  test('the Filters button toggles the panel and counts active filters', async ({ page }) => {
    await page.goto('/professionals');
    await expect(filtersButton(page)).toHaveText('Filters');

    await openFilters(page);
    await choose(page, 'State', 'Gujarat');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(filtersButton(page)).toHaveText('Filters (1)');

    await filtersButton(page).click();
    await expect(page.getByRole('combobox')).toHaveCount(0);
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);
    await expect(filtersButton(page)).toHaveText('Filters (1)');

    await filtersButton(page).click();
    await filter(page, 'State').click();
    await option(page, 'Gujarat').click();
    await page.keyboard.press('Escape');
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

  test('state dropdown is searchable', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);
    await filter(page, 'State').click();
    await expect(option(page, 'Gujarat')).toBeVisible();
    await expect(option(page, 'Maharashtra')).toBeVisible();

    await page.getByRole('textbox', { name: 'Search states' }).fill('guj');

    await expect(option(page, 'Gujarat')).toBeVisible();
    await expect(option(page, 'Maharashtra')).toHaveCount(0);

    await page.getByRole('textbox', { name: 'Search states' }).fill('zzz');
    await expect(page.getByText('No matching states.')).toBeVisible();

    await page.getByRole('textbox', { name: 'Search states' }).fill('guj');
    await option(page, 'Gujarat').click();
    await page.keyboard.press('Escape');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);
  });

  test('several states can be selected at once', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);

    await choose(page, 'State', 'Maharashtra', 'Gujarat');

    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(historyButton(page, 'Old Timer')).toBeVisible();
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(historyButton(page, 'Zeta Filler 01')).toHaveCount(0);
    await expect(filter(page, 'State')).toHaveText('Maharashtra +1');
    await expect(chip(page, 'Maharashtra', 'state')).toBeVisible();
    await expect(chip(page, 'Gujarat', 'state')).toBeVisible();
    await expect(filtersButton(page)).toHaveText('Filters (2)');
  });

  test('city options follow the selected states and several cities can be chosen', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);
    await choose(page, 'State', 'Maharashtra');

    await filter(page, 'City').click();
    await expect(option(page, 'Mumbai')).toBeVisible();
    await expect(option(page, 'Pune')).toBeVisible();
    await expect(option(page, 'Ahmedabad')).toHaveCount(0);
    await page.keyboard.press('Escape');

    await choose(page, 'State', 'Gujarat');
    await filter(page, 'City').click();
    await expect(option(page, 'Ahmedabad')).toBeVisible();
    await option(page, 'Mumbai').click();
    await option(page, 'Pune').click();
    await page.keyboard.press('Escape');

    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(historyButton(page, 'Old Timer')).toBeVisible();
    await expect(historyButton(page, 'Priya Shah')).toHaveCount(0);
    await expect(filter(page, 'City')).toHaveText('Mumbai +1');
  });

  test('removing a state also drops cities that no longer apply', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);
    await choose(page, 'State', 'Maharashtra', 'Gujarat');
    await choose(page, 'City', 'Pune');
    await expect(chip(page, 'Pune', 'city')).toBeVisible();
    await expect(page.getByText('Showing 1–1 of 1')).toBeVisible();

    await chip(page, 'Maharashtra', 'state').click();

    await expect(chip(page, 'Pune', 'city')).toHaveCount(0);
    await expect(filter(page, 'City')).toHaveText('All cities');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();
    await expect(page.getByText('Showing 1–1 of 1')).toBeVisible();
  });

  test('a selected value can be removed from the dropdown, the chip, or all at once', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);
    await choose(page, 'State', 'Maharashtra', 'Gujarat');

    await chip(page, 'Gujarat', 'state').click();
    await expect(chip(page, 'Gujarat', 'state')).toHaveCount(0);
    await expect(historyButton(page, 'Priya Shah')).toHaveCount(0);

    await filter(page, 'State').click();
    await expect(page.getByText('1 selected')).toBeVisible();
    await option(page, 'Gujarat').click();
    await expect(page.getByText('2 selected')).toBeVisible();
    await option(page, 'Gujarat').click();
    await expect(page.getByText('1 selected')).toBeVisible();
    await page.getByRole('button', { name: 'Clear selection' }).click();
    await page.keyboard.press('Escape');

    await expect(filter(page, 'State')).toHaveText('All states');
    await expect(filtersButton(page)).toHaveText('Filters');
    await expect(historyButton(page, 'Zeta Filler 01')).toBeVisible();
  });

  test('the dropdown works from the keyboard', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);

    await filter(page, 'State').focus();
    await page.keyboard.press('ArrowDown');
    await expect(page.getByRole('listbox')).toBeVisible();
    await page.keyboard.type('guj');
    await page.keyboard.press('Enter');

    await expect(option(page, 'Gujarat')).toHaveAttribute('aria-selected', 'true');
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.getByRole('listbox')).toHaveCount(0);
    await expect(filter(page, 'State')).toBeFocused();
    await expect(filter(page, 'State')).toHaveText('Gujarat');
  });

  test('clicking outside closes the dropdown and keeps the selection', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);
    await filter(page, 'State').click();
    await option(page, 'Gujarat').click();

    await page.getByRole('heading', { level: 1 }).click();

    await expect(page.getByRole('listbox')).toHaveCount(0);
    await expect(filter(page, 'State')).toHaveText('Gujarat');
  });

  test('search and filters work together', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);

    await choose(page, 'State', 'Maharashtra');
    await searchBox(page).fill('timer');
    await expect(historyButton(page, 'Old Timer')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toHaveCount(0);

    await searchBox(page).fill('mehta');
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();
    await expect(historyButton(page, 'Old Timer')).toHaveCount(0);

    await filter(page, 'State').click();
    await option(page, 'Maharashtra').click();
    await option(page, 'Gujarat').click();
    await page.keyboard.press('Escape');
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

  const nriBadge = (page: Page, name: string) =>
    page.getByRole('button', { name: new RegExp(`^NRI signals for ${name}`) });

  test('listings show an NRI badge with confidence and count only where signals exist', async ({ page }) => {
    await page.goto('/professionals');

    await expect(nriBadge(page, 'Rohan Mehta')).toHaveText(/NRI High\s*\(2\)/);
    await expect(nriBadge(page, 'Priya Shah')).toHaveText(/NRI Medium\s*\(1\)/);
    await expect(nriBadge(page, 'Old Timer')).toHaveCount(0);
    await expect(nriBadge(page, 'Zulu Otherperson')).toHaveCount(0);
  });

  test('the NRI filter narrows to a minimum confidence and shows a removable chip', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);

    await filter(page, 'NRI signals').selectOption('high');
    await expect(page.getByText('Showing 1–1 of 1')).toBeVisible();
    await expect(historyButton(page, 'Rohan Mehta')).toBeVisible();

    await filter(page, 'NRI signals').selectOption('medium');
    await expect(page.getByText('Showing 1–2 of 2')).toBeVisible();
    await expect(historyButton(page, 'Priya Shah')).toBeVisible();

    await page.getByRole('button', { name: 'Remove NRI: medium or higher NRI filter' }).click();
    await expect(page.getByText(`Showing 1–25 of ${TOTAL}`)).toBeVisible();
  });

  test('the NRI filter combines with search and rejected signals never match', async ({ page }) => {
    await page.goto('/professionals');
    await openFilters(page);
    await filter(page, 'NRI signals').selectOption('low');

    await searchBox(page).fill('Old Timer');

    await expect(page.getByText('No professionals match your filters.')).toBeVisible();
  });

  test('opening the NRI badge shows the matched text, page, confidence and review state', async ({ page }) => {
    await page.goto('/professionals');

    await nriBadge(page, 'Rohan Mehta').click();

    const section = page.getByRole('region', { name: 'NRI signals' });
    await expect(section.getByText('Wealth advisory for NRIs and overseas Indians')).toBeVisible();
    await expect(section.getByText('We understand FEMA rules')).toBeVisible();
    await expect(section.getByText('High confidence')).toBeVisible();
    await expect(section.getByText('Not yet reviewed').first()).toBeVisible();
    await expect(section.getByRole('link', { name: 'mehta-wealth.example.com', exact: true })).toHaveAttribute(
      'href',
      'https://mehta-wealth.example.com/'
    );
    await expect(section.getByRole('link', { name: /mehta-wealth.example.com\/nri-0/ })).toBeVisible();
  });

  test('a reviewed signal is labelled confirmed', async ({ page }) => {
    await page.goto('/professionals');

    await nriBadge(page, 'Priya Shah').click();

    await expect(page.getByRole('region', { name: 'NRI signals' }).getByText('Reviewed: confirmed')).toBeVisible();
  });

  test('professionals without signals have no NRI section in the panel', async ({ page }) => {
    await page.goto('/professionals');
    await searchBox(page).fill('Zulu Otherperson');

    await historyButton(page, 'Zulu Otherperson').click();

    await expect(page.getByRole('heading', { name: 'Change history' })).toBeVisible();
    await expect(page.getByRole('region', { name: 'NRI signals' })).toHaveCount(0);
  });

  test('an NRI detail failure shows an error inside the panel', async ({ page }) => {
    await page.route(/\/nri$/, (route) => route.fulfill({ status: 500, body: 'boom' }));
    await page.goto('/professionals');

    await nriBadge(page, 'Rohan Mehta').click();

    await expect(page.getByRole('alert').filter({ hasText: 'Could not load NRI signals' })).toBeVisible();
  });
});
