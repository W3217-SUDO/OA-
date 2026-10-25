import Ionicons from "@expo/vector-icons/Ionicons";
import { useHeaderHeight } from "@react-navigation/elements";
import { useNavigation } from "expo-router";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ActivityIndicator, Alert, FlatList, KeyboardAvoidingView, Modal, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Markdown } from "@/components/Markdown";
import { Button, Empty, ErrorBanner } from "@/components/ui";
import { agentApi, sendAgentMessage } from "@/lib/agent";
import { colors } from "@/lib/theme";
import type { ConversationSnapshot, PendingAction, WorkspaceConversation, WorkspaceMessage, WorkspaceState } from "@/lib/types";
// 系统提示框默认按钮是英文 OK。
const OK = [{ text: "好" }];

const EMPTY: WorkspaceState = { messages: [], pending_actions: [], dismissed_action_ids: [] };
// 需要填写外部凭证或预览的操作在手机上不确认，提示到网页端处理。
const needsWeb = (action: PendingAction) => action.type.toLowerCase().includes("mcp");

export default function AgentScreen() {
  const navigation = useNavigation();
  // 安卓边到边显示下键盘不会自动顶起页面，按导航栏高度手动避让。
  const headerHeight = useHeaderHeight();
  const [items, setItems] = useState<WorkspaceConversation[]>([]);
  const [state, setState] = useState<WorkspaceState>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [deciding, setDeciding] = useState("");
  const controller = useRef<AbortController | null>(null);
  const listRef = useRef<FlatList<WorkspaceMessage>>(null);

  const apply = (snapshot: ConversationSnapshot) => {
    setItems(snapshot.items || []);
    setState(snapshot.state || EMPTY);
    if (snapshot.active_unavailable_reason) setError(snapshot.active_unavailable_reason);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      apply(await agentApi.snapshot());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 首次进入只读一次快照；之后的刷新走 load()。
    agentApi
      .snapshot()
      .then(apply)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
    return () => controller.current?.abort();
  }, []);

  const switchTo = async (action: () => Promise<ConversationSnapshot>) => {
    if (running) {
      Alert.alert("请先停止当前回答", undefined, OK);
      return;
    }
    setPickerOpen(false);
    setLoading(true);
    setError("");
    try {
      apply(await action());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <View style={styles.headerActions}>
          <Pressable hitSlop={10} onPress={() => setPickerOpen(true)} accessibilityLabel="历史对话">
            <Ionicons name="time-outline" size={22} color="#fff" />
          </Pressable>
          <Pressable hitSlop={10} onPress={() => void switchTo(agentApi.create)} accessibilityLabel="新对话">
            <Ionicons name="create-outline" size={22} color="#fff" />
          </Pressable>
        </View>
      ),
      headerTitle: state.conversation_title || "智能体",
    });
  });

  const send = async () => {
    const content = draft.trim();
    const id = state.conversation_id;
    if (!content || running) return;
    if (!id) {
      setError("请先新建对话");
      return;
    }
    setDraft("");
    setRunning(true);
    setProgress("正在连接办公助手…");
    const base = state.messages.length;
    setState((current) => ({ ...current, messages: [...current.messages, { role: "user", content }, { role: "assistant", content: "" }] }));
    const abort = new AbortController();
    controller.current = abort;
    try {
      const result = await sendAgentMessage(
        id,
        content,
        {
          onProgress: setProgress,
          onDelta: (delta) =>
            setState((current) => ({
              ...current,
              messages: current.messages.map((item, index) => (index === base + 1 ? { ...item, content: item.content + delta } : item)),
            })),
        },
        abort.signal,
      );
      if (result) setState(result);
      else if (!abort.signal.aborted) throw new Error("响应中断，未收到完整结果，请重新发送");
    } catch (e) {
      if (!abort.signal.aborted) {
        const text = (e as Error).message || "智能体处理失败";
        setState((current) => ({
          ...current,
          messages: current.messages.map((item, index) => (index === base + 1 ? { ...item, failed: true, content: text } : item)),
        }));
      }
    } finally {
      controller.current = null;
      setRunning(false);
      setProgress("");
    }
  };

  const stop = async () => {
    const id = state.conversation_id;
    if (!id) return;
    setProgress("正在停止当前回答…");
    try {
      // 先等服务端停止并释放会话锁，再中断本地读取，避免迟到的增量覆盖停止结果。
      const { state: stopped } = await agentApi.stop(id);
      controller.current?.abort();
      setState(stopped);
    } catch (e) {
      Alert.alert("停止失败，回答可能仍在生成", (e as Error).message, OK);
    }
  };

  const decide = (action: PendingAction, decision: "approved" | "rejected") => {
    const id = state.conversation_id;
    if (!id) return;
    const label = decision === "approved" ? "确认执行" : "取消操作";
    Alert.alert(label, action.summary, [
      { text: "返回", style: "cancel" },
      {
        text: label,
        style: decision === "approved" ? "default" : "destructive",
        onPress: async () => {
          setDeciding(action.id);
          try {
            const { state: next } = await agentApi.decide(action.id, id, decision);
            if (next.conversation_id !== id) throw new Error("确认响应对话编号不匹配");
            setState(next);
          } catch (e) {
            // 决定可能已在服务端落库：只读回查最新状态，不自动重试写入。
            Alert.alert("确认结果未知", `${(e as Error).message}\n已重新读取对话状态，请核对后再操作，不要重复提交。`, OK);
            await load();
          } finally {
            setDeciding("");
          }
        },
      },
    ]);
  };

  const pending = state.pending_actions.filter((item) => item.status === "pending" && !state.dismissed_action_ids.includes(item.id));

  return (
    <KeyboardAvoidingView style={styles.page} behavior="padding" keyboardVerticalOffset={headerHeight}>
      {!!error && <ErrorBanner message={error} onRetry={() => void load()} />}
      {loading ? (
        <ActivityIndicator style={{ marginTop: 48 }} color={colors.primary} />
      ) : (
        <FlatList
          ref={listRef}
          data={state.messages}
          keyExtractor={(_, index) => String(index)}
          contentContainerStyle={{ padding: 12, paddingBottom: 4 }}
          onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: false })}
          ListEmptyComponent={<Empty text={state.conversation_id ? "有什么可以帮你？可以问案件进展、待办任务、文书起草等。" : "点右上角新建对话"} />}
          renderItem={({ item, index }) => <MessageBubble item={item} streaming={running && index === state.messages.length - 1} />}
          ListFooterComponent={
            <>
              {running && !!progress && <Text style={styles.progress}>{progress}</Text>}
              {pending.map((action) => (
                <View key={action.id} style={styles.action}>
                  <Text style={styles.actionTitle}>待你确认的操作</Text>
                  <Text style={styles.actionSummary} selectable>{action.summary}</Text>
                  {needsWeb(action) ? (
                    <Text style={styles.actionHint}>此操作需要在网页端填写凭证后确认。</Text>
                  ) : (
                    <View style={styles.actionButtons}>
                      <Button title="取消" kind="danger" disabled={!!deciding || running} onPress={() => decide(action, "rejected")} />
                      <Button title="确认执行" loading={deciding === action.id} disabled={!!deciding || running} onPress={() => decide(action, "approved")} />
                    </View>
                  )}
                </View>
              ))}
            </>
          }
        />
      )}
      <View style={styles.composer}>
        <TextInput
          style={styles.input}
          placeholder={state.conversation_id ? "给智能体发消息" : "请先新建对话"}
          value={draft}
          onChangeText={setDraft}
          multiline
          editable={!!state.conversation_id}
        />
        {running ? (
          <Pressable style={[styles.send, { backgroundColor: colors.danger }]} onPress={() => void stop()} accessibilityLabel="停止">
            <Ionicons name="stop" size={18} color="#fff" />
          </Pressable>
        ) : (
          <Pressable style={[styles.send, !draft.trim() && { opacity: 0.4 }]} disabled={!draft.trim()} onPress={() => void send()} accessibilityLabel="发送">
            <Ionicons name="arrow-up" size={20} color="#fff" />
          </Pressable>
        )}
      </View>

      <Modal visible={pickerOpen} animationType="slide" onRequestClose={() => setPickerOpen(false)}>
        <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
          <View style={styles.pickerHead}>
            <Text style={styles.pickerTitle}>历史对话</Text>
            <Pressable hitSlop={10} onPress={() => setPickerOpen(false)}><Ionicons name="close" size={24} color={colors.text} /></Pressable>
          </View>
          <FlatList
            data={items}
            keyExtractor={(item) => item.id}
            ListEmptyComponent={<Empty text="暂无对话" />}
            renderItem={({ item }) => (
              <Pressable style={[styles.pickerItem, item.id === state.conversation_id && { backgroundColor: colors.primarySoft }]} onPress={() => void switchTo(() => agentApi.select(item.id))}>
                <Text style={styles.pickerItemTitle} numberOfLines={1}>{item.title || "新对话"}</Text>
                <Text style={styles.pickerItemMeta}>{item.message_count} 条消息 · {String(item.updated_at || "").replace("T", " ").slice(0, 16)}</Text>
              </Pressable>
            )}
          />
        </SafeAreaView>
      </Modal>
    </KeyboardAvoidingView>
  );
}

