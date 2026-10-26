import 'dotenv/config';

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
}

export const config = {
  databaseUrl: required('DATABASE_URL'),
  databaseSsl: process.env.DATABASE_SSL !== 'false', // Supabase needs SSL; local test Postgres doesn't

  jwtSecret: required('JWT_SECRET'),
  timezone: process.env.APP_TIMEZONE || 'UTC',
  port: Number(process.env.PORT) || 3000,
  isProd: process.env.NODE_ENV === 'production',
};
