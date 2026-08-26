const normalizeLocationText = (value) => String(value || "")
  .trim()
  .replace(/\s+/g, "")
  .replace(/[\/\\]/g, "-")
  .toLocaleLowerCase();

export const buildWarehouseLocationOptions = (catalog) => (Array.isArray(catalog) ? catalog : [])
  .filter((warehouse) => warehouse?.is_active)
  .flatMap((warehouse) => (Array.isArray(warehouse.locations) ? warehouse.locations : [])
    .filter((location) => location?.is_active)
    .map((location) => ({
      value: Number(location.id),
      label: `${warehouse.name} (${location.name})`,
      warehouseId: Number(warehouse.id),
      warehouseName: String(warehouse.name || ""),
      locationName: String(location.name || ""),
    })))
  .filter((option) => Number.isInteger(option.value) && option.value > 0);

export const resolveCaseWarehouseLocationIds = (data, options) => {
  const stored = Array.isArray(data?.warehouse_location_ids)
    ? data.warehouse_location_ids.map(Number).filter((value) => Number.isInteger(value) && value > 0)
    : [];
  if (stored.length) return [...new Set(stored)];

  const legacyText = String(data?.deposit_address || data?.warehouse_location || "").trim();
  if (!legacyText) return [];
  const parts = legacyText.split(/[,;]+/).map(normalizeLocationText).filter(Boolean);
  return [...new Set((Array.isArray(options) ? options : [])
    .filter((option) => {
      const labels = [
        option.label,
        `${option.warehouseName} (${option.locationName})`,
        `${option.warehouseName}-${option.locationName}`,
        `${option.warehouseName}${option.locationName}`,
      ].map(normalizeLocationText);
      return parts.some((part) => labels.includes(part));
    })
    .map((option) => Number(option.value)))];
};
