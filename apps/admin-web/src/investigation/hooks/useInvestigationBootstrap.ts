import { useState } from "react";
import { message } from "antd";
import { api } from "../../api";
import type {
  InvestigationBootstrapData,
  Profile,
  PersonOption,
  WarehouseCatalogItem,
} from "../types";

export const loadInvestigationBootstrap = (): Promise<InvestigationBootstrapData> =>
  Promise.all([
    api.get("/auth/me").then(({ data }) => data as Profile),
    api.get("/investigations/assignment-supervisor")
      .then(({ data }) => String(data.username || ""))
      .catch(() => ""),
    api.get("/system/parameters/options", { params: { category: "notary_office" } })
      .then(({ data }) =>
        (data.items || [])
          .map((item: { name?: string }) => ({ value: String(item.name || "").trim() }))
          .filter((item: { value: string }) => item.value),
      )
      .catch(() => [] as { value: string }[]),
    api.get("/people/options")
      .then(({ data }) => data.items || [])
      .catch(() => [] as PersonOption[]),
    api.get("/warehouse/catalog")
      .then(({ data }) => data.items || [])
      .catch(() => [] as WarehouseCatalogItem[]),
  ]).then(([profile, assignmentSupervisor, notaryOfficeOptions, casePeopleOptions, warehouseCatalog]) => ({
    profile, assignmentSupervisor, notaryOfficeOptions, casePeopleOptions, warehouseCatalog,
  }));

export function useInvestigationBootstrap() {
  const [profile, setProfile] = useState<Profile>({
    username: "",
    display_name: "",
    role: "",
  });
  const [assignmentSupervisor, setAssignmentSupervisor] = useState("");
  const [notaryOfficeOptions, setNotaryOfficeOptions] = useState<{ value: string }[]>([]);
  const [casePeopleOptions, setCasePeopleOptions] = useState<PersonOption[]>([]);
  const [warehouseCatalog, setWarehouseCatalog] = useState<WarehouseCatalogItem[]>([]);

  const loadBootstrap = async () => {
    try {
      const data = await loadInvestigationBootstrap();
      setProfile(data.profile);
      setAssignmentSupervisor(data.assignmentSupervisor);
      setNotaryOfficeOptions(data.notaryOfficeOptions);
      setCasePeopleOptions(data.casePeopleOptions);
      setWarehouseCatalog(data.warehouseCatalog);
    } catch {
      message.error("调查辅助数据加载失败，业务列表仍可正常使用");
    }
  };

  return {
    profile,
    setProfile,
    assignmentSupervisor,
    setAssignmentSupervisor,
    notaryOfficeOptions,
    setNotaryOfficeOptions,
    casePeopleOptions,
    setCasePeopleOptions,
    warehouseCatalog,
    setWarehouseCatalog,
    loadBootstrap,
  };
}
