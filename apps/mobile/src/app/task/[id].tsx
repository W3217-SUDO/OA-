import { useMutation, useQuery, useQueryClient, type InfiniteData } from "@tanstack/react-query";
import { useHeaderHeight } from "@react-navigation/elements";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, KeyboardAvoidingView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { Button, Card, Empty, ErrorBanner, Field, Tag, personName } from "@/components/ui";
import { api, request } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ACTION_COMMENTS, deadlineText, taskActions, taskStatus } from "@/lib/tasks";
import { colors } from "@/lib/theme";
import type { CaseRow, TaskHistoryItem, TaskListResponse, TaskRow } from "@/lib/types";
// 系统提示框默认按钮是英文 OK。
const OK = [{ text: "好" }];

/** 列表接口返回的是完整任务投影，详情优先复用缓存，避免再查通用记录接口。 */
function findCachedTask(queryClient: ReturnType<typeof useQueryClient>, id: number): TaskRow | undefined {
  for (const [, data] of queryClient.getQueriesData<InfiniteData<TaskListResponse>>({ queryKey: ["tasks", "list"] })) {
    const found = data?.pages.flatMap((page) => page.items).find((item) => item.id === id);
    if (found) return found;
  }
  return queryClient.getQueryData<TaskRow>(["task", id]);
}

