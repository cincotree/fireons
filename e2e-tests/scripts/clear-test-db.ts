import pg from 'pg';

const { Client } = pg;

async function clearTestDatabase() {
  const client = new Client({
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432'),
    database: process.env.POSTGRES_DB || 'fireons_test',
    user: process.env.POSTGRES_USER || 'postgres',
    password: process.env.POSTGRES_PASSWORD || 'postgres',
  });

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
