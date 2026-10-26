-- Run once in the Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS employees (
  id            SERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attendance (
  id            SERIAL PRIMARY KEY,
  employee_id   INT  NOT NULL REFERENCES employees(id),
  date          DATE NOT NULL,
  day           TEXT NOT NULL,            -- 'Monday' ... 'Sunday'
  check_in_time TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (employee_id, date)              -- one mark per employee per day
);

-- Employees are created with: npm run create-user -- "Name" email password
