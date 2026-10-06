import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext.jsx";

export function ProtectedRoute({ children, capability }) {
  const { status, can } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="route-loading" role="status" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        Checking your session...
      </div>
    );
  }

  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (capability && !can(capability)) {
    return <Navigate to="/app" replace />;
  }

  return children;
}
