import type { InvestigationRegionGroup } from "./types";

export function intersectInvestigationTaskScopes(
  rootGroups: InvestigationRegionGroup[], parentGroups: InvestigationRegionGroup[],
): InvestigationRegionGroup[] {
  return rootGroups.map((group) => ({
    ...group,
    cities: group.cities.filter((city) => parentGroups.some(
      (parent) => parent.province === group.province && parent.cities.includes(city),
    )),
  })).filter((group) => group.cities.length > 0);
}

export function investigationTaskPathAllowed(
  path: string[], groups: InvestigationRegionGroup[], allGroups: InvestigationRegionGroup[],
): boolean {
  const group = groups.find((item) => item.province === path[0]);
  if (!group) return false;
  if (path.length === 2) return group.cities.includes(path[1]);
  const province = allGroups.find((item) => item.province === path[0]);
  return path.length === 1 && Boolean(province?.cities.every((city) => group.cities.includes(city)));
}
