// 501368：企业信息查询页和新建客户页共用的类型与一次性预填键。
export type LibraryRoles = { customers: { id: number; serial_no: string; title: string }[]; parties: { id: number; party_no: string; name: string }[] };
export type LibraryCompany = {
  name: string; credit_code: string; legal_representative: string; registered_address: string; organization_type: string;
  status: string; established_date: string; registered_capital: string; queried_at: string; queried_by?: string; abnormal: boolean; roles: LibraryRoles;
  phone?: string; business_scope?: string; registration_authority?: string; cached?: boolean;
};
/** 新建客户页读取的一次性预填（企业信息查询 → 新建客户）。 */
export const COMPANY_PREFILL_KEY = "oa-company-library-prefill";

