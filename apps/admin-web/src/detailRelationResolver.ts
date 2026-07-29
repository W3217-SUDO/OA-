import { api } from "./api";

export type DetailRelationModule = "case" | "contract" | "customer";

export type DetailRelationTarget = {
  id: number;
  serial_no: string;
  title: string;
  customer?: string;
};

/** Resolve a visible business object before changing routes.
 *
 * Display fields may outlive the linked record (for example after a local
 * acceptance cleanup), so navigation must not leave the user on an unrelated
 * unfiltered list.  The server-side record query also applies data scope.
 */
export async function resolveDetailRelation(
  module: DetailRelationModule,
  target: { serial_no?: unknown; title?: unknown },
): Promise<DetailRelationTarget | null> {
  const serialNo = String(target.serial_no || "").trim();
  const title = String(target.title || "").trim();
  const keyword = serialNo || title;
  if (!keyword) return null;
  const { data } = await api.get("/records", {
    params: { module, keyword, page_size: 100 },
  });
  return ((data.items || []) as DetailRelationTarget[]).find((item) => {
    if (serialNo && item.serial_no === serialNo) return true;
    return Boolean(title && (item.title === title || item.customer === title));
  }) || null;
}
