import type { ModuleKey, Row } from "./types";

export const CLUE_INFRINGEMENT_METHOD_OPTIONS = [
  "电商平台",
  "实体店铺",
  "工厂",
  "网页链接",
  "其他",
];

export const CLUE_SALES_CHANNEL_OPTIONS = [
  "淘宝",
  "天猫",
  "京东",
  "拼多多",
  "抖音",
  "快手",
  "小红书",
  "微信",
  "官网",
  "线下门店",
  "其他",
];

export const moduleMeta: Record<ModuleKey, { title: string; prefix: string; statuses: string[] }> = {
  investigation: {
    title: "调查任务",
    prefix: "DC",
    statuses: ["待分配", "进行中", "已完成", "已取消"],
  },
  clue: {
    title: "调查线索",
    prefix: "XS",
    statuses: [
      "草稿",
      "待审批",
      "待取证",
      "已取证",
      "待公证",
      "已转案件",
      "已驳回",
    ],
  },
  notary: {
    title: "公证审核",
    prefix: "GZ",
    statuses: ["等待材料", "待审核", "审核通过", "审核驳回"],
  },
  evidence: {
    title: "证据材料",
    prefix: "ZJ",
    statuses: ["待整理", "已整理", "已入卷"],
  },
};

export const statusColors: Record<string, string> = {
  待分配: "orange",
  进行中: "blue",
  已完成: "green",
  已取消: "red",
  待审批: "orange",
  待客户审核: "gold",
  待取证: "cyan",
  已取证: "blue",
  待公证: "purple",
  已转案件: "green",
  等待材料: "gold",
  审核通过: "green",
  审核驳回: "red",
  待审核: "orange",
  已入卷: "green",
};

export const isLegacyInvestigationRecord = (row: Row | null) => {
  const data = row?.data || {};
  return Boolean(
    data.migration_source ||
      data.legacy_investigation_id ||
      data.legacy_record,
  );
};

export const investigationListView = (route: string) => {
  if (
    route === "investigation-task-unassigned" ||
    route === "investigation-task-sub-mine"
  )
    return "assigned";
  if (
    route === "investigation-task-published" ||
    route === "investigation-task-overdue" ||
    route === "investigation-task-sub-published"
  )
    return "published";
  if (route === "investigation-task-mine") return "published";
  return "";
};

export const serial = (prefix: string) =>
  prefix + new Date().toISOString().replace(/\D/g, "").slice(0, 14);
