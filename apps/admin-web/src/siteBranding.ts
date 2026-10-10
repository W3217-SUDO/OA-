import config from "./siteBranding.config.json";

const defaultBrand = {
  code: "sunhold",
  name: "Sunhold",
  navigationName: "Sunhold",
  compactName: "S",
  subtitle: "法律服务机构管理系统",
  welcome: "欢迎进入思法汇成协作平台",
  logo: "",
} as const;

const huzhiBrand = {
  code: "huzhi",
  name: "上海沪知律师事务所",
  navigationName: "沪知",
  compactName: "沪",
  subtitle: "法律服务机构管理系统",
  welcome: "欢迎进入沪知协作平台",
  documentTitle: "上海沪知律师事务所 OA 系统",
  logo: "/huzhi-logo.jpg",
  icon: "/huzhi-icon.svg",
  manifest: "/huzhi.webmanifest",
} as const;

export function resolveSiteBrand(hostname: string) {
  const host = hostname.trim().toLowerCase().replace(/\.$/, "");
  const configuredBrand = config.hostBrands[host as keyof typeof config.hostBrands];
  return configuredBrand === "huzhi" ? huzhiBrand : defaultBrand;
}
