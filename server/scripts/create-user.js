// Usage: npm run create-user -- "Full Name" email@company.com password
import bcrypt from 'bcryptjs';
import { pool } from '../src/db.js';

const [name, email, password] = process.argv.slice(2);
if (!name || !email || !password) {
  console.error('Usage: npm run create-user -- "Full Name" email password');
  process.exit(1);
}

try {
  const hash = await bcrypt.hash(password, 10);
  const { rows } = await pool.query(
    'INSERT INTO employees (name, email, password_hash) VALUES ($1, $2, $3) RETURNING id',
    [name, email.toLowerCase(), hash]
  );
  console.log(`Created employee #${rows[0].id} (${email})`);
} catch (err) {
  console.error(err.code === '23505' ? 'An employee with that email already exists.' : err.message);
  process.exitCode = 1;
} finally {
  await pool.end();
}
