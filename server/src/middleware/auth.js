import jwt from 'jsonwebtoken';
import { config } from '../config.js';

export const COOKIE_NAME = 'token';

export function requireAuth(req, res, next) {
  const token = req.cookies[COOKIE_NAME];
  if (!token) return res.status(401).json({ error: 'Not authenticated' });
  try {
    const payload = jwt.verify(token, config.jwtSecret);
    req.user = { id: payload.sub };
    next();
  } catch {
    res.status(401).json({ error: 'Invalid or expired session' });
  }
}
