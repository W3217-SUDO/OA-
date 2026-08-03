/**
 * Synchronous single-flight gate for finance mutations.
 * React state remains presentation-only; this closure closes the same-render
 * double-click window before an async request is started.
 */
export function createFinanceActionGate() {
  let inFlight = false;
  return {
    tryEnter() {
      if (inFlight) return false;
      inFlight = true;
      return true;
    },
    leave() {
      inFlight = false;
    },
  };
}
