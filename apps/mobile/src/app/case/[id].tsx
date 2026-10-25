import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useNavigation, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { Card, Empty, ErrorBanner, Field, Tag, personName } from "@/components/ui";
import { api } from "@/lib/api";
import { caseHeaderHearingLawyers, caseParties, casePersonName, courtLevels, type PersonOption } from "@/lib/cases";
import { taskStatus } from "@/lib/tasks";
import { colors } from "@/lib/theme";
import type { CaseLog, CaseRow, Paged, TaskRow } from "@/lib/types";

const SECTIONS = [
  { key: "info", label: "案件信息" },
  { key: "logs", label: "进展日志" },
  { key: "tasks", label: "案件任务" },
] as const;

export default function CaseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const caseId = Number(id);
  const navigation = useNavigation();
  const [section, setSection] = useState<(typeof SECTIONS)[number]["key"]>("info");

  const detail = useQuery({ queryKey: ["case", caseId], queryFn: () => api.get<CaseRow>(`/records/${caseId}`) });

  useEffect(() => {
    if (detail.data?.serial_no) navigation.setOptions({ title: detail.data.serial_no });
  }, [detail.data?.serial_no, navigation]);

  if (detail.isLoading) return <ActivityIndicator style={{ marginTop: 48 }} color={colors.primary} />;
  if (!detail.data) return <ErrorBanner message={(detail.error as Error)?.message || "未找到案件或当前账号无权查看"} onRetry={() => detail.refetch()} />;

  return (
    <View style={{ flex: 1 }}>
      <View style={styles.segments}>
        {SECTIONS.map((item) => (
          <Pressable key={item.key} style={[styles.segment, section === item.key && styles.segmentActive]} onPress={() => setSection(item.key)}>
            <Text style={[styles.segmentText, section === item.key && styles.segmentTextActive]}>{item.label}</Text>
          </Pressable>
        ))}
      </View>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
        {section === "info" && <CaseInfo row={detail.data} />}
        {section === "logs" && <CaseLogs caseId={caseId} />}
        {section === "tasks" && <CaseTasks caseId={caseId} />}
      </ScrollView>
    </View>
  );
}

function CaseInfo({ row }: { row: CaseRow }) {
  const data = row.data || {};
  const isCriminal = data.case_type === "刑事案件";
  const { plaintiff, defendant } = caseParties(data);
  const reference = useQuery({
    queryKey: ["cases", "reference-options"],
    queryFn: () => api.get<{ case_assistants?: PersonOption[] }>("/cases/reference-options"),
    staleTime: 10 * 60_000,
  });
  const people = reference.data?.case_assistants || [];
  const hearing = caseHeaderHearingLawyers(data).map((item) => casePersonName(item, people));
  return (
    <>
      <Card>
        <View style={styles.head}>
          <Text style={styles.title} selectable>{row.title || "（无案件名称）"}</Text>
          {!!row.status && <Tag label={row.status} />}
        </View>
        <Field label="我方案号" value={row.serial_no} />
        <Field label="案件类型" value={data.case_type} />
        <Field label={isCriminal ? "罪名" : "案由"} value={data.cause_or_charge || data.cause_of_action} />
        <Field label={isCriminal ? "受害人" : "原告"} value={plaintiff} />
        {!isCriminal && <Field label="被告" value={defendant} />}
        <Field label="客户" value={row.customer} />
        <Field label="合同号" value={data.contract_no} />
        <Field label="承办律师" value={personName(row.owner_display_name, row.owner)} />
        <Field label="开庭律师" value={hearing.join("、")} />
        <Field label="诉讼标的" value={data.litigation_subject || data.litigation_amount} />
        <Field label="案源日期" value={String(data.source_date || data.source_at || "").slice(0, 10)} />
      </Card>
      {data.case_type !== "法律顾问" &&
        courtLevels(data).map((level) => (
          <Card key={level.label}>
            <Text style={styles.cardTitle}>{level.label}法院</Text>
            <Field label="法院" value={level.court} />
            <Field label="法庭" value={level.courtroom} />
            <Field label="案号" value={level.caseNo} />
            <Field label="开庭时间" value={level.hearingDate} />
          </Card>
        ))}
      {!!row.description && (
        <Card>
          <Text style={styles.cardTitle}>备注</Text>
          <Text style={styles.body} selectable>{row.description}</Text>
        </Card>
      )}
    </>
  );
}

function CaseLogs({ caseId }: { caseId: number }) {
  const logs = useQuery({ queryKey: ["case", caseId, "logs"], queryFn: () => api.get<{ items: CaseLog[] }>(`/cases/${caseId}/logs`) });
  if (logs.isLoading) return <ActivityIndicator style={{ marginTop: 24 }} color={colors.primary} />;
  if (logs.error) return <ErrorBanner message={(logs.error as Error).message} onRetry={() => logs.refetch()} />;
  if (!logs.data?.items.length) return <Empty text="暂无进展日志" />;
  return (
    <>
      {logs.data.items.map((log) => (
        <Card key={String(log.id)}>
          <Text style={styles.logHead}>{String(log.created_at || "").replace("T", " ").slice(0, 16)} · {personName(log.operator_display_name, log.operator)}</Text>
          <Text style={styles.body} selectable>{log.content}</Text>
        </Card>
      ))}
    </>
  );
}

function CaseTasks({ caseId }: { caseId: number }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const tasks = useQuery({
    queryKey: ["case", caseId, "tasks"],
    queryFn: () => api.get<Paged<TaskRow>>(`/cases/${caseId}/tasks`, { page: 1, page_size: 50 }),
  });
  if (tasks.isLoading) return <ActivityIndicator style={{ marginTop: 24 }} color={colors.primary} />;
  if (tasks.error) return <ErrorBanner message={(tasks.error as Error).message} onRetry={() => tasks.refetch()} />;
  if (!tasks.data?.items.length) return <Empty text="暂无案件任务" />;
  return (
    <>
      {tasks.data.items.map((task) => (
        <Card
          key={task.id}
          onPress={() => {
            // 预先放入任务投影，详情页不必回退到通用记录接口。
            queryClient.setQueryData(["task", task.id], task);
            router.push(`/task/${task.id}`);
          }}
        >
          <View style={styles.head}>
            <Text style={styles.taskTitle} numberOfLines={2}>{task.title}</Text>
            <Tag label={taskStatus(task)} />
          </View>
          <Text style={styles.logHead}>负责人 {personName(task.owner_display_name, task.owner)}{task.deadline ? ` · 截止 ${task.deadline.slice(0, 10)}` : ""}</Text>
        </Card>
      ))}
    </>
  );
}

const styles = StyleSheet.create({
  segments: { flexDirection: "row", backgroundColor: colors.surface, borderBottomWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  segment: { flex: 1, alignItems: "center", paddingVertical: 12, borderBottomWidth: 2, borderColor: "transparent" },
  segmentActive: { borderColor: colors.primary },
  segmentText: { color: colors.textSecondary, fontSize: 15 },
  segmentTextActive: { color: colors.primary, fontWeight: "700" },
  head: { flexDirection: "row", gap: 8, marginBottom: 8 },
  title: { flex: 1, fontSize: 17, fontWeight: "700", color: colors.text },
  cardTitle: { fontSize: 15, fontWeight: "700", color: colors.text, marginBottom: 4 },
  body: { color: colors.text, lineHeight: 21, marginTop: 4 },
  logHead: { color: colors.textMuted, fontSize: 12 },
  taskTitle: { flex: 1, fontSize: 15, fontWeight: "600", color: colors.text },
});
