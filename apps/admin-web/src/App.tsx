import {
  Component,
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useState,
  type ComponentType,
  type ReactNode,
} from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Dropdown,
  Form,
  Input,
  Layout,
  Menu,
  message,
  Modal,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
} from "antd";
import {
  BankOutlined,
  DashboardOutlined,
  DownloadOutlined,
  DownOutlined,
  FileTextOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  HomeOutlined,
  LinkOutlined,
  MenuFoldOutlined,
  MessageOutlined,
  MenuOutlined,
  MenuUnfoldOutlined,
  ReloadOutlined,
  RobotOutlined,
  SearchOutlined,
  TeamOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { api, AUTH_EXPIRED_EVENT } from "./api";
import "dingtalk-jsapi/entry/union";
import requestDingTalkAuthCode from "dingtalk-jsapi/api/runtime/permission/requestAuthCode";
import { getENV as getDingTalkEnvironment } from "dingtalk-jsapi/lib/env";
import NotificationCenter from "./NotificationCenter";
import GlobalSearch from "./GlobalSearch";
import { rememberCaseDetailTarget } from "./caseDetailNavigation";
import { rememberCustomerDetailTarget } from "./customerDetailNavigation";
import {
  CONTRACT_DETAIL_TARGET_EVENT,
  clearContractDetailTarget,
  type ContractDetailNavigationContext,
} from "./contractDetailNavigation";
import {
  clearContractCustomerContext,
  CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY,
} from "./contractCreateContext";

function reloadAppShell() {
  const url = new URL(window.location.href);
  url.searchParams.set("_v", String(Date.now()));
  window.location.replace(url.toString());
}

function lazyWithVersionRecovery<T extends ComponentType<any>>(
  key: string,
  importer: () => Promise<{ default: T }>,
) {
  return lazy(async () => {
    const marker = `sunhold:chunk-reload:${key}`;
    try {
      const module = await importer();
      sessionStorage.removeItem(marker);
      return module;
    } catch (error) {
      // A user can keep the previous shell open while a new image replaces its
      // hashed chunks. Reload once to fetch the current no-store index page.
      if (!sessionStorage.getItem(marker)) {
        sessionStorage.setItem(marker, "1");
        reloadAppShell();
        return new Promise<never>(() => undefined);
      }
      sessionStorage.removeItem(marker);
      throw error;
    }
  });
}

class PageLoadBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error, info: { componentStack: string }) {
    // Keep the generic recovery UI, but retain the real failure in browser logs.
    console.error("Page render failed", error, info.componentStack);
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <Alert
        type="error"
        showIcon
        message="页面资源加载失败"
        description="系统版本已更新或网络暂时中断，请刷新后重试。"
        action={<Button onClick={reloadAppShell}>刷新页面</Button>}
      />
    );
  }
}

const CustomerConflictPage = lazyWithVersionRecovery("customer-conflict", () => import("./CustomerConflictPage"));
const ContractReceivablesPage = lazyWithVersionRecovery("contract-receivables", () => import("./ContractReceivablesPage"));
const InvestigationCenterPage = lazyWithVersionRecovery("investigation", () => import("./InvestigationCenterPage"));
const CaseCenterPage = lazyWithVersionRecovery("case", () => import("./CaseCenterPage"));
const IprCenterPage = lazyWithVersionRecovery("ipr", () => import("./IprCenterPage"));
const IprOfficialFilePage = lazyWithVersionRecovery("ipr-office-files", () => import("./IprOfficialFilePage"));
const IprCustomFileImportPage = lazyWithVersionRecovery("ipr-custom-file-import", () => import("./IprCustomFileImportPage"));
const TaskCenterPage = lazyWithVersionRecovery("task", () => import("./TaskCenterPage"));
const BusinessPage = lazyWithVersionRecovery("business", () => import("./BusinessPage"));
const DocumentCenterPage = lazyWithVersionRecovery("document", () => import("./DocumentCenterPage"));
const FinanceCenterPage = lazyWithVersionRecovery("finance", () => import("./FinanceCenterPage"));
const SystemCenterPage = lazyWithVersionRecovery("system", () => import("./SystemCenterPage"));
const IprFileTypeSettingsPage = lazyWithVersionRecovery("ipr-file-types", () => import("./IprFileTypeSettingsPage"));
const LawFirmPage = lazyWithVersionRecovery("law-firms", () => import("./LawFirmPage"));
const HrCenterPage = lazyWithVersionRecovery("hr", () => import("./HrCenterPage"));
const OrganizationCenterPage = lazyWithVersionRecovery("organization", () => import("./OrganizationCenterPage"));
const WarehousePage = lazyWithVersionRecovery("warehouse", () => import("./WarehousePage"));
const ReportCenterPage = lazyWithVersionRecovery("report", () => import("./ReportCenterPage"));
const CustomerCenterPage = lazyWithVersionRecovery("customer", () => import("./CustomerCenterPage"));
const ContractCenterPage = lazyWithVersionRecovery("contract", () => import("./ContractCenterPage"));
const AuditLogPage = lazyWithVersionRecovery("audit-log", () => import("./AuditLogPage"));
const AgentDocumentPage = lazyWithVersionRecovery("agent-document", () => import("./AgentDocumentPage"));
const AgentCenterPage = lazyWithVersionRecovery("agent-center", () => import("./AgentCenterPage"));
const SealCenterPage = lazyWithVersionRecovery("seal", () => import("./SealCenterPage"));
const UserCenterPage = lazyWithVersionRecovery("user", () => import("./UserCenterPage"));
const MessageCenterPage = lazyWithVersionRecovery("message", () => import("./MessageCenterPage"));
const CommunicationLogPage = lazyWithVersionRecovery("communication", () => import("./CommunicationLogPage"));
const CustomerPortalPage = lazyWithVersionRecovery("customer-portal", () => import("./CustomerPortalPage"));

const { Header, Sider, Content } = Layout;

type NavItem = {
  key: string;
  icon?: ReactNode;
  label: string;
  badge?: string;
  disabled?: boolean;
  link_url?: string;
  menu_type_id?: number;
  open_target?: string;
  children?: NavItem[];
};
type NavConfig = {
  id: number;
  key: string;
  parent_key: string;
  label: string;
  icon: string;
  sort_order: number;
  is_visible: boolean;
  is_active: boolean;
  is_system?: boolean;
  link_url?: string;
  LinkUrl?: string;
  menu_type_id?: number;
  menu_type?: number;
  MenuTypeId?: number;
  open_target?: string;
};