function MessageBubble({ item, streaming }: { item: WorkspaceMessage; streaming: boolean }) {
  if (item.role === "user") {
    return (
      <View style={[styles.bubble, styles.user]}>
        <Text style={styles.userText} selectable>{item.content}</Text>
      </View>
    );
  }
  return (
    <View style={[styles.bubble, styles.assistant, item.failed && styles.failed]}>
      {item.content ? <Markdown content={item.content} color={item.failed ? colors.danger : colors.text} /> : streaming ? <ActivityIndicator color={colors.primary} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  headerActions: { flexDirection: "row", gap: 18, marginRight: 14 },
  bubble: { maxWidth: "88%", borderRadius: 12, padding: 10, marginVertical: 5 },
  user: { alignSelf: "flex-end", backgroundColor: colors.primary },
  userText: { color: "#fff", fontSize: 15, lineHeight: 22 },
  assistant: { alignSelf: "flex-start", backgroundColor: colors.surface, borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  failed: { borderColor: colors.danger },
  progress: { color: colors.textMuted, fontSize: 13, marginVertical: 6 },
  action: { backgroundColor: "#fff8ec", borderColor: colors.warning, borderWidth: 1, borderRadius: 10, padding: 12, marginTop: 8 },
  actionTitle: { fontWeight: "700", color: colors.warning, marginBottom: 4 },
  actionSummary: { color: colors.text, lineHeight: 20 },
  actionHint: { color: colors.textSecondary, marginTop: 8 },
  actionButtons: { flexDirection: "row", gap: 10, marginTop: 10 },
  composer: { flexDirection: "row", alignItems: "flex-end", padding: 8, gap: 8, backgroundColor: colors.surface, borderTopWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  input: { flex: 1, maxHeight: 120, minHeight: 40, backgroundColor: colors.background, borderRadius: 20, paddingHorizontal: 14, paddingTop: 10, paddingBottom: 10, fontSize: 15, color: colors.text },
  send: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" },
  pickerHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 16 },
  pickerTitle: { fontSize: 18, fontWeight: "700", color: colors.text },
  pickerItem: { paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderColor: colors.border, backgroundColor: colors.surface },
  pickerItemTitle: { fontSize: 15, color: colors.text },
  pickerItemMeta: { fontSize: 12, color: colors.textMuted, marginTop: 3 },
});
