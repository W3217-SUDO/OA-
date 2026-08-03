type PaymentRecord = {
  id?: number;
  serial_no?: string;
  customer?: string;
  contract_record_id?: number;
  contract_id?: number;
  contract_no?: string;
  data?: {
    contract_record_id?: number;
    contract_id?: number;
    contract_no?: string;
    amount?: number;
    pending_amount?: number;
  };
};

type ContractRecord = {
  id?: number;
  serial_no?: string;
  customer?: string;
};

type ContractPaymentNavigationInput = {
  pathname: string;
  hash?: string;
  payment: PaymentRecord;
  contract: ContractRecord;
};

type ContractPaymentNavigation =
  | { ok: true; page: "finance-payment-mine"; url: string }
  | { ok: false; message: string };

export const buildContractPaymentNavigation = ({
  pathname,
  hash = "",
  payment,
  contract,
}: ContractPaymentNavigationInput): ContractPaymentNavigation => {
  const paymentNo = String(payment.serial_no || "").trim();
  if (!paymentNo) return { ok: false, message: "当前付款记录缺少申请单号" };

  const sourceId = Number(payment.id || 0);
  if (!Number.isFinite(sourceId) || sourceId <= 0) {
    return { ok: false, message: "当前付款记录缺少来源ID" };
  }

  const contractId = Number(contract.id || 0);
  const paymentData = payment.data || {};
  const linkedIds = [payment.contract_record_id, payment.contract_id, paymentData.contract_record_id, paymentData.contract_id]
    .map((value) => Number(value || 0))
    .filter((value) => Number.isFinite(value) && value > 0);
  const uniqueIds = [...new Set(linkedIds)];
  const linkedNos = [payment.contract_no, paymentData.contract_no]
    .map((value) => String(value || "").trim())
    .filter(Boolean);
  const uniqueNos = [...new Set(linkedNos)];
  if (uniqueIds.length > 1 || uniqueNos.length > 1) {
    return { ok: false, message: "当前付款记录关联合同不一致" };
  }
  const paymentContractId = uniqueIds[0] || 0;
  const paymentContractNo = uniqueNos[0] || "";
  const currentContractNo = String(contract.serial_no || "").trim();
  if (paymentContractId > 0 && (!Number.isFinite(contractId) || paymentContractId !== contractId)) {
    return { ok: false, message: "当前付款记录关联合同不一致" };
  }
  if (paymentContractNo && (!currentContractNo || paymentContractNo !== currentContractNo)) {
    return { ok: false, message: "当前付款记录关联合同不一致" };
  }
  const contractNo = paymentContractNo || currentContractNo;
  if (!Number.isFinite(contractId) || contractId <= 0 || !contractNo) {
    return { ok: false, message: "当前付款记录缺少关联合同" };
  }

  const customer = String(payment.customer || contract.customer || "").trim();
  if (!customer) return { ok: false, message: "当前付款记录缺少客户信息" };

  const amount = [payment.data?.amount, payment.data?.pending_amount]
    .map((value) => Number(value || 0))
    .find((value) => Number.isFinite(value) && value > 0);
  if (!amount) return { ok: false, message: "当前付款记录缺少有效金额" };

  const params = new URLSearchParams();
  params.set("page", "finance-payment-mine");
  params.set("payment_no", paymentNo);
  params.set("contract_no", contractNo);
  params.set("customer", customer);
  params.set("amount", String(amount));
  params.set("source_id", String(sourceId));
  params.set("source_module", "contract_payment");
  params.set("return_page", `contract-detail-${contractId}-${encodeURIComponent(contractNo)}`);
  return {
    ok: true,
    page: "finance-payment-mine",
    url: `${pathname}?${params.toString()}${hash}`,
  };
};
