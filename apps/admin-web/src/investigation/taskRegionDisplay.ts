export function taskRegionLabel(data: Record<string, any> | undefined): string {
  const regions = data?.investigation_regions;
  if (Array.isArray(regions) && regions.length > 0) {
    return regions.map((path: string[]) => path.join(" ")).join("、");
  }
  return data?.region || [data?.province, data?.city, data?.district].filter(Boolean).join(" ") || "—";
}
