import { useInfiniteQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { Card, Empty, ErrorBanner, Tag, personName } from "@/components/ui";
import { api } from "@/lib/api";
import { TASK_VIEWS, deadlineText, taskStatus } from "@/lib/tasks";
import { colors } from "@/lib/theme";
import type { TaskListResponse, TaskRow } from "@/lib/types";

const PAGE_SIZE = 20;

export default function TasksScreen() {
  const router = useRouter();
  const [viewKey, setViewKey] = useState(TASK_VIEWS[0].key);
  const view = TASK_VIEWS.find((item) => item.key === viewKey) || TASK_VIEWS[0];

  const query = useInfiniteQuery({
    queryKey: ["tasks", "list", view.key],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      view.unread
        ? api.get<TaskListResponse>("/tasks/unread-messages", { page: pageParam, page_size: PAGE_SIZE })
        : api.get<TaskListResponse>("/tasks", {
            scope: "mine",
            relation: view.relation,
            statuses: view.statuses.join(","),
            page: pageParam,
            page_size: PAGE_SIZE,
          }),
    getNextPageParam: (last) => (last.page * last.page_size < last.total ? last.page + 1 : undefined),
  });
  const items = query.data?.pages.flatMap((page) => page.items) || [];
  const total = query.data?.pages[0]?.total ?? 0;

  return (
    <View style={styles.page}>
      <View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabs}>
          {TASK_VIEWS.map((item) => (
            <Pressable key={item.key} onPress={() => setViewKey(item.key)} style={[styles.tab, item.key === view.key && styles.tabActive]}>
              <Text style={[styles.tabText, item.key === view.key && styles.tabTextActive]}>{item.label}</Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>
      {query.error && <ErrorBanner message={(query.error as Error).message} onRetry={() => query.refetch()} />}
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => <TaskCard task={item} unreadView={!!view.unread} onPress={() => router.push({ pathname: "/task/[id]", params: { id: String(item.id), ...(view.unread ? { fromUnread: "1" } : {}) } })} />}
        refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => void query.refetch()} colors={[colors.primary]} />}
        onEndReached={() => query.hasNextPage && !query.isFetchingNextPage && query.fetchNextPage()}
        onEndReachedThreshold={0.4}
        ListHeaderComponent={query.isSuccess ? <Text style={styles.count}>共 {total} 条</Text> : undefined}
        ListEmptyComponent={query.isLoading ? <ActivityIndicator style={{ marginTop: 48 }} color={colors.primary} /> : query.isSuccess ? <Empty text="暂无任务" /> : undefined}
        ListFooterComponent={query.isFetchingNextPage ? <ActivityIndicator style={{ margin: 16 }} color={colors.primary} /> : <View style={{ height: 16 }} />}
      />
    </View>
  );
}

function TaskCard({ task, unreadView, onPress }: { task: TaskRow; unreadView: boolean; onPress: () => void }) {
  const overdue = (task.days_remaining ?? 0) < 0;
  return (
    <Card onPress={onPress}>
      <View style={styles.cardHead}>
        <Text style={styles.title} numberOfLines={2}>{task.title || "（无标题）"}</Text>
        <Tag label={taskStatus(task)} />
      </View>
      <Text style={styles.meta}>{task.serial_no}{task.case_no ? ` · ${task.case_no}` : ""}</Text>
      {!!task.customer && <Text style={styles.meta} numberOfLines={1}>客户：{task.customer}</Text>}
      <Text style={styles.meta}>发起人 {personName(task.initiator_display_name, task.initiator)} → 负责人 {personName(task.owner_display_name, task.owner)}</Text>
      <Text style={[styles.meta, overdue && { color: colors.danger }]}>{deadlineText(task)}</Text>
      {unreadView && !!task.latest_unread_message && (
        <Text style={styles.unread} numberOfLines={2}>
          {personName(task.latest_unread_sender_display_name)}：{task.latest_unread_message}
        </Text>
      )}
      {task.unread_count > 0 && <Text style={styles.badge}>{task.unread_count} 条未读</Text>}
    </Card>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  tabs: { paddingHorizontal: 8, paddingVertical: 8, backgroundColor: colors.surface },
  tab: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 16, marginHorizontal: 4, backgroundColor: colors.background },
  tabActive: { backgroundColor: colors.primary },
  tabText: { color: colors.textSecondary, fontSize: 14 },
  tabTextActive: { color: "#fff", fontWeight: "600" },
  count: { color: colors.textMuted, fontSize: 12, marginHorizontal: 14, marginTop: 10 },
  cardHead: { flexDirection: "row", justifyContent: "space-between", gap: 8, marginBottom: 6 },
  title: { flex: 1, fontSize: 16, fontWeight: "600", color: colors.text },
  meta: { color: colors.textSecondary, fontSize: 13, marginTop: 3 },
  unread: { marginTop: 8, padding: 8, backgroundColor: colors.primarySoft, borderRadius: 6, color: colors.text, fontSize: 13 },
  badge: { marginTop: 6, color: colors.danger, fontSize: 12 },
});
