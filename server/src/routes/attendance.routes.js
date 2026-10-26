import { Router } from 'express';
import { pool } from '../db.js';
import { config } from '../config.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();
router.use(requireAuth);

// "Today" is always the calendar date in the company timezone, decided by the DB clock.
const TODAY_SQL = `(now() AT TIME ZONE $2)::date`;

const MS_UNTIL_NEXT_DAY_SQL = `
  SELECT (EXTRACT(EPOCH FROM (
    (date_trunc('day', now() AT TIME ZONE $1) + interval '1 day') AT TIME ZONE $1 - now()
  )) * 1000)::bigint AS ms`;

async function msUntilNextDay() {
  const { rows } = await pool.query(MS_UNTIL_NEXT_DAY_SQL, [config.timezone]);
  return Number(rows[0].ms);
}

router.get('/today', async (req, res, next) => {
  try {
    const { rows } = await pool.query(
      `SELECT check_in_time FROM attendance WHERE employee_id = $1 AND date = ${TODAY_SQL}`,
      [req.user.id, config.timezone]
    );
    res.json({
      marked: rows.length > 0,
      checkInTime: rows[0]?.check_in_time ?? null,
      msUntilNextDay: await msUntilNextDay(),
    });
  } catch (err) {
    next(err);
  }
});

router.post('/', async (req, res, next) => {
  try {
    const { rows } = await pool.query(
      `INSERT INTO attendance (employee_id, date, day)
       VALUES ($1, ${TODAY_SQL}, trim(to_char(now() AT TIME ZONE $2, 'FMDay')))
       ON CONFLICT (employee_id, date) DO NOTHING
       RETURNING date::text AS date, day, check_in_time AS "checkInTime"`,
      [req.user.id, config.timezone]
    );
    if (rows.length === 0) return res.status(409).json({ error: 'Attendance already marked today' });
    res.status(201).json(rows[0]);
  } catch (err) {
    next(err);
  }
});

router.get('/', async (req, res, next) => {
  try {
    const { rows } = await pool.query(
      `SELECT date::text AS date, day, check_in_time AS "checkInTime"
       FROM attendance WHERE employee_id = $1 ORDER BY date DESC`,
      [req.user.id]
    );
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

export default router;
