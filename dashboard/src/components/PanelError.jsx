import { StatusDot } from "./StatusDot.jsx";

/** Requirement 4: a panel whose backend is unreachable degrades to this,
 * in place of its content - it never throws and never takes the rest of
 * the dashboard down with it (each panel's usePolling() call is independent). */
export function PanelError({ message }) {
  return (
    <div className="panel-error">
      <StatusDot state="unknown" />
      Service unreachable{message ? ` (${message})` : ""}
    </div>
  );
}