const menuItems: NavItem[] = [
  {
    key: "dashboard",
    icon: <DashboardOutlined />,
    label: "控制台",
    badge: "hot",
  },
  {
    key: "agent-center",
    icon: <RobotOutlined />,
    label: "智能体中心",
  },
  {
    key: "seal",
    icon: <FileTextOutlined />,
    label: "用印中心",
    children: [
      { key: "seal-my", label: "我的申请" },
      { key: "seal-audit", label: "用印审批" },
      { key: "seal-admin", label: "印章管理" },
    ],
  },
  {
    key: "task",
    icon: <FileTextOutlined />,
    label: "事务中心",
    children: [
      {
        key: "task-my",
        label: "我的任务",
        children: [
          { key: "task-my-created", label: "我发起的任务" },
          { key: "task-my-accepted", label: "我接受的任务" },
          { key: "task-my-collaborating", label: "我协作的任务" },
          { key: "task-my-unread", label: "未读新消息的任务" },
        ],
      },
      {
        key: "task-dept",
        label: "部门任务",
        children: [
          { key: "task-dept-created", label: "部门发起的任务" },
          { key: "task-dept-accepted", label: "部门接受的任务" },
          { key: "task-dept-collaborating", label: "部门协作的任务" },
        ],
      },
      {
        key: "task-company",
        label: "全所任务",
        children: [
          { key: "task-company-created", label: "公司发起的任务" },
          { key: "task-company-accepted", label: "公司接受的任务" },
          { key: "task-company-collaborating", label: "公司协作的任务" },
        ],
      },
      { key: "affairs-records", label: "事项记录" },
    ],
  },
  {
    key: "customer",
    icon: <TeamOutlined />,
    label: "客户管理",
    children: [
      { key: "customer-new", label: "新建客户" },
      { key: "customer-mine", label: "我的客户" },
      { key: "customer-recycle", label: "个人回收站" },
      { key: "customer-dept", label: "部门客户" },
      { key: "customer-dept-recycle", label: "部门回收站" },
      { key: "customer-company", label: "公司客户" },
      { key: "customer-public", label: "公海客户" },
      { key: "customer-shared", label: "我的共享客户" },
      { key: "customer-recent-contact", label: "最近联系的客户" },
      { key: "customer-recent-update", label: "最近更新的客户" },
      { key: "customer-company-recycle", label: "公司回收站" },
      { key: "customer-conflict", label: "客户利益检索" },
    ],
  },
  {
    key: "contract",
    icon: <FileTextOutlined />,
    label: "合同中心",
    children: [
      { key: "contract-new", label: "合同新建" },
      { key: "contract-mine", label: "我的合同" },
      { key: "contract-audit", label: "合同审批" },
      { key: "contract-receivable", label: "合同应收" },
    ],
  },
  {
    key: "case",
    icon: <FileTextOutlined />,
    label: "案件中心",
    children: [
      {
        key: "case-new",
        label: "新建案件",
        children: [
          { key: "case-new-civil", label: "民事争议" },
          { key: "case-new-criminal", label: "刑事案件" },
          { key: "case-new-administrative", label: "行政案件及国家赔偿" },
          { key: "case-new-counsel", label: "法律顾问" },
          { key: "case-new-arbitration", label: "仲裁" },
        ],
      },
      { key: "case-mine", label: "我的案件" },
      { key: "case-dept", label: "部门案件" },
      { key: "case-company", label: "全所案件" },
      { key: "case-schedule", label: "开庭排期" },
      { key: "case-execution", label: "执行案件" },
      { key: "case-archive", label: "归档审核" },
    ],
  },
  {
    key: "ipr",
    label: "知识产权中心",
    children: [
      { key: "ipr-patent", label: "专利案件" },
      { key: "ipr-trademark", label: "商标案件" },
      { key: "ipr-review", label: "知识产权立案审核" },
      { key: "ipr-office-files", label: "知识产权官文" },
      { key: "ipr-custom-file-import", label: "案件自定义文件导入" },
    ],
  },
  {
    key: "investigation",
    icon: <SearchOutlined />,
    label: "调查大厅",
    children: [
      {
        key: "investigation-task-published",
        label: "我发布的调查任务",
        icon: <UnorderedListOutlined />,
        children: [
          { key: "investigation-task-mine", label: "我的调查任务" },
          { key: "investigation-task-overdue", label: "过期调查任务" },
        ],
      },
      { key: "investigation-task-unassigned", label: "待我分配的调查任务", icon: <UnorderedListOutlined /> },
      { key: "investigation-task-sub-published", label: "我发布的调查子任务", icon: <UnorderedListOutlined /> },
      { key: "investigation-task-sub-mine", label: "我的调查任务", icon: <UnorderedListOutlined /> },
      {
        key: "clue",
        label: "我的调查线索",
        icon: <UnorderedListOutlined />,
        children: [
          { key: "clue-my-draft", label: "待提交线索" },
          { key: "clue-my-pending", label: "待审核线索" },
          { key: "clue-my-customer", label: "待客户审核" },
          { key: "clue-my-collect", label: "待取证线索" },
          { key: "clue-my-collected", label: "已取证线索" },
          { key: "clue-my-refused", label: "已拒绝线索" },
          { key: "clue-my-no-fee", label: "未申请费用线索" },
          { key: "clue-my-fee", label: "已申请费用线索" },
        ],
      },
      {
        key: "clue-audit",
        label: "调查线索审核",
        icon: <UnorderedListOutlined />,
        children: [
          { key: "clue-audit-pending", label: "待审批线索" },
          { key: "clue-audit-customer", label: "待客户审核" },
          { key: "clue-audit-refused", label: "已拒绝线索" },
          { key: "clue-audit-collect", label: "待取证线索" },
          { key: "clue-audit-collected", label: "已取证线索" },
        ],
      },
      {
        key: "clue-company",
        label: "公司调查线索",
        icon: <UnorderedListOutlined />,
        children: [
          { key: "clue-company-draft", label: "待提交线索" },
          { key: "clue-company-pending", label: "待审核线索" },
          { key: "clue-company-collect", label: "待取证线索" },
          { key: "clue-company-collected", label: "已取证线索" },
          { key: "clue-company-refused", label: "已拒绝线索" },
          { key: "clue-company-no-fee", label: "未申请费用线索" },
          { key: "clue-company-fee", label: "已申请费用线索" },
        ],
      },
      {
        key: "notary",
        label: "公证信息导入",
        icon: <UnorderedListOutlined />,
        children: [
          { key: "notary-import-info", label: "公证信息导入" },
          { key: "notary-import-storage", label: "取证信息文件导入" },
          { key: "notary-import-files", label: "公证书文件导入" },
          { key: "notary-import-invoices", label: "发票文件导入" },
        ],
      },
    ],
  },
  {
    key: "documents",
    icon: <FileTextOutlined />,
    label: "收发文台",
    children: [
      { key: "documents-official", label: "官文收文" },
      { key: "documents-outgoing", label: "正式发文" },
      { key: "documents-my", label: "我的收文" },
      { key: "documents-company", label: "公司收文" },
      { key: "documents-register", label: "收发文登记" },
      { key: "documents-files", label: "文件附件" },
      { key: "documents-template", label: "文书模板" },
      { key: "documents-agent", label: "AI 智能文档" },
      { key: "documents-archive", label: "归档材料" },
    ],
  },
  {
    key: "finance",
    icon: <FileTextOutlined />,
    label: "财务中心",
    children: [
      {
        key: "finance-receipts",
        label: "回款管理",
        children: [
          { key: "finance-receipts-icbc", label: "回款(工行)" },
          { key: "finance-receipts-citic", label: "回款(中信)" },
          { key: "finance-receipts-boc", label: "回款(中行)" },
          { key: "finance-receipts-new", label: "新增回款" },
          { key: "finance-receipts-manage", label: "回款管理" },
          { key: "finance-receipts-claim", label: "回款领取" },
          { key: "finance-receipts-pending", label: "待分配回款" },
          { key: "finance-receipts-allocated", label: "已分配回款" },
          { key: "finance-receipts-query", label: "到账查询" },
        ],
      },
      {
        key: "finance-payment",
        label: "付款管理",
        children: [
          { key: "finance-payment-mine", label: "我的请款单" },
          { key: "finance-payment-audit", label: "请款单审批" },
          { key: "finance-payment-waiting", label: "待付款列表" },
          { key: "finance-payment-print", label: "付款单打印" },
          { key: "finance-payment-writeoff", label: "待核销列表" },
          { key: "finance-payment-query", label: "付款单查询" },
        ],
      },
      { key: "finance-internal", label: "内部费用" },
      { key: "finance-invoice", label: "开票管理" },
      { key: "finance-settlement", label: "结算管理" },
      { key: "finance-archive-fee", label: "归档费结算" },
      { key: "finance-fee-query", label: "费用查询" },
    ],
  },
  {
    key: "platform-finance",
    icon: <BankOutlined />,
    label: "平台财务中心",
    children: [
      { key: "platform-finance-overview", label: "回款管理" },
      { key: "platform-finance-payment", label: "付款管理" },
      { key: "platform-finance-invoice", label: "开票管理" },
      { key: "platform-finance-settlement", label: "结算管理" },
      { key: "platform-finance-archive-fee", label: "归档费结算" },
      { key: "platform-finance-fee-query", label: "费用查询" },
    ],
  },
  {
    key: "user-center",
    icon: <UserOutlined />,
    label: "用户中心",
    children: [
      { key: "user-messages", label: "消息通知" },
      { key: "user-communications", label: "沟通日志" },
      { key: "user-account", label: "账户管理" },
    ],
  },
  {
    key: "hr",
    icon: <TeamOutlined />,
    label: "人事中心",
    children: [
      { key: "hr-new", label: "新建员工" },
      { key: "hr-all", label: "员工管理" },
      { key: "hr-departments", label: "部门管理" },
      { key: "hr-roles", label: "角色管理" },
    ],
  },
  {
    key: "system",
    icon: <UserOutlined />,
    label: "系统中心",
    children: [
      {
        key: "system-parameters",
        label: "系统参数",
        children: [
          { key: "system-parameters-case-type", label: "案件类型" },
          { key: "system-parameters-fee-type", label: "费用类型" },
          { key: "system-parameters-case-phase", label: "案件阶段" },
          { key: "system-parameters-court", label: "法院设置" },
          { key: "system-parameters-notary", label: "公证处设置" },
          { key: "system-parameters-cause", label: "案由设置" },
          { key: "system-parameters-payment", label: "付款类型" },
          { key: "system-parameters-company", label: "公司设置" },
          { key: "system-parameters-customer-type", label: "客户类型" },
          { key: "system-parameters-case-file-type", label: "案件文件类型" },
          { key: "system-parameters-ipr-case-file-type", label: "知识产权案件文件类型" },
          { key: "system-parameters-district", label: "地区设置" },
          { key: "system-parameters-court-officer", label: "法院工作人员" },
        ],
      },
      { key: "system-law-firms", label: "律所档案" },
      {
        key: "system-management",
        label: "系统管理",
        children: [
          { key: "system-management-cache", label: "缓存管理" },
          { key: "system-management-menu", label: "菜单管理" },
          { key: "system-management-config", label: "系统配置" },
        ],
      },
    ],
  },
  {
    key: "warehouse",
    icon: <FileTextOutlined />,
    label: "仓库管理",
    children: [{ key: "warehouse-list", label: "仓库一览表" }],
  },
  { key: "reports", icon: <DashboardOutlined />, label: "报表中心" },
];

