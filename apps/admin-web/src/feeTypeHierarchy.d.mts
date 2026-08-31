export type FeeTypeCatalogItem = {
  id: number;
  code: string;
  name: string;
  extra?: Record<string, unknown>;
  parent_code?: string;
  path?: string;
  depth?: number;
  root_code?: string;
  base_fee_type: string;
  expense_scopes: string[];
  has_children: boolean;
  selectable: boolean;
  is_active?: boolean;
};

export type FeeTypeTreeNode = {
  value: number;
  title: string;
  selectable: boolean;
  children?: FeeTypeTreeNode[];
};

export function feeTypeSelection(catalog: FeeTypeCatalogItem[], feeTypeId: unknown): FeeTypeCatalogItem | undefined;
export function selectableFeeTypes(catalog: FeeTypeCatalogItem[], scope: unknown, preset?: string): FeeTypeCatalogItem[];
export function feeTypeTreeData(catalog: FeeTypeCatalogItem[], scope: unknown, preset?: string): FeeTypeTreeNode[];
export function initialFeeTypeId(catalog: FeeTypeCatalogItem[], scope: unknown, preset?: string, preferredName?: string): number | undefined;
