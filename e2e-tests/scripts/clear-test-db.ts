import pg from 'pg';

const { Client } = pg;

async function clearTestDatabase() {
  const databaseUrl =
    process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/fireons_e2e';
  const client = new Client({ connectionString: databaseUrl.replace('+psycopg', '') });

  try {
    await client.connect();
    console.log('Connected to test database');

    await client.query('DROP SCHEMA public CASCADE');
    await client.query('CREATE SCHEMA public');

    console.log('✓ Database schema reset successfully');
  } catch (error) {
    console.error('Error resetting database schema:', error);
    process.exit(1);
  } finally {
    await client.end();
  }
}

clearTestDatabase();