function configuredMenuItems(rows: NavConfig[]): NavItem[] {
  if (!rows.length) return menuItems;
  const icon = (name: string) =>
    name === "dashboard" ? (
      <DashboardOutlined />
    ) : name === "robot" ? (
      <RobotOutlined />
    ) : name === "team" ? (
      <TeamOutlined />
    ) : name === "search" ? (
      <SearchOutlined />
    ) : name === "bank" ? (
      <BankOutlined />
    ) : name === "user" ? (
      <UserOutlined />
    ) : (
      <FileTextOutlined />
    );
  const ordered = rows.filter(
    (item) =>
      item.is_visible &&
      item.is_active &&
      item.key !== "task-reminders" &&
      item.key !== "system-users",
  ).sort(
    (a, b) => a.sort_order - b.sort_order || a.id - b.id,
  );
  const build = (parentKey: string): NavItem[] =>
    ordered
      .filter((item) => item.parent_key === parentKey)
      .map((item) => {
        const children = build(item.key);
        const linkUrl = item.link_url || item.LinkUrl || "";
        const menuTypeId = Number(item.menu_type_id ?? item.menu_type ?? item.MenuTypeId ?? 0);
        return {
          key: item.key,
          label: item.label,
          disabled: item.key.startsWith("legacy-menu-") && !linkUrl,
          link_url: linkUrl || undefined,
          menu_type_id: menuTypeId || undefined,
          open_target: item.open_target,
          icon: parentKey ? undefined : icon(item.icon),
          badge: item.key === "dashboard" ? "hot" : undefined,
          children: children.length ? children : undefined,
        };
      });
  const built = build("");
  const taskChildren = [
    { key: "investigation-task-mine", label: "我的调查任务" },
    { key: "investigation-task-overdue", label: "过期调查任务" },
  ];
  const investigationChildren: NavItem[] = [
    { key: "investigation-task-published", label: "我发布的调查任务", icon: <UnorderedListOutlined />, children: taskChildren },
    { key: "investigation-task-unassigned", label: "待我分配的调查任务", icon: <UnorderedListOutlined /> },
    { key: "investigation-task-sub-published", label: "我发布的调查子任务", icon: <UnorderedListOutlined /> },
    { key: "investigation-task-sub-mine", label: "我的调查任务", icon: <UnorderedListOutlined /> },
    {
      key: "clue",
      label: "我的调查线索",
      icon: <UnorderedListOutlined />,
      children: [
        { key: "clue-my-draft", label: "待提交线索" },
        { key: "clue-my-pending", label: "待审核线索" },
        { key: "clue-my-customer", label: "待客户审核" },
        { key: "clue-my-collect", label: "待取证线索" },
        { key: "clue-my-collected", label: "已取证线索" },
        { key: "clue-my-refused", label: "已拒绝线索" },
        { key: "clue-my-no-fee", label: "未申请费用线索" },
        { key: "clue-my-fee", label: "已申请费用线索" },
      ],
    },
    {
      key: "clue-audit",
      label: "调查线索审核",
      icon: <UnorderedListOutlined />,
      children: [
        { key: "clue-audit-pending", label: "待审批线索" },
        { key: "clue-audit-customer", label: "待客户审核" },
        { key: "clue-audit-refused", label: "已拒绝线索" },
        { key: "clue-audit-collect", label: "待取证线索" },
        { key: "clue-audit-collected", label: "已取证线索" },
      ],
    },
    {
      key: "clue-company",
      label: "公司调查线索",
      icon: <UnorderedListOutlined />,
      children: [
        { key: "clue-company-draft", label: "待提交线索" },
        { key: "clue-company-pending", label: "待审核线索" },
        { key: "clue-company-collect", label: "待取证线索" },
        { key: "clue-company-collected", label: "已取证线索" },
        { key: "clue-company-refused", label: "已拒绝线索" },
        { key: "clue-company-no-fee", label: "未申请费用线索" },
        { key: "clue-company-fee", label: "已申请费用线索" },
      ],
    },
    {
      key: "notary",
      label: "公证信息导入",
      icon: <UnorderedListOutlined />,
      children: [
        { key: "notary-import-info", label: "公证信息导入" },
        { key: "notary-import-storage", label: "取证信息文件导入" },
        { key: "notary-import-files", label: "公证书文件导入" },
        { key: "notary-import-invoices", label: "发票文件导入" },
      ],
    },
  ];
  const hasPublishedTaskRoute = ordered.some(
    (item) => item.key === "investigation-task-published",
  );
  if (!hasPublishedTaskRoute) return built;
  return built.map((item) => {
    if (item.key !== "investigation") return item;
    return {
      ...item,
      children: investigationChildren,
    };
  });
}

function flattenMenu(items: NavItem[]): NavItem[] {
  return items.flatMap((item) => [item, ...flattenMenu(item.children || [])]);
}
function menuKeysWithChildren(items: NavItem[]): string[] {
  return items.flatMap((item) =>
    item.children?.length
      ? [item.key, ...menuKeysWithChildren(item.children)]
      : [],
  );
}
function filterMenuByGrantedKeys(items: NavItem[], grantedKeys: Set<string>): NavItem[] {
  return items.flatMap((item) => {
    const children = filterMenuByGrantedKeys(item.children || [], grantedKeys);
    // A parent is retained only as a container for an authorized descendant.
    // It does not grant its own route unless the server returned that key in
    // the user's effective menu permissions.
    if (item.key !== "dashboard" && !grantedKeys.has(item.key) && !children.length) return [];
    return [{ ...item, ...(item.children ? { children } : {}) }];
  });
}
type RenderableMenuItem = Omit<NavItem, "label" | "children"> & { label: ReactNode; children?: RenderableMenuItem[] };

// Legacy sidebar double-click reloads the workspace page bound to the menu leaf.
function menuItemsWithDoubleClickReload(
  items: NavItem[],
  onReload: (item: NavItem) => void,
  depth = 0,
): RenderableMenuItem[] {
  return items.map((item) => {
    const children = item.children
      ? menuItemsWithDoubleClickReload(item.children, onReload, depth + 1)
      : undefined;
    return {
      ...item,
      icon: item.icon || (depth > 0 ? <UnorderedListOutlined /> : undefined),
      ...(children ? { children } : {}),
      label: children ? item.label : (
        <span
          onDoubleClick={(event) => {
            event.preventDefault();
            event.stopPropagation();
            if (item.link_url || item.disabled) return;
            onReload(item);
          }}
        >
          {item.label}
        </span>
      ),
    };
  });
}

function ancestorMenuKeys(
  items: NavItem[],
  target: string,
  path: string[] = [],
): string[] {
  for (const item of items) {
    if (item.key === target) return path;
    if (item.children) {
      const result = ancestorMenuKeys(item.children, target, [...path, item.key]);
      if (result.length) return result;
    }
  }
  return [];
}
export function normalizeOpenMenuKeys(
  items: NavItem[],
  currentKeys: string[],
  nextKeys: string[],
): string[] {
  const addedKey = nextKeys.find((key) => !currentKeys.includes(key));
  const focusKey = addedKey || nextKeys[nextKeys.length - 1] || "";
  if (!focusKey) return [];
  const focusPath = ancestorMenuKeys(items, focusKey);
  return [...focusPath, focusKey].filter((key) => nextKeys.includes(key));
}
export function routeForMenuOpenChange(
  currentKeys: string[],
  nextKeys: string[],
  activeRoute: string,
): string | null {
  const route = "system-parameters";
  const toggled = currentKeys.includes(route) !== nextKeys.includes(route);
  const alreadyInsideSection =
    activeRoute === route || activeRoute.startsWith(`${route}-`);
  return toggled && !alreadyInsideSection ? route : null;
}
function canonicalRoute(route: string): string {
  if (route.endsWith("-schedule") && route.startsWith("case-"))
    return "case-schedule";
  if (route.endsWith("-execution") && route.startsWith("case-"))
    return "case-execution";
  if (
    route.startsWith("investigation-task-published") ||
    route.startsWith("investigation-task-sub-published")
  )
    return "task-my-created";
  if (
    route.startsWith("investigation-task-mine") ||
    route.startsWith("investigation-task-sub-mine")
  )
    return "task-my-accepted";
  if (route === "investigation-task-overdue") return "task-reminders";
  if (route === "investigation-task-unassigned") return "task-company";
  if (route.startsWith("reports-")) return "reports";
  const prefixes = [
    "seal-my",
    "seal-audit",
    "seal-admin",
    "task-my",
    "task-dept",
    "task-company",
    "contract-audit",
    "contract-receivable",
    "case-new",
    "case-mine",
    "case-dept",
    "case-company",
    "case-archive",
    "clue",
    "notary",
    "evidence",
    "finance-fees",
    "finance-audit",
    "finance-receipts",
    "finance-invoice",
    "platform-finance-overview",
    "platform-finance-invoice",
  ];
  return prefixes.find((prefix) => route.startsWith(`${prefix}-`)) || route;
}

function financeRouteFromPlatform(route: string): string {
  const roots: Record<string, string> = {
    "platform-finance-overview": "finance-receipts-manage",
    "platform-finance-payment": "finance-payment-mine",
    "platform-finance-invoice": "finance-invoice-company",
    "platform-finance-settlement": "finance-settlement-pending",
    "platform-finance-archive-fee": "finance-archive-fee-pending",
    "platform-finance-fee-query": "finance-fee-query",
  };
  if (roots[route]) return roots[route];
  return route
    .replace("platform-finance-overview-", "finance-receipts-")
    .replace("platform-finance-payment-", "finance-payment-")
    .replace("platform-finance-invoice-", "finance-invoice-")
    .replace("platform-finance-settlement-", "finance-settlement-")
    .replace("platform-finance-archive-fee-", "finance-archive-fee-");
}

