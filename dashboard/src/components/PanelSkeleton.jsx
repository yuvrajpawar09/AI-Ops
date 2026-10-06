export function PanelSkeleton({ rows = 3 }) {
  return (
    <div className="skeleton" role="status" aria-live="polite">
      <span className="sr-only">Loading</span>
      {Array.from({ length: rows }).map((_, i) => (
        <div className="skeleton-row" key={i}>
          <div className="skeleton-bar skeleton-bar--wide" />
          <div className="skeleton-bar skeleton-bar--narrow" />
        </div>
      ))}
    </div>
  );
}
