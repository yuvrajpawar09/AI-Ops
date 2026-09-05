export function Meter({ value }) {
  // value: 0.0 - 1.0. Same-ramp track+fill (both blue) per the meter spec -
  // confidence isn't a severity signal, so it doesn't borrow the status ramp.
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="meter">
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="meter-value">{pct}%</span>
    </div>
  );
}
