import { StatusDot } from "./StatusDot.jsx";

/** Requirement 4: a panel whose backend is unreachable degrades to this,
 * in place of its content - it never throws and never takes the rest of
 * the dashboard down with it (each panel's usePolling() call is independent). */
export function PanelError({ message, status, onRetry }) {
  const forbidden = status === 401 || status === 403;
  return (
    <div className="panel-error" role="alert">
      <StatusDot state="unknown" />
      <span>
        {forbidden
          ? `Your role is not permitted to read this feed (HTTP ${status})`
          : `Service unreachable${message ? ` (${message})` : ""}`}
      </span>
      {!forbidden && onRetry && (
        <button className="panel-retry" type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