const supportTools = [
  {
    label: "国家知识产权局商标局",
    href: "http://wcjs.sbj.cnipa.gov.cn/txnT01.do",
  },
  {
    label: "国家知识产权局专利局",
    href: "http://pss-system.cnipa.gov.cn/sipopublicsearch/portal/uiIndex.shtml",
  },
  { label: "全国组织机构查询平台", href: "https://www.cods.org.cn" },
  { label: "法律法规查询", href: "https://flk.npc.gov.cn/" },
  { label: "裁判文书检索", href: "https://openlaw.cn/index.jsp" },
];

type DashboardData = {
  metrics: { key: string; label: string; value: string; tone: string; route: string }[];
  todos: (string | number)[][];
  hearings: Record<string, string>[];
  latest_cases: Record<string, string>[];
  case_trend: { date: string; value: number }[];
  civil_distribution: { label: string; value: number; color: string }[];
};
type SessionUser = {
  username: string;
  display_name: string;
  department?: string;
  role: string;
  menu_keys?: string[];
  data_scope?: string;
  must_change_password?: boolean;
};
type OpenPage = { key: string; label: string };

// Deep routes are not all navigation-menu leaves. Keep workspace tabs readable
// instead of exposing an internal route key to users.
const legacyRouteAliases: Record<string, string> = {
  "agent-document": "documents-agent",
  "system-users": "hr-all",
};
const normalizeWorkspaceRoute = (route: string) => legacyRouteAliases[route] || route;
const businessNavigationSessionKeys = [
  "sunhold:case-detail-context",
  "sunhold:contract-detail-context",
  "sunhold:customer-detail-context",
  "sunhold:customer-relation-context",
  "sunhold:investigation-detail-context",
  "sunhold:task-detail-context",
  "sunhold:contract-customer",
  "sunhold:case-contract-context",
  "sunhold:business-record-detail-context",
  "sunhold:document-search-detail-context",
];

function clearClientSessionStorage() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
  localStorage.removeItem("sunhold:open-pages");
  localStorage.removeItem("sunhold:last-page");
  businessNavigationSessionKeys.forEach((key) => sessionStorage.removeItem(key));
}

function replaceWithRootRoute() {
  window.history.replaceState(null, "", window.location.pathname);
}
const routePageLabels: Record<string, string> = {
  "system-audit": "操作日志",
  "contract-approver-settings": "审批关系",
  "documents-agent": "AI 智能文档",
  "notary-import-info": "公证信息导入",
  "notary-import-storage": "取证信息文件导入",
  "notary-import-files": "公证书文件导入",
  "notary-import-invoices": "发票文件导入",
  "notary-query-files": "公证书文件列表",
};

function resolveWorkspacePageLabel(key: string, items: NavItem[] = menuItems): string {
  const normalizedKey = normalizeWorkspaceRoute(key);
  if (normalizedKey === "dashboard") return "控制台";
  if (normalizedKey.startsWith("case-new-")) return "新建案件";
  if (normalizedKey.startsWith("case-detail-")) {
    const match = normalizedKey.match(/^case-detail-\d+-(.+)$/);
    if (match?.[1]) {
      try {
        return decodeURIComponent(match[1]);
      } catch {
        return match[1];
      }
    }
    return "案件详情";
  }
  if (normalizedKey.startsWith("contract-detail-")) {
    const match = normalizedKey.match(/^contract-detail-\d+-(.+)$/);
    if (match?.[1]) {
      try {
        return decodeURIComponent(match[1]);
      } catch {
        return match[1];
      }
    }
    return "合同详情";
  }
  const menuLabel = flattenMenu(items).find((item) => item.key === normalizedKey)?.label;
  return menuLabel || routePageLabels[normalizedKey] || "业务页面";
}

function readWorkspaceRouteFromLocation() {
  const requestedRoute = new URLSearchParams(window.location.search).get("page");
  if (requestedRoute) return normalizeWorkspaceRoute(requestedRoute);
  try {
    return normalizeWorkspaceRoute(localStorage.getItem("sunhold:last-page") || "dashboard");
  } catch {
    return "dashboard";
  }
}

function readOpenPages(active: string): OpenPage[] {
  try {
    const stored = JSON.parse(localStorage.getItem("sunhold:open-pages") || "[]") as OpenPage[];
    const valid = Array.from(new Map(
      stored
        .filter((item) => item?.key && item?.label)
        .map((item) => {
          const key = normalizeWorkspaceRoute(item.key);
          return [key, { key, label: resolveWorkspacePageLabel(key) }];
        }),
    ).values());
    if (valid.some((item) => item.key === active)) return valid;
    return [...valid, { key: active, label: resolveWorkspacePageLabel(active) }];
  } catch {
    return [{ key: active, label: resolveWorkspacePageLabel(active) }];
  }
}

function readStoredUser(): SessionUser | null {
  try {
    return JSON.parse(
      localStorage.getItem("user") || "null",
    ) as SessionUser | null;
  } catch {
    return null;
  }
}

function Login({ onSuccess }: { onSuccess: (user: SessionUser) => void }) {
  const [loading, setLoading] = useState(false);
  const [dingtalkEnabled, setDingtalkEnabled] = useState(false);
  const [dingtalkAuthCode, setDingtalkAuthCode] = useState("");
  const [installPrompt, setInstallPrompt] = useState<Event | null>(null);
  const [pendingUser, setPendingUser] = useState<SessionUser | null>(null);
  const [passwordForm] = Form.useForm();
  useEffect(() => {
    const rememberInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event);
    };
    window.addEventListener("beforeinstallprompt", rememberInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", rememberInstallPrompt);
  }, []);
  useEffect(() => {
    let active = true;
    const loginFromDingTalk = async () => {
      try {
        const { data: config } = await api.get("/auth/dingtalk/config");
        if (!active || !config.enabled) return;
        setDingtalkEnabled(true);
        if (getDingTalkEnvironment().platform === "notInDingTalk") return;
        setLoading(true);
        const result = await requestDingTalkAuthCode({ corpId: config.corp_id });
        const { data } = await api.post("/auth/dingtalk/login", { auth_code: result.code });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        if (active) onSuccess(data.user);
      } catch (error: any) {
        if (active && error?.response?.status === 403 && error?.config?.data) {
          try { setDingtalkAuthCode(JSON.parse(error.config.data).auth_code || ""); } catch { setDingtalkAuthCode(""); }
          message.info("首次使用钉钉登录，请输入一次现有 OA 账号和密码完成绑定");
        } else if (active && getDingTalkEnvironment().platform !== "notInDingTalk") {
          message.error(error?.response?.data?.detail || "钉钉免登失败，请联系管理员检查账号绑定");
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    void loginFromDingTalk();
    return () => { active = false; };
  }, [onSuccess]);
  const submit = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const form = new URLSearchParams(values);
      let data: any;
      if (dingtalkAuthCode) {
        // DingTalk auth codes are single-use. The initial SSO probe consumes its
        // code before an unbound user reaches this form, so binding needs a new one.
        const { data: config } = await api.get("/auth/dingtalk/config");
        const result = await requestDingTalkAuthCode({ corpId: config.corp_id });
        ({ data } = await api.post("/auth/dingtalk/bind", { ...values, auth_code: result.code }));
      } else {
        ({ data } = await api.post("/auth/login", form));
      }
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      if (data.must_change_password) {
        setPendingUser(data.user);
        passwordForm.resetFields();
        message.warning("首次登录必须修改一次性初始密码");
      } else {
        onSuccess(data.user);
      }
    } catch (error: any) {
        message.error(error?.response?.data?.detail || "账号或密码错误");
    } finally {
      setLoading(false);
    }
  };
  const forcePasswordChange = async () => {
    const values = await passwordForm.validateFields();
    setLoading(true);
    try {
      const { data } = await api.patch("/auth/me", { current_password: values.current_password, new_password: values.new_password });
      const user = { ...pendingUser, ...data, must_change_password: false } as SessionUser;
      localStorage.setItem("user", JSON.stringify(user));
      setPendingUser(null);
      message.success("初始密码已更换，请妥善保管新密码");
      onSuccess(user);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "密码修改失败");
    } finally {
      setLoading(false);
    }
  };
  const installExternalApp = async () => {
    const prompt = installPrompt as (Event & {
      prompt?: () => Promise<void>;
      userChoice?: Promise<{ outcome: string }>;
    }) | null;
    if (!prompt?.prompt) {
      message.info("请打开浏览器菜单，选择“添加到主屏幕”或“安装应用”");
      return;
    }
    await prompt.prompt();
    await prompt.userChoice;
    setInstallPrompt(null);
  };
  return (
    <div className="login-page">
      <div className="login-brand">
        <b>Sunhold</b>
        <span>法律服务机构管理系统</span>
      </div>
      <Card className="login-card">
        <h2>系统登录</h2>
        <p>欢迎进入思法汇成协作平台</p>
        {dingtalkAuthCode && <Alert type="info" showIcon title="首次钉钉登录" description="输入一次现有 OA 账号和密码完成绑定；以后从钉钉工作台打开将直接登录。" style={{marginBottom:16}} />}
        <Form
          onFinish={submit}
          layout="vertical"
        >
          <Form.Item name="username" label="账号" rules={[{ required: true }]}>
            <Input size="large" prefix={<UserOutlined />} />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password size="large" />
          </Form.Item>
          <Button
            block
            size="large"
            type="primary"
            htmlType="submit"
            loading={loading}
          >
            {dingtalkAuthCode ? "绑定钉钉并登录" : "登 录"}
          </Button>
          {dingtalkEnabled && getDingTalkEnvironment().platform === "notInDingTalk" && (
            <Button block size="large" style={{ marginTop: 12 }} onClick={() => message.info("请从钉钉工作台打开本系统，即可自动登录")}>钉钉免登</Button>
          )}
          {getDingTalkEnvironment().platform === "notInDingTalk" && (
            <Button
              block
              size="large"
              icon={<DownloadOutlined />}
              style={{ marginTop: 12 }}
              onClick={() => void installExternalApp()}
            >
              安装到手机桌面
            </Button>
          )}
        </Form>
      </Card>
      <Modal open={Boolean(pendingUser)} title="首次登录修改密码" closable={false} maskClosable={false} keyboard={false} okText="修改密码并进入系统" cancelButtonProps={{style:{display:"none"}}} confirmLoading={loading} onOk={forcePasswordChange}>
        <Alert type="warning" showIcon title="当前密码是一次性初始密码，修改前不能进入任何业务页面。" style={{marginBottom:16}} />
        <Form form={passwordForm} layout="vertical">
          <Form.Item name="current_password" label="当前初始密码" rules={[{required:true,message:"请输入当前初始密码"}]}><Input.Password autoComplete="current-password" /></Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{required:true,min:8,message:"新密码至少 8 位"}]}><Input.Password autoComplete="new-password" /></Form.Item>
          <Form.Item name="confirm_password" label="确认新密码" dependencies={["new_password"]} rules={[{required:true,message:"请再次输入新密码"},({getFieldValue})=>({validator(_,value){return !value||getFieldValue("new_password")===value?Promise.resolve():Promise.reject(new Error("两次输入的新密码不一致"))}})]}><Input.Password autoComplete="new-password" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