export default function TaskDetailScreen() {
  const { id, fromUnread } = useLocalSearchParams<{ id: string; fromUnread?: string }>();
  const taskId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const headerHeight = useHeaderHeight();
  const [comment, setComment] = useState("");

  const task = useQuery({
    queryKey: ["task", taskId],
    queryFn: async () => {
      const record = await api.get<TaskRow>(`/records/${taskId}`);
      return { ...record, workflow_status: record.workflow_status || record.status };
    },
    initialData: () => findCachedTask(queryClient, taskId),
    // 通用记录接口字段比列表投影少，已有列表数据时不自动用它覆盖。
    staleTime: Infinity,
  });
  const history = useQuery({
    queryKey: ["task", taskId, "history"],
    queryFn: () => api.get<{ items: TaskHistoryItem[] }>(`/tasks/${taskId}/history`),
  });

  useEffect(() => {
    // 与网页端 openCommunication 一致：只有从“未读消息”列表打开才标记已读。
    if (fromUnread !== "1") return;
    void api.post(`/tasks/${taskId}/messages/read`).then(() => queryClient.invalidateQueries({ queryKey: ["tasks"] })).catch(() => undefined);
  }, [taskId, fromUnread, queryClient]);

  const afterChange = async (updated?: TaskRow) => {
    // 操作接口返回的任务缺显示名、案件阶段等投影字段；按编号重新取列表投影（同网页端 serial_no 定位）。
    const serialNo = updated?.serial_no || task.data?.serial_no;
    if (serialNo) {
      try {
        const { items } = await api.get<TaskListResponse>("/tasks", { serial_no: serialNo, scope: "default", page_size: 20 });
        const fresh = items.find((item) => item.id === taskId);
        if (fresh) queryClient.setQueryData(["task", taskId], fresh);
        else if (updated?.id) queryClient.setQueryData<TaskRow>(["task", taskId], (old) => ({ ...old, ...updated }));
      } catch {
        if (updated?.id) queryClient.setQueryData<TaskRow>(["task", taskId], (old) => ({ ...old, ...updated }));
      }
    }
    void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    void queryClient.invalidateQueries({ queryKey: ["task", taskId, "history"] });
  };

  const action = useMutation({
    mutationFn: (type: keyof typeof ACTION_COMMENTS) => api.post<TaskRow>(`/tasks/${taskId}/${type}`, { comment: ACTION_COMMENTS[type] }),
    onSuccess: async (data, type) => {
      await afterChange(data);
      Alert.alert(ACTION_COMMENTS[type], undefined, OK);
    },
    onError: (error) => Alert.alert("操作失败", (error as Error).message, OK),
  });

  const feedback = useMutation({
    mutationFn: (text: string) => {
      const body = new FormData();
      body.append("comment", text);
      return request(`/tasks/${taskId}/feedback`, { method: "POST", multipart: body });
    },
    onSuccess: async () => {
      setComment("");
      await afterChange();
    },
    onError: (error) => Alert.alert("反馈提交失败", (error as Error).message, OK),
  });

  // 与网页端 taskCaseContext 一致：按案号在可见案件中精确匹配。
  const openCase = async (caseNo: string) => {
    try {
      const { items } = await api.get<{ items: CaseRow[] }>("/records", { module: "case", keyword: caseNo, page_size: 100 });
      const target = items.find((item) => item.serial_no === caseNo);
      if (target) router.push(`/case/${target.id}`);
      else Alert.alert("未找到关联案件或当前账号无权查看", undefined, OK);
    } catch (error) {
      Alert.alert("打开案件失败", (error as Error).message, OK);
    }
  };

  if (!task.data) {
    if (task.isLoading) return <ActivityIndicator style={{ marginTop: 48 }} color={colors.primary} />;
    return <ErrorBanner message={(task.error as Error)?.message || "未找到任务或当前账号无权查看"} onRetry={() => task.refetch()} />;
  }
  const row = task.data;
  const can = taskActions(row, user);
  const confirmAction = (type: keyof typeof ACTION_COMMENTS, label: string) =>
    Alert.alert(label, `确定${label}吗？`, [{ text: "取消", style: "cancel" }, { text: "确定", onPress: () => action.mutate(type) }]);

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior="padding" keyboardVerticalOffset={headerHeight}>
      <ScrollView contentContainerStyle={{ paddingBottom: 24 }} keyboardShouldPersistTaps="handled">
        <Card>
          <View style={styles.head}>
            <Text style={styles.title} selectable>{row.title || "（无标题）"}</Text>
            <Tag label={taskStatus(row)} />
          </View>
          <Field label="任务编号" value={row.serial_no} />
          <Field label="关联案件" value={row.case_no} />
          <Field label="客户" value={row.customer} />
          <Field label="发起人" value={personName(row.initiator_display_name, row.initiator)} />
          <Field label="负责人" value={personName(row.owner_display_name, row.owner)} />
          <Field label="协作人" value={(row.collaborator_display_names || row.collaborators || []).join("、")} />
          <Field label="优先级" value={row.priority} />
          <Field label="期限" value={deadlineText(row)} />
          <Field label="案件阶段" value={row.case_stage} />
          {!!row.rejected_reason && <Field label="拒绝原因" value={row.rejected_reason} />}
          {!!row.description && <Text style={styles.description} selectable>{row.description}</Text>}
          {!!row.case_no && (
            <Text style={styles.link} onPress={() => void openCase(row.case_no)}>查看关联案件 ›</Text>
          )}
        </Card>

        {(can.accept || can.complete || can.confirm) && (
          <View style={styles.actions}>
            {can.accept && <Button title="接受任务" kind="ghost" loading={action.isPending && action.variables === "accept"} onPress={() => confirmAction("accept", "接受任务")} />}
            {can.complete && <Button title="提交完成" loading={action.isPending && action.variables === "complete"} onPress={() => confirmAction("complete", "提交完成")} />}
            {can.confirm && <Button title="验收" loading={action.isPending && action.variables === "confirm"} onPress={() => confirmAction("confirm", "验收任务")} />}
          </View>
        )}

        <Text style={styles.section}>沟通记录</Text>
        {history.error && <ErrorBanner message={(history.error as Error).message} onRetry={() => history.refetch()} />}
        {history.isLoading && <ActivityIndicator color={colors.primary} />}
        {history.data && !history.data.items.length && <Empty text="暂无沟通记录" />}
        {history.data?.items.map((item) => (
          <View key={item.id} style={styles.history}>
            <Text style={styles.historyHead}>
              {personName(item.operator_display_name, item.operator)} · {item.action}
              {item.to_status && item.to_status !== item.from_status ? `（${item.from_status || "—"} → ${item.to_status}）` : ""}
            </Text>
            {!!item.comment && <Text style={styles.historyBody} selectable>{item.comment}</Text>}
            <Text style={styles.historyTime}>{item.created_at?.replace("T", " ").slice(0, 16)}</Text>
          </View>
        ))}

        {can.feedback && (
          <Card>
            <TextInput style={styles.input} placeholder="填写反馈内容" multiline value={comment} onChangeText={setComment} />
            <View style={{ flexDirection: "row", marginTop: 8 }}>
              <Button title="提交反馈" disabled={!comment.trim()} loading={feedback.isPending} onPress={() => feedback.mutate(comment.trim())} />
            </View>
          </Card>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  head: { flexDirection: "row", gap: 8, marginBottom: 8 },
  title: { flex: 1, fontSize: 17, fontWeight: "700", color: colors.text },
  description: { marginTop: 8, padding: 10, backgroundColor: colors.background, borderRadius: 6, color: colors.text, lineHeight: 20 },
  link: { marginTop: 10, color: colors.accent, fontWeight: "600" },
  actions: { flexDirection: "row", gap: 10, marginHorizontal: 12, marginTop: 12 },
  section: { marginHorizontal: 14, marginTop: 18, marginBottom: 4, fontSize: 15, fontWeight: "700", color: colors.text },
  history: { marginHorizontal: 12, marginTop: 8, padding: 12, backgroundColor: colors.surface, borderRadius: 8 },
  historyHead: { color: colors.textSecondary, fontSize: 13 },
  historyBody: { color: colors.text, marginTop: 4, lineHeight: 20 },
  historyTime: { color: colors.textMuted, fontSize: 12, marginTop: 4 },
  input: { minHeight: 80, borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 10, textAlignVertical: "top", fontSize: 15, color: colors.text },
});
