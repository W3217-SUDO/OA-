export const shouldApplyCaseClueResponse = ({
  requestId,
  currentRequestId,
  currentCaseId,
  targetCaseId,
}) => requestId === currentRequestId && currentCaseId === targetCaseId;
