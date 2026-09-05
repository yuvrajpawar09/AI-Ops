// Shared between IncidentPanel (a small badge) and RemediationPanel (the
// full log) so both agree on what each outcome means and looks like.
export const OUTCOME_META = {
  DIAGNOSED_ONLY: { label: "Diagnosed only", className: "outcome-badge--neutral" },
  AUTO_RESOLVED: { label: "Auto-resolved", className: "outcome-badge--good" },
  ESCALATED_TO_HUMAN: { label: "Escalated to human", className: "outcome-badge--critical" },
};

export function outcomeMeta(outcome) {
  return OUTCOME_META[outcome] || OUTCOME_META.DIAGNOSED_ONLY;
}
