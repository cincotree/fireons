import { execSync } from 'child_process';
import path from 'path';

export default async function globalTeardown() {
  console.log('Clearing all database tables...');

  try {
    const scriptPath = path.join(__dirname, 'scripts', 'clear-test-db.ts');
    execSync(`npx tsx ${scriptPath}`, {
      cwd: __dirname,
      stdio: 'inherit',
      env: process.env
    });
  } catch (error) {
    console.error('Error during cleanup:', error);
    process.exit(1);
  }
}