function CaseTrendChart({
  items,
}: {
  items: { date: string; value: number }[];
}) {
  const width = 470,
    height = 220,
    left = 38,
    right = 12,
    top = 12,
    bottom = 52,
    plotWidth = width - left - right,
    plotHeight = height - top - bottom,
    maxValue = Math.max(1, ...items.map((item) => item.value)),
    max = Math.max(5, Math.ceil(maxValue / 5) * 5),
    ticks = Array.from({ length: 5 }, (_, index) => Math.round((max * index) / 4));
  const points = items
    .map(
      (item, index) =>
        `${left + (items.length === 1 ? 0 : (index * plotWidth) / (items.length - 1))},${top + plotHeight - (item.value / max) * plotHeight}`,
    )
    .join(" ");
  return (
    <svg
      className="case-trend-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="案件趋势折线图"
    >
      {ticks.map((value) => {
        const y = top + plotHeight - (value / max) * plotHeight;
        return (
          <g key={value}>
            <line
              x1={left}
              y1={y}
              x2={width - right}
              y2={y}
              className="trend-grid-line"
            />
            <text
              x={left - 8}
              y={y + 4}
              textAnchor="end"
              className="trend-axis-text"
            >
              {value}
            </text>
          </g>
        );
      })}
      {items.map((item, index) => {
        const x =
          left +
          (items.length === 1 ? 0 : (index * plotWidth) / (items.length - 1));
        return (
          <line
            key={item.date}
            x1={x}
            y1={top}
            x2={x}
            y2={top + plotHeight}
            className="trend-grid-line vertical"
          />
        );
      })}
      <polyline points={points} className="trend-line" />
      {items.map((item, index) => {
        const x =
            left +
            (items.length === 1 ? 0 : (index * plotWidth) / (items.length - 1)),
          y = top + plotHeight - (item.value / max) * plotHeight;
        return (
          <g key={`${item.date}-point`}>
            <circle cx={x} cy={y} r="3.5" className="trend-point" />
            <text
              transform={`translate(${x - 2} ${height - 38}) rotate(-45)`}
              textAnchor="end"
              className="trend-date-text"
            >
              {item.date}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function CivilDistribution({
  items,
}: {
  items: { label: string; value: number; color: string }[];
}) {
  const total = items.reduce((sum, item) => sum + item.value, 0) || 1;
  let cursor = 0;
  const gradient = items
    .map((item) => {
      const start = (cursor / total) * 360;
      cursor += item.value;
      const end = (cursor / total) * 360;
      return `${item.color} ${start}deg ${end}deg`;
    })
    .join(",");
  return (
    <div className="civil-distribution">
      <div
        className="donut-chart"
        style={{ background: `conic-gradient(${gradient})` }}
      >
        <div className="donut-hole" />
      </div>
      <div className="donut-legend">
        {items.map((item) => (
          <span key={item.label}>
            <i style={{ background: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function Dashboard({ onNavigate }: { onNavigate: (route: string) => void }) {
  const [data, setData] = useState<DashboardData | null>(null);
  useEffect(() => {
    let active = true;
    const loadDashboard = () => {
      api
        .get("/dashboard")
        .then((r) => active && setData(r.data))
        .catch(() => active && message.error("看板加载失败"));
    };
    const refreshOnFocus = () => loadDashboard();
    loadDashboard();
    const timer = window.setInterval(loadDashboard, 30_000);
    window.addEventListener("focus", refreshOnFocus);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshOnFocus);
    };
  }, []);
  const todoRoutes: Record<string, string> = {
    待处理任务: "task-my",
    待审批官方费用: "finance-payment-audit",
    待审批线索: "clue",
    待审批内部费用: "finance-internal-fee-audit",
    待审批合同: "contract-audit",
    待审批结算费用: "finance-settlement-audit",
    待审批用印: "seal-audit",
    待审批归档费用: "finance-archive-fee-pending",
    待审核归档: "case-archive",
    待审核预损费用: "finance-internal-fee-audit",
  };
  const keyboardNavigate = (event: React.KeyboardEvent, route: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onNavigate(route);
    }
  };
  const openDashboardCase = (caseNo: string) => {
    rememberCaseDetailTarget({ serial_no: caseNo });
    onNavigate("case-company");
  };
  const openDashboardCustomer = (customer: string) => {
    rememberCustomerDetailTarget({ title: customer });
    onNavigate("customer-company");
  };
  const hearingCols = useMemo(
    () => [
      { title: "星期", dataIndex: "weekday", width: 80 },
      { title: "日期", dataIndex: "date", width: 100 },
      { title: "时间", dataIndex: "time", width: 90 },
      { title: "开庭法院", dataIndex: "court", ellipsis: true },
      {
        title: "案号",
        dataIndex: "case_no",
        width: 140,
        render: (v: string) => (
          <a onClick={() => openDashboardCase(v)}>{v}</a>
        ),
      },
      {
        title: "客户",
        dataIndex: "client",
        ellipsis: true,
        render: (value: string) =>
          value ? <a onClick={() => openDashboardCustomer(value)}>{value}</a> : "—",
      },
      {
        title: "开庭律师",
        dataIndex: "lawyer",
        width: 105,
        render: (v: string) => <span>{v}</span>,
      },
      {
        title: "经办律师",
        dataIndex: "agent",
        width: 115,
        render: (v: string) => <span>{v}</span>,
      },
      { title: "律师助理", dataIndex: "assistant", width: 105 },
    ],
    [],
  );
  const latestCaseCols = useMemo(
    () => [
      {
        title: "案号",
        dataIndex: "case_no",
        width: 125,
        render: (v: string) => (
          <a onClick={() => openDashboardCase(v)}>{v}</a>
        ),
      },
      { title: "阶段", dataIndex: "stage", width: 100 },
      { title: "原告", dataIndex: "plaintiff", width: 185, ellipsis: true },
      { title: "被告", dataIndex: "defendant", width: 205, ellipsis: true },
      { title: "案源日期", dataIndex: "date", width: 100 },
      { title: "客户管理人", dataIndex: "manager", width: 90 },
      { title: "开庭律师", dataIndex: "lawyer", width: 85 },
      { title: "经办律师", dataIndex: "agent", width: 100, ellipsis: true },
      { title: "律师助理", dataIndex: "assistant", width: 85 },
    ],
    [],
  );
  if (!data) return <div className="loading">正在加载...</div>;
  return (
    <div className="reference-dashboard">
      <div className="dashboard-top-grid">
        <div className="metrics reference-metrics">
          {data.metrics.map((m, i) => (
            <div
              className={`metric target-${i}`}
              key={m.key}
              role="button"
              tabIndex={0}
              onClick={() => onNavigate(m.route)}
              onKeyDown={(event) => keyboardNavigate(event, m.route)}
            >
              <div className="metric-icon">
                {["◷", "✉", "♟", "⚖", "⚑", "▤", "☕", "¥"][i]}
              </div>
              <div>
                <strong>{m.value}</strong>
                <span>{m.label}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="dashboard-split-row dashboard-todo-trend-row">
        <Card title="➤ 待办事项" className="dashboard-card compact-todo-card">
          <table className="todo-table">
            <tbody>
              {data.todos.map((row, i) => (
                <tr key={i}>
                  {row.map((c, j) => {
                    const route =
                      todoRoutes[String(row[j < 3 ? 0 : 3])] || "dashboard";
                    return (
                      <td
                        key={j}
                        className={
                          typeof c === "number" ? `count count-${j % 3}` : ""
                        }
                      >
                        <button
                          type="button"
                          className="todo-link"
                          onClick={() => onNavigate(route)}
                        >
                          {c}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mobile-todo-list">
            {data.todos.flatMap((row, rowIndex) =>
              [
                { label: row[0], primary: row[1], secondary: row[2] },
                { label: row[3], primary: row[4], secondary: row[5] },
              ].map((item, itemIndex) => {
                const route = todoRoutes[String(item.label)] || "dashboard";
                return (
                  <button
                    type="button"
                    className="mobile-todo-item"
                    key={`${rowIndex}-${itemIndex}`}
                    onClick={() => onNavigate(route)}
                  >
                    <span>{item.label}</span>
                    <strong>{item.primary}</strong>
                    <small>{item.secondary}</small>
                  </button>
                );
              }),
            )}
          </div>
        </Card>
        <Card title="◩ 案件趋势" className="dashboard-card target-trend-card">
          <CaseTrendChart items={data.case_trend} />
        </Card>
      </div>
      <Card title="▥ 开庭排期" className="dashboard-card target-hearing-card dashboard-full-row-card">
        <Table
          rowKey={(r) => `${r.case_no}-${r.time}`}
          size="small"
          pagination={false}
          columns={hearingCols}
          dataSource={data.hearings}
          scroll={{ x: 1050 }}
        />
      </Card>
      <div className="dashboard-split-row latest-row">
        <Card title="◉ 最新案件" className="dashboard-card latest-cases-card">
          <Table
            rowKey="case_no"
            size="small"
            pagination={false}
            columns={latestCaseCols}
            dataSource={data.latest_cases}
            scroll={{ x: 1100 }}
          />
        </Card>
        <Card title="◔ 民事案件" className="dashboard-card civil-card">
          <CivilDistribution items={data.civil_distribution} />
        </Card>
      </div>
    </div>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(
    Boolean(localStorage.getItem("access_token")),
  );
  const [sessionUser, setSessionUser] = useState<SessionUser | null>(
    readStoredUser,
  );
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("sunhold:sidebar-auto-collapse") === "yes",
  );
  const routeFromLocation = readWorkspaceRouteFromLocation;
  const [active, setActive] = useState(routeFromLocation);
  const [contractDetailTarget, setContractDetailTarget] = useState<ContractDetailNavigationContext | null>(null);
  const [openPages, setOpenPages] = useState<OpenPage[]>(() => readOpenPages(routeFromLocation()));
  const [workspaceReloadKey, setWorkspaceReloadKey] = useState(0);
  const [sidebarHoverExpanded, setSidebarHoverExpanded] = useState(false);
  const [isNarrowViewport, setIsNarrowViewport] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [menuConfig, setMenuConfig] = useState<NavConfig[]>([]);
  const [openMenuKeys, setOpenMenuKeys] = useState<string[]>([]);
  const [isFullscreen, setIsFullscreen] = useState(() => Boolean(document.fullscreenElement));
  const [caseQuickKeyword, setCaseQuickKeyword] = useState("");
  const [taskUnreadCount, setTaskUnreadCount] = useState(0);
  const sidebarCollapsed = isNarrowViewport
    ? !mobileSidebarOpen
    : collapsed && !sidebarHoverExpanded;
  const resetWorkspaceForSession = () => {
    const dashboard = [{ key: "dashboard", label: "控制台" }];
    setContractDetailTarget(null);
    setOpenMenuKeys([]);
    setOpenPages(dashboard);
    setActive("dashboard");
  };
  const endClientSession = () => {
    clearClientSessionStorage();
    clearContractDetailTarget();
    setLoggedIn(false);
    setSessionUser(null);
    resetWorkspaceForSession();
    replaceWithRootRoute();
  };
  useEffect(() => {
    const restoreRouteFromHistory = () => {
      setActive(routeFromLocation());
    };
    window.addEventListener("popstate", restoreRouteFromHistory);
    return () => window.removeEventListener("popstate", restoreRouteFromHistory);
  }, []);
  useEffect(() => {
    if (!loggedIn) return;
    localStorage.setItem("sunhold:last-page", active);
  }, [active, loggedIn]);
  useEffect(() => {
    const syncFullscreenState = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", syncFullscreenState);
    return () => document.removeEventListener("fullscreenchange", syncFullscreenState);
  }, []);
  useEffect(() => {
    const receiveContractDetailTarget = (event: Event) => {
      const target = (event as CustomEvent<ContractDetailNavigationContext>).detail;
      if (target?.id || target?.serial_no) setContractDetailTarget(target);
    };
    window.addEventListener(CONTRACT_DETAIL_TARGET_EVENT, receiveContractDetailTarget);
    return () => window.removeEventListener(CONTRACT_DETAIL_TARGET_EVENT, receiveContractDetailTarget);
  }, []);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const routeFromUrl = params.get("page") || "dashboard";
    if (routeFromUrl === active) return;
    if (active === "dashboard") params.delete("page");
    else params.set("page", active);
    const query = params.toString();
    window.history.pushState(
      null,
      "",
      `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`,
    );
  }, [active]);
  useEffect(() => {
    const expired = () => {
      endClientSession();
      message.warning("登录状态已过期，请重新登录");
    };
    const synchronizeLogout = (event: StorageEvent) => {
      if (event.storageArea === localStorage && event.key === "access_token" && !event.newValue) {
        endClientSession();
      }
    };
    const profileUpdated = () => setSessionUser(readStoredUser());
    const preferencesUpdated = (event: Event) => {
      const detail = (event as CustomEvent<{ auto_collapse?: string }>).detail;
      if (detail?.auto_collapse) setCollapsed(detail.auto_collapse === "yes");
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, expired);
    window.addEventListener("storage", synchronizeLogout);
    window.addEventListener("sunhold:profile-updated", profileUpdated);
    window.addEventListener("sunhold:preferences-updated", preferencesUpdated);
    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, expired);
      window.removeEventListener("storage", synchronizeLogout);
      window.removeEventListener("sunhold:profile-updated", profileUpdated);
      window.removeEventListener(
        "sunhold:preferences-updated",
        preferencesUpdated,
      );
    };
  }, []);
  useEffect(() => {
    if (!loggedIn) return;
    api
      .get("/auth/me")
      .then(({ data }) => {
        const user = {
          username: data.username,
          display_name: data.display_name,
          department: data.department,
          role: data.role,
          menu_keys: data.menu_keys,
          data_scope: data.data_scope,
          must_change_password: data.must_change_password,
        };
        localStorage.setItem("user", JSON.stringify(user));
        if (data.must_change_password) {
          // A page refresh must never leave the already-mounted workspace
          // visible after the API reports that this account is still using an
          // administrator-issued one-time password.
          clearClientSessionStorage();
          setLoggedIn(false);
          setSessionUser(null);
          resetWorkspaceForSession();
          replaceWithRootRoute();
          message.warning("请重新登录并修改一次性初始密码后再进入系统");
          return;
        }
        setSessionUser(user);
        if (data.menu_auto_collapse === "yes" || data.menu_auto_collapse === "no") {
          localStorage.setItem(
            "sunhold:sidebar-auto-collapse",
            data.menu_auto_collapse,
          );
          setCollapsed(data.menu_auto_collapse === "yes");
        }
      })
      .catch(() => undefined);
  }, [loggedIn]);
  useEffect(() => {
    if (!loggedIn) return;
    const loadMenus = () =>
      api
        .get("/system/menus/navigation")
        .then(({ data }) => setMenuConfig(data.items))
        .catch(() => setMenuConfig([]));
    loadMenus();
    window.addEventListener("sunhold:menus-updated", loadMenus);
    return () => window.removeEventListener("sunhold:menus-updated", loadMenus);
  }, [loggedIn]);
  useEffect(() => {
    if (!loggedIn) return;
    const loadTaskUnread = () =>
      api
        .get("/tasks/unread-messages")
        .then(({ data }) =>
          setTaskUnreadCount(Number(data?.unread_messages ?? data?.total ?? 0)),
        )
        .catch(() => undefined);
    loadTaskUnread();
    const timer = window.setInterval(loadTaskUnread, 30000);
    return () => window.clearInterval(timer);
  }, [loggedIn]);
  const effectiveMenuItems = useMemo(
    () => configuredMenuItems(menuConfig),
    [menuConfig],
  );
  useEffect(() => {
    if (!loggedIn) return;
    document.title = resolveWorkspacePageLabel(active, effectiveMenuItems);
  }, [active, effectiveMenuItems, loggedIn]);
  const navigate = (route: string) => {
    const normalizedRoute = normalizeWorkspaceRoute(route);
    if (normalizedRoute === "contract-new") {
      if (sessionStorage.getItem(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY) !== "customer") {
        clearContractCustomerContext(sessionStorage);
        sessionStorage.removeItem(CONTRACT_CUSTOMER_ROUTE_SOURCE_KEY);
      }
    }
    if (normalizedRoute === active) window.dispatchEvent(new CustomEvent("sunhold:route-reselect", { detail: normalizedRoute }));
    setActive(normalizedRoute);
  };
  const openLegacyMenuItem = (item: NavItem) => {
    const rawUrl = String(item.link_url || "").trim();
    if (!rawUrl) return;
    const target = item.open_target || (item.menu_type_id === 4 ? "_blank" : "_self");
    if (/^https?:\/\//i.test(rawUrl)) {
      window.open(rawUrl, target, "noopener,noreferrer");
      return;
    }
    const url = rawUrl.startsWith("/") ? rawUrl : `/${rawUrl.replace(/^\/+/, "")}`;
    if (target === "_blank") window.open(url, target, "noopener,noreferrer");
    else window.location.assign(url);
  };
  useEffect(() => {
    const effectiveLabel = resolveWorkspacePageLabel(active, effectiveMenuItems);
    setOpenPages((current) => {
      const normalized = Array.from(new Map(current.map((entry) => {
        const key = normalizeWorkspaceRoute(entry.key);
        return [key, { key, label: resolveWorkspacePageLabel(key, effectiveMenuItems) }];
      })).values());
      const next = normalized.some((entry) => entry.key === active)
        ? normalized
        : [...normalized, { key: active, label: effectiveLabel }];
      if (
        next.length === current.length &&
        next.every((entry, index) => entry.key === current[index]?.key && entry.label === current[index]?.label)
      ) return current;
      localStorage.setItem("sunhold:open-pages", JSON.stringify(next));
      return next;
    });
  }, [active, effectiveMenuItems]);
  const closeOpenPage = (target: string) => {
    setOpenPages((current) => {
      if (current.length <= 1) return current;
      const index = current.findIndex((entry) => entry.key === target);
      const next = current.filter((entry) => entry.key !== target);
      localStorage.setItem("sunhold:open-pages", JSON.stringify(next));
      if (target === active) setActive(next[Math.max(0, index - 1)]?.key || "dashboard");
      return next;
    });
  };
  useEffect(() => {
    const ancestors = ancestorMenuKeys(effectiveMenuItems, active);
    setOpenMenuKeys(ancestors);
  }, [active, effectiveMenuItems]);
  const logout = () => {
    endClientSession();
  };
  if (new URLSearchParams(window.location.search).get("page") === "customer-portal")
    return <PageLoadBoundary><Suspense fallback={<div className="page-loading">加载客户服务端…</div>}><CustomerPortalPage /></Suspense></PageLoadBoundary>;
  if (!loggedIn)
    return (
      <Login
        onSuccess={(user) => {
          setSessionUser(user);
          resetWorkspaceForSession();
          setLoggedIn(true);
        }}
      />
  );
  const currentPageLabel = resolveWorkspacePageLabel(active, effectiveMenuItems);
  const navigationMenuKeys = flattenMenu(effectiveMenuItems).map((item) => item.key);
  const grantedMenuKeys = new Set(
    sessionUser?.role === "admin"
      ? navigationMenuKeys
      : ["user-center", ...(sessionUser?.menu_keys || [])],
  );
  const sideMenuItems = filterMenuByGrantedKeys(effectiveMenuItems, grantedMenuKeys);
  const sidebarReloadableItems = menuItemsWithDoubleClickReload(sideMenuItems, (item) => {
    setActive(String(item.key));
    setWorkspaceReloadKey((value) => value + 1);
  });
  const accountProfileRoute = grantedMenuKeys.has("user-account") ? "user-account" : "user-center";
  const runCaseQuickSearch = (value: string) => {
    const keyword = value.trim();
    if (!keyword) return;
    const target = ["case-company", "case-dept", "case-mine"].find((route) =>
      grantedMenuKeys.has(route),
    );
    if (!target) {
      message.error("当前角色没有案件列表菜单权限");
      return;
    }
    sessionStorage.setItem(
      "sunhold:case-list-return",
      JSON.stringify({ route: target, query: { keyword } }),
    );
    navigate(target);
  };
  const route = canonicalRoute(active);
  const pageAllowed =
    sessionUser?.role === "admin" ||
    route === "dashboard" ||
    (active.startsWith("case-detail-") &&
      Array.from(grantedMenuKeys).some((key) =>
        key.startsWith("case-mine") ||
        key.startsWith("case-dept") ||
        key.startsWith("case-company") ||
        key.startsWith("case-archive")
      )) ||
    (active.startsWith("contract-detail-") &&
      Array.from(grantedMenuKeys).some((key) => key.startsWith("contract-"))) ||
    // Leaf menus are independently grantable.  A canonical route can collapse
    // a leaf such as task-my-accepted to its container task-my for component
    // selection, but that must not discard the explicit leaf grant.
    grantedMenuKeys.has(active) ||
    grantedMenuKeys.has(route);
  const requestedPage =
    route === "dashboard" ? (
      <Dashboard onNavigate={navigate} />
    ) : route === "agent-center" ? (
      <AgentCenterPage />
    ) : route.startsWith("seal-") ? (
      <SealCenterPage initialView={active} onNavigate={navigate} />
    ) : route === "customer-conflict" ? (
      <CustomerConflictPage />
    ) : route.startsWith("customer-") ? (
      <CustomerCenterPage initialView={route} onNavigate={navigate} />
    ) : route === "system-law-firms" ? (
      <LawFirmPage />
    ) : route === "system-audit" ? (
      <AuditLogPage onNavigate={navigate} />
    ) : route === "system-parameters-ipr-case-file-type" ? (
      <IprFileTypeSettingsPage />
    ) : route.startsWith("system-") ? (
      <SystemCenterPage initialView={route} />
    ) : route === "contract-receivable" ? (
      <ContractReceivablesPage initialView={active} onNavigate={navigate} />
    ) : route.startsWith("contract-") ? (
      <ContractCenterPage
        initialView={active}
        onNavigate={navigate}
        detailTarget={contractDetailTarget}
        onDetailTargetHandled={() => {
          clearContractDetailTarget();
          setContractDetailTarget(null);
        }}
      />
    ) : active.startsWith("investigation-task-") || route.startsWith("clue-") || route.startsWith("notary-") || ["investigation", "clue", "notary", "evidence"].includes(route) ? (
      <InvestigationCenterPage initialTab={active} onNavigate={navigate} />
    ) : route === "ipr-office-files" ? (
      <IprOfficialFilePage />
    ) : route === "ipr-custom-file-import" ? (
      <IprCustomFileImportPage />
    ) : route.startsWith("ipr-") ? (
      <IprCenterPage initialView={active} onNavigate={navigate} />
    ) : route.startsWith("case-") ? (
      <CaseCenterPage initialView={active} onNavigate={navigate} />
    ) : route === "affairs-records" ? (
      <BusinessPage module="task" title="事项记录" onNavigate={navigate} />
    ) : route.startsWith("task-") ? (
      <TaskCenterPage initialView={active} onNavigate={navigate} />
    ) : route === "documents-agent" ? (
      <AgentDocumentPage onNavigate={navigate} />
    ) : route.startsWith("documents-") ? (
      <DocumentCenterPage initialView={route} onNavigate={navigate} />
    ) : route.startsWith("platform-finance-") ? (
      <FinanceCenterPage
        initialView={financeRouteFromPlatform(active)}
        platformMode
        onNavigate={navigate}
      />
    ) : route === "user-messages" ? (
      <MessageCenterPage />
    ) : route === "user-communications" ? (
      <CommunicationLogPage onNavigate={navigate} />
    ) : ["user-center", "user-account"].includes(route) ? (
      <UserCenterPage />
    ) : route.startsWith("finance-") ? (
      <FinanceCenterPage initialView={active} onNavigate={navigate} />
    ) : ["hr-departments", "hr-roles"].includes(route) ? (
      <OrganizationCenterPage initialView={route} />
    ) : route.startsWith("hr-") ? (
      <HrCenterPage initialView={route} />
    ) : route.startsWith("warehouse") ? (
      <WarehousePage onNavigate={navigate} />
    ) : route === "reports" ? (
      <ReportCenterPage initialView={active} />
    ) : (
      <Card className="panel">
        <div className="placeholder">页面不存在，请从左侧菜单重新选择。</div>
      </Card>
    );
  const currentPage = pageAllowed ? (
    requestedPage
  ) : (
    <Card className="panel">
      <div className="placeholder">
        <h2>无权访问</h2>
        <p>当前角色没有该功能的菜单权限，请联系系统管理员。</p>
        <Button type="primary" onClick={() => setActive("dashboard")}>
          返回控制台
        </Button>
      </div>
    </Card>
  );
  return (
    <Layout className="app-shell">
      <Header className="topbar">
        <div
          className={`logo ${collapsed ? "logo-collapsed" : ""}`}
          role="button"
          tabIndex={0}
          onClick={() => navigate("dashboard")}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              navigate("dashboard");
            }
          }}
        >
          {collapsed ? "S" : "Sunhold"}
        </div>
        <Button
          className="sidebar-toggle"
          type="text"
          aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
          title={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
          icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={() => {
            if (isNarrowViewport) {
              setMobileSidebarOpen((open) => !open);
              return;
            }
            setCollapsed((v) => !v);
          }}
        />
        <div className="mobile-top-title" aria-live="polite">
          {currentPageLabel}
        </div>
        <div className="global-search">
          <GlobalSearch
            onNavigate={navigate}
            menuItems={sideMenuItems}
            onOpenMenu={(item) => {
              if (item.link_url) {
                openLegacyMenuItem(item);
                return;
              }
              navigate(item.key);
            }}
          />
        </div>
        <Input.Search
          className="case-quick-search"
          value={caseQuickKeyword}
          onChange={(event) => setCaseQuickKeyword(event.target.value)}
          onSearch={runCaseQuickSearch}
          enterButton
          allowClear
          placeholder="案号、法院号、案件名、客户名、任务内容"
          aria-label="案件快捷搜索"
          style={{ width: 260 }}
        />
        <Space className="top-actions">
          <Tooltip title="返回控制台">
            <Button
              type="text"
              aria-label="返回控制台"
              icon={<HomeOutlined />}
              onClick={() => navigate("dashboard")}
            />
          </Tooltip>
          <Dropdown
            menu={{
              items: sideMenuItems,
              onClick: ({ key }) => {
                const item = flattenMenu(sideMenuItems).find(entry => entry.key === key);
                if (!item || item.disabled || item.children?.length) return;
                if (item.link_url) {
                  openLegacyMenuItem(item);
                  return;
                }
                navigate(String(key));
              },
            }}
            trigger={["click"]}
            placement="bottomLeft"
          >
            <Button type="text" icon={<MenuOutlined />}>
              系统导航 <DownOutlined />
            </Button>
          </Dropdown>
          <NotificationCenter onNavigate={navigate} />
          <Tooltip title="任务消息">
            <Badge count={taskUnreadCount} size="small" overflowCount={99}>
              <Button
                type="text"
                aria-label="任务消息"
                icon={<MessageOutlined />}
                onClick={() => navigate("task-reminders")}
              />
            </Badge>
          </Tooltip>
          <Tooltip title={isFullscreen ? "退出全屏" : "全屏"}>
            <Button
              type="text"
              aria-label={isFullscreen ? "退出全屏" : "全屏"}
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={() => {
                if (document.fullscreenElement) {
                  void document.exitFullscreen?.();
                  return;
                }
                void document.documentElement.requestFullscreen?.();
              }}
            />
          </Tooltip>
          <Dropdown
            menu={{
              items: [
                { key: "profile", label: "个人资料" },
                {
                  key: "official-site",
                  label: <a href="http://www.idchien.com" target="_blank" rel="noreferrer">官网</a>,
                },
                {
                  key: "forum",
                  label: <a href="http://forum.idchien.com" target="_blank" rel="noreferrer">论坛</a>,
                },
                {
                  key: "documentation",
                  label: <a href="http://doc.idchien.com" target="_blank" rel="noreferrer">文档</a>,
                },
                { type: "divider" },
                { key: "logout", label: "退出", danger: true },
              ],
              onClick: ({ key }) => {
                if (key === "profile") {
                  navigate(accountProfileRoute);
                  return;
                }
                if (key === "logout") logout();
              },
            }}
            trigger={["click"]}
            placement="bottomRight"
          >
            <Button type="text" aria-label="账户菜单" icon={<UserOutlined />}>
              {(() => {
                const username = sessionUser?.username || "admin";
                const account = `${username.slice(0, 1).toUpperCase()}${username.slice(1)}`;
                const displayName = sessionUser?.display_name || "管理者";
                const label = displayName.toLowerCase() === username.toLowerCase()
                  ? account
                  : `${account} ${displayName}`;
                return <>{label} <DownOutlined /></>;
              })()}
            </Button>
          </Dropdown>
        </Space>
        <Space className="mobile-top-actions">
          <NotificationCenter onNavigate={navigate} />
          <Badge count={taskUnreadCount} size="small" overflowCount={99}>
            <Button
              type="text"
              aria-label="任务消息"
              icon={<MessageOutlined />}
              onClick={() => navigate("task-reminders")}
            />
          </Badge>
        </Space>
      </Header>
      <Layout className="app-body">
        <Sider
          width={280}
          breakpoint="lg"
          onBreakpoint={(broken) => {
            setIsNarrowViewport(broken);
            if (!broken) setMobileSidebarOpen(false);
          }}
          collapsedWidth={isNarrowViewport ? 0 : 50}
          collapsed={sidebarCollapsed}
          onMouseEnter={() => collapsed && setSidebarHoverExpanded(true)}
          onMouseLeave={() => setSidebarHoverExpanded(false)}
          className="sidebar"
        >
          {(isNarrowViewport ? mobileSidebarOpen : !collapsed) && (
            <div className="user-panel">
              <div
                className="avatar"
                role="button"
                tabIndex={0}
                aria-label="打开个人资料"
                onClick={() => navigate(accountProfileRoute)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    navigate(accountProfileRoute);
                  }
                }}
              >
                {(sessionUser?.username || "admin").slice(0, 1).toUpperCase()}
              </div>
              <div>
                <b>{sessionUser?.display_name || sessionUser?.username || "管理员"}</b>
                <span>● 在线</span>
              </div>
            </div>
          )}
          <Menu
            mode="inline"
            inlineIndent={16}
            theme="dark"
            items={sidebarReloadableItems}
            selectedKeys={[active]}
            openKeys={openMenuKeys}
            onOpenChange={(keys) => {
              const nextKeys = normalizeOpenMenuKeys(effectiveMenuItems, openMenuKeys, keys as string[]);
              const parentRoute = routeForMenuOpenChange(openMenuKeys, nextKeys, active);
              setOpenMenuKeys(nextKeys);
              if (parentRoute) navigate(parentRoute);
            }}
            onClick={({ key }) => {
              const item = flattenMenu(sideMenuItems).find(entry => entry.key === key);
              if (!item || item.disabled) return;
              if (item.link_url) {
                openLegacyMenuItem(item);
                if (isNarrowViewport) setMobileSidebarOpen(false);
                return;
              }
              navigate(key);
              if (isNarrowViewport) setMobileSidebarOpen(false);
            }}
          />
          {(isNarrowViewport ? mobileSidebarOpen : !collapsed) && (
            <div className="support-tools">
              <div className="support-tools-title">办案辅助工具</div>
              {supportTools.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  target="_blank"
                  rel="noreferrer"
                >
                  <LinkOutlined />
                  {item.label}
                </a>
              ))}
            </div>
          )}
        </Sider>
        {isNarrowViewport && mobileSidebarOpen && (
          <button
            type="button"
            className="mobile-sidebar-mask"
            aria-label="关闭功能菜单"
            onClick={() => setMobileSidebarOpen(false)}
          />
        )}
        <Content
          className={`content ${active === "dashboard" ? "dashboard-content" : ""} ${active.startsWith("case-detail-") || active.startsWith("contract-detail-") ? "case-detail-content" : ""}`}
          onClick={() => {
            if (isNarrowViewport && mobileSidebarOpen) setMobileSidebarOpen(false);
          }}
        >
          <div className="page-head">
            <div>
              <h1>
                {currentPageLabel}
                {active === "dashboard" && <sup className="dashboard-hot">hot</sup>}
              </h1>
              <span>首页 / {currentPageLabel}</span>
            </div>
          </div>
          <Tabs
            className="workspace-tabs"
            type="editable-card"
            hideAdd
            size="small"
            activeKey={active}
            onChange={navigate}
            onEdit={(target, action) => action === "remove" && closeOpenPage(String(target))}
            tabBarExtraContent={{
              right: (
                <Tooltip title="刷新当前页">
                  <Button
                    type="text"
                    aria-label="刷新当前页"
                    icon={<ReloadOutlined />}
                    onClick={() => setWorkspaceReloadKey((value) => value + 1)}
                  />
                </Tooltip>
              ),
            }}
            items={openPages.map((item) => ({
              key: item.key,
              label: (
                <span
                  onDoubleClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    if (item.key === "dashboard") return;
                    closeOpenPage(item.key);
                  }}
                >
                  {item.label}
                </span>
              ),
              closable: item.key !== "dashboard",
            }))}
          />
          <main className="page-workbench">
            <PageLoadBoundary key={`${active}:${workspaceReloadKey}`}>
              <Suspense fallback={<div className="loading">正在加载页面...</div>}>
                {currentPage}
              </Suspense>
            </PageLoadBoundary>
          </main>
        </Content>
      </Layout>
      <nav className="mobile-bottom-nav" aria-label="移动端主导航">
        <button
          type="button"
          className={active === "dashboard" ? "active" : ""}
          aria-current={active === "dashboard" ? "page" : undefined}
          onClick={() => navigate("dashboard")}
        >
          <HomeOutlined />
          <span>首页</span>
        </button>
        <button
          type="button"
          className={active === "agent-center" ? "active" : ""}
          aria-current={active === "agent-center" ? "page" : undefined}
          onClick={() => navigate("agent-center")}
        >
          <RobotOutlined />
          <span>智能体</span>
        </button>
        <button
          type="button"
          className={active.startsWith("task-") ? "active" : ""}
          onClick={() => navigate("task-my")}
        >
          <Badge count={taskUnreadCount} size="small" overflowCount={99}>
            <UnorderedListOutlined />
          </Badge>
          <span>待办</span>
        </button>
        <button
          type="button"
          className={active === "task-reminders" ? "active" : ""}
          onClick={() => navigate("task-reminders")}
        >
          <MessageOutlined />
          <span>消息</span>
        </button>
        <button
          type="button"
          className={active === accountProfileRoute ? "active" : ""}
          onClick={() => navigate(accountProfileRoute)}
        >
          <UserOutlined />
          <span>我的</span>
        </button>
      </nav>
    </Layout>
  );
}
