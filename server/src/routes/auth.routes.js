import { Router } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { pool } from '../db.js';
import { config } from '../config.js';
import { COOKIE_NAME, requireAuth } from '../middleware/auth.js';

const router = Router();

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

const SESSION_MS = 12 * 60 * 60 * 1000;

router.post('/login', async (req, res, next) => {
  try {
    const parsed = loginSchema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ error: 'Email and password are required' });

    const { email, password } = parsed.data;
    const { rows } = await pool.query(
      'SELECT id, name, email, password_hash FROM employees WHERE email = $1',
      [email.toLowerCase()]
    );
    const employee = rows[0];
    const ok = employee && (await bcrypt.compare(password, employee.password_hash));
    if (!ok) return res.status(401).json({ error: 'Invalid email or password' });

    const token = jwt.sign({ sub: employee.id }, config.jwtSecret, { expiresIn: '12h' });
    res.cookie(COOKIE_NAME, token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: config.isProd,
      maxAge: SESSION_MS,
    });
    res.json({ id: employee.id, name: employee.name, email: employee.email });
  } catch (err) {
    next(err);
  }
});

router.post('/logout', requireAuth, (req, res) => {
  res.clearCookie(COOKIE_NAME);
  res.status(204).end();
});

router.get('/me', requireAuth, async (req, res, next) => {
  try {
    const { rows } = await pool.query('SELECT id, name, email FROM employees WHERE id = $1', [
      req.user.id,
    ]);
    if (!rows[0]) return res.status(401).json({ error: 'Account not found' });
    res.json(rows[0]);
  } catch (err) {
    next(err);
  }
});

export default router;
