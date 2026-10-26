export default function MarkAttendanceButton({ marked, checkInTime, busy, onMark }) {
  return (
    <div className="mark">
      <button className="btn" disabled={marked || busy} onClick={onMark}>
        {marked ? 'Marked Present' : busy ? 'Marking…' : 'Mark Attendance'}
      </button>
      {marked && checkInTime && (
        <p className="muted">
          Checked in at {new Date(checkInTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
    </div>
  );
}
