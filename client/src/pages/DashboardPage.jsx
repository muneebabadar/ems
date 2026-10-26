import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../context/AuthContext.jsx';
import MarkAttendanceButton from '../components/MarkAttendanceButton.jsx';
import AttendanceHistory from '../components/AttendanceHistory.jsx';

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [today, setToday] = useState(null); // { marked, checkInTime, msUntilNextDay }
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const [t, h] = await Promise.all([api.today(), api.history()]);
      setToday(t);
      setHistory(h);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Re-check when the next day starts so the button re-enables without a reload.
  useEffect(() => {
    if (!today) return;
    const timer = setTimeout(refresh, today.msUntilNextDay + 1000);
    return () => clearTimeout(timer);
  }, [today, refresh]);

  // Also re-check when the tab regains focus (laptop asleep over midnight, etc).
  useEffect(() => {
    const onVisible = () => document.visibilityState === 'visible' && refresh();
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [refresh]);

  async function handleMark() {
    setBusy(true);
    setError('');
    try {
      await api.mark();
    } catch (err) {
      if (err.status !== 409) setError(err.message); // 409 = already marked; just resync
    }
    await refresh();
    setBusy(false);
  }

  return (
    <main className="card">
      <header>
        <h1>Hi, {user.name}</h1>
        <button className="link" onClick={logout}>
          Log out
        </button>
      </header>
      <p className="muted">
        {new Date().toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
      </p>

      {today && (
        <MarkAttendanceButton
          marked={today.marked}
          checkInTime={today.checkInTime}
          busy={busy}
          onMark={handleMark}
        />
      )}
      {error && <p className="error">{error}</p>}

      <h2>Attendance history</h2>
      <AttendanceHistory records={history} />
    </main>
  );
}
