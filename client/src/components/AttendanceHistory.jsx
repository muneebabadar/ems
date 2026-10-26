export default function AttendanceHistory({ records }) {
  if (records.length === 0) return <p className="muted">No attendance recorded yet.</p>;

  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Day</th>
          <th>Check-in time</th>
        </tr>
      </thead>
      <tbody>
        {records.map((r) => (
          <tr key={r.date}>
            <td>{r.date}</td>
            <td>{r.day}</td>
            <td>{new Date(r.checkInTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
