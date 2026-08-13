export type InvestigationRegionOption = {
  label: string;
  value: string;
};

export type InvestigationRegionGroup = {
  province: string;
  cities: string[];
};

export const INVESTIGATION_REGION_OPTIONS: InvestigationRegionOption[];
export const INVESTIGATION_REGION_GROUPS: InvestigationRegionGroup[];
