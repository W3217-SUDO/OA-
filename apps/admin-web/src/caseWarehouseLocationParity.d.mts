export type WarehouseLocationOption = {
  value: number;
  label: string;
  warehouseId: number;
  warehouseName: string;
  locationName: string;
};

export function buildWarehouseLocationOptions(catalog: unknown[]): WarehouseLocationOption[];
export function resolveCaseWarehouseLocationIds(
  data: Record<string, unknown>,
  options: WarehouseLocationOption[],
): number[];
