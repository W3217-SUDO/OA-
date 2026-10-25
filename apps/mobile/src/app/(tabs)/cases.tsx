import { useInfiniteQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";
import { Card, Empty, ErrorBanner, Tag, personName } from "@/components/ui";
import { api } from "@/lib/api";
import { caseParties } from "@/lib/cases";
import { colors } from "@/lib/theme";
import type { CaseRow, Paged } from "@/lib/types";

const PAGE_SIZE = 20;
// 对应网页“我的案件 / 部门案件 / 公司案件”；无权限的范围由后端返回 403。
const SCOPES = [
  { key: "mine", label: "我的" },
  { key: "department", label: "部门" },
  { key: "company", label: "全所" },
] as const;

export default function CasesScreen() {
  const router = useRouter();
  const [scope, setScope] = useState<(typeof SCOPES)[number]["key"]>("mine");
  const [input, setInput] = useState("");
  const [keyword, setKeyword] = useState("");

  const query = useInfiniteQuery({
    queryKey: ["cases", scope, keyword],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      api.post<Paged<CaseRow>>("/cases/search", { scope, keyword, sort_order: "updated_desc", page: pageParam, page_size: PAGE_SIZE }),
    getNextPageParam: (last) => (last.page * last.page_size < last.total ? last.page + 1 : undefined),
  });
  const items = query.data?.pages.flatMap((page) => page.items) || [];

  return (
    <View style={styles.page}>
      <View style={styles.toolbar}>
        <TextInput
          style={styles.search}
          placeholder="搜索案号、案件名称、客户、当事人"
          value={input}
          onChangeText={setInput}
          returnKeyType="search"
          onSubmitEditing={() => setKeyword(input.trim())}
          clearButtonMode="while-editing"
        />
        <View style={styles.scopes}>
          {SCOPES.map((item) => (
            <Pressable key={item.key} onPress={() => setScope(item.key)} style={[styles.scope, scope === item.key && styles.scopeActive]}>
              <Text style={[styles.scopeText, scope === item.key && styles.scopeTextActive]}>{item.label}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      {query.error && <ErrorBanner message={(query.error as Error).message} onRetry={() => query.refetch()} />}
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        keyboardShouldPersistTaps="handled"
        renderItem={({ item }) => <CaseCard row={item} onPress={() => router.push(`/case/${item.id}`)} />}
        refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => void query.refetch()} colors={[colors.primary]} />}
        onEndReached={() => query.hasNextPage && !query.isFetchingNextPage && query.fetchNextPage()}
        onEndReachedThreshold={0.4}
        ListHeaderComponent={query.isSuccess ? <Text style={styles.count}>共 {query.data.pages[0]?.total ?? 0} 件</Text> : undefined}
        ListEmptyComponent={query.isLoading ? <ActivityIndicator style={{ marginTop: 48 }} color={colors.primary} /> : query.isSuccess ? <Empty text="没有符合条件的案件" /> : undefined}
        ListFooterComponent={query.isFetchingNextPage ? <ActivityIndicator style={{ margin: 16 }} color={colors.primary} /> : <View style={{ height: 16 }} />}
      />
    </View>
  );
}

function CaseCard({ row, onPress }: { row: CaseRow; onPress: () => void }) {
  const data = row.data || {};
  const { plaintiff, defendant } = caseParties(data);
  return (
    <Card onPress={onPress}>
      <View style={styles.head}>
        <Text style={styles.serial}>{row.serial_no}</Text>
        {!!row.status && <Tag label={row.status} />}
      </View>
      <Text style={styles.title} numberOfLines={2}>{row.title || "（无案件名称）"}</Text>
      <Text style={styles.meta} numberOfLines={1}>{[data.case_type, data.cause_or_charge || data.cause_of_action].filter(Boolean).join(" · ") || "—"}</Text>
      {(plaintiff || defendant) && <Text style={styles.meta} numberOfLines={1}>{plaintiff || "—"} 诉 {defendant || "—"}</Text>}
      <Text style={styles.meta} numberOfLines={1}>客户：{row.customer || "—"}　承办：{personName(row.owner_display_name, row.owner)}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  toolbar: { backgroundColor: colors.surface, padding: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  search: { height: 40, backgroundColor: colors.background, borderRadius: 8, paddingHorizontal: 12, fontSize: 15, color: colors.text },
  scopes: { flexDirection: "row", marginTop: 8, gap: 8 },
  scope: { paddingHorizontal: 14, paddingVertical: 5, borderRadius: 14, backgroundColor: colors.background },
  scopeActive: { backgroundColor: colors.primary },
  scopeText: { color: colors.textSecondary },
  scopeTextActive: { color: "#fff", fontWeight: "600" },
  count: { color: colors.textMuted, fontSize: 12, marginHorizontal: 14, marginTop: 10 },
  head: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 4 },
  serial: { color: colors.accent, fontWeight: "600", fontSize: 13 },
  title: { fontSize: 16, fontWeight: "600", color: colors.text },
  meta: { color: colors.textSecondary, fontSize: 13, marginTop: 3 },
});
