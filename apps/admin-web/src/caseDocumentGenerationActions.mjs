export const LEGACY_CASE_DOCUMENT_GENERATION_ITEMS = Object.freeze([
  ["archive-cover", "生成归档封面"],
  ["authorization-letter", "生成授权委托书"],
  ["first-instance-appellant-lawyer-letter", "生成一审所函(我方原告)"],
  ["first-instance-appellee-lawyer-letter", "生成一审所函(我方被告)"],
  ["second-instance-appellant-lawyer-letter", "生成二审所函(我方上诉)"],
  ["second-instance-appellee-lawyer-letter", "生成二审所函(对方上诉)"],
  ["execution-lawyer-letter", "生成执行所函"],
  ["gd-authorization-letter", "生成广东版授权委托书"],
  ["gd-first-instance-appellant-lawyer-letter", "生成广东版一审上诉人律师函"],
  ["gd-first-instance-appellee-lawyer-letter", "生成广东版一审被上诉人律师函"],
  ["gd-second-instance-appellant-lawyer-letter", "生成广东版二审上诉人律师函"],
  ["gd-second-instance-appellee-lawyer-letter", "生成广东版二审被上诉人律师函"],
  ["gd-execution-lawyer-letter", "生成广东版执行律师函"],
  ["identity-certificate", "生成身份证明"],
  ["identification_letter", "生成鉴定函"],
  ["settlement-list", "生成结算提成表"],
  ["compensation-payment-application", "生成代收代付赔偿款申请单"],
]);

const generationActionKeys = new Set(LEGACY_CASE_DOCUMENT_GENERATION_ITEMS.map(([key]) => key));

export const getLegacyCaseDocumentGenerationItems = () => LEGACY_CASE_DOCUMENT_GENERATION_ITEMS;

// Keep Ant Design's menu event translation in one testable place. In
// particular, the first two legacy actions must not depend on where the popup
// happens to be positioned in the case drawer.
export const dispatchCaseDocumentGenerationMenuClick = (event, runAction) => {
  event?.domEvent?.preventDefault?.();
  event?.domEvent?.stopPropagation?.();
  const key = String(event?.key ?? "");
  if (!generationActionKeys.has(key)) return false;
  runAction(key);
  return true;
};
