const APPROVED_STATUS = "\u5df2\u901a\u8fc7";
const PRESENTED_APPROVED_STATUS = "\u5ba1\u6279\u901a\u8fc7";

export const displayContractStatus = (status) => (
  String(status ?? "") === APPROVED_STATUS ? PRESENTED_APPROVED_STATUS : status
);
