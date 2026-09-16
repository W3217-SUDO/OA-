export const isMoneyHeader = (header: string) => /金额|提成|已分官费|已分代理费|已分其他费用|扣归档费|已分配|未分配|本次结算|实际结算|到账额/.test(header)
  && !/类型|编号|日期|时间|备注|状态|比例/.test(header);

export const moneyColumnStyle = (header: string) => isMoneyHeader(header)
  ? { align: "right" as const, className: "finance-money-column" }
  : {};
