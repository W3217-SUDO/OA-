import Ionicons from "@expo/vector-icons/Ionicons";
import { useQuery } from "@tanstack/react-query";
import { Tabs } from "expo-router";
import type { ColorValue } from "react-native";
import { api } from "@/lib/api";
import { colors } from "@/lib/theme";
import type { Paged, TaskRow } from "@/lib/types";

type IconName = React.ComponentProps<typeof Ionicons>["name"];
type IconProps = { color: ColorValue; size: number };
// tabBarIcon 的 color 类型含 null，Ionicons 只接受字符串颜色。
function TabIcon({ name, color, size }: IconProps & { name: IconName }) {
  return <Ionicons name={name} color={String(color)} size={size} />;
}
const icon = (name: IconName) => function TabBarIcon(props: IconProps) {
  return <TabIcon name={name} {...props} />;
};

export default function TabsLayout() {
  // 与网页底部导航一致：任务角标取未读任务消息数。
  const unread = useQuery({
    queryKey: ["tasks", "unread-count"],
    queryFn: () => api.get<Paged<TaskRow>>("/tasks/unread-messages", { page: 1, page_size: 1 }),
    refetchInterval: 60_000,
  });
  const unreadTotal = unread.data?.total || 0;

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.primary },
        headerTintColor: "#fff",
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
      }}
    >
      <Tabs.Screen name="agent" options={{ title: "智能体", tabBarIcon: icon("sparkles-outline") }} />
      <Tabs.Screen name="cases" options={{ title: "案件", tabBarIcon: icon("briefcase-outline") }} />
      <Tabs.Screen
        name="tasks"
        options={{ title: "我的任务", tabBarIcon: icon("checkbox-outline"), tabBarBadge: unreadTotal ? (unreadTotal > 99 ? "99+" : unreadTotal) : undefined }}
      />
      <Tabs.Screen name="me" options={{ title: "我的", tabBarIcon: icon("person-outline") }} />
    </Tabs>
  );
}
