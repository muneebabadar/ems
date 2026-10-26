import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import helmet from 'helmet';
import cookieParser from 'cookie-parser';
import { config } from './config.js';
import { pool } from './db.js';
import authRoutes from './routes/auth.routes.js';
import attendanceRoutes from './routes/attendance.routes.js';
import { errorHandler } from './middleware/errorHandler.js';

const app = express();
app.set('trust proxy', 1); // Render terminates TLS in front of the app

app.use(helmet());
app.use(express.json());
app.use(cookieParser());

app.get('/api/health', (req, res) => res.json({ ok: true }));
app.use('/api/auth', authRoutes);
app.use('/api/attendance', attendanceRoutes);
app.use('/api', (req, res) => res.status(404).json({ error: 'Not found' }));

// Serve the built React app in production (one Render service for everything).
const clientDist = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../client/dist');
app.use(express.static(clientDist));
app.use((req, res) => res.sendFile(path.join(clientDist, 'index.html')));

app.use(errorHandler);

const server = app.listen(config.port, () => {
  console.log(`Server listening on port ${config.port} (tz: ${config.timezone})`);
});

process.on('SIGTERM', () => {
  server.close(() => pool.end());
});
