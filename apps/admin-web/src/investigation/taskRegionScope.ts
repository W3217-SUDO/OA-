import type { InvestigationRegionGroup } from "./types";
import { INVESTIGATION_REGION_GROUPS } from "../investigationRegionOptions.mjs";

type InvestigationAuthorizationData = {
  authorization_scope_type?: unknown;
  authorization_regions?: unknown;
  authorization_scope?: unknown;
  province?: unknown;
  city?: unknown;
};

export function investigationTaskRegionOptions(groups: InvestigationRegionGroup[]) {
  return groups.map(({ province, cities }) => ({
    value: province,
    label: province,
    children: cities.map((city) => ({ value: city, label: city })),
  }));
}

export function investigationTaskScopeGroups(data: InvestigationAuthorizationData): InvestigationRegionGroup[] {
  const groups = INVESTIGATION_REGION_GROUPS as InvestigationRegionGroup[];
  const regions = data.authorization_regions;
  if (data.authorization_scope_type === "R" && Array.isArray(regions) && regions.length > 0) {
    return groups.map((group) => ({
      ...group,
      cities: group.cities.filter((city) => regions.some(
        (path: string[]) => path[0] === group.province && (path.length === 1 || path[1] === city),
      )),
    })).filter((group) => group.cities.length > 0);
  }
  const scope = String(data.authorization_scope || "").trim();
  const scopeTokens = scope.split(/[\s,，、;；|/]+/).map((item) => item.trim()).filter(Boolean);
  if (data.authorization_scope_type === "N" || ["全国", "全国范围"].includes(scope) || scopeTokens.includes("全国")) return groups;

  const scopeIncludes = (value: string) => scopeTokens.includes(value) || scope.includes(value);
  const scopedGroups = groups.map(({ province, cities }) => {
    const selectedCities = scopeIncludes(province) ? cities : cities.filter((city) => scopeIncludes(city));
    return { province, cities: selectedCities };
  }).filter((group) => group.cities.length > 0);
  if (scopedGroups.length) return scopedGroups;

  const inheritedProvinces = new Set(String(data.province || "").split(/[、,，;；\s]+/).filter(Boolean));
  const inheritedCities = new Set(String(data.city || "").split(/[、,，;；\s]+/).filter(Boolean));
  return groups.map(({ province, cities }) => ({
    province,
    cities: inheritedProvinces.has(province) ? cities : cities.filter((city) => inheritedCities.has(city)),
  })).filter((group) => group.cities.length > 0);
}

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
