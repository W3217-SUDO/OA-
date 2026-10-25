import { Alert, StyleSheet, Text, View } from "react-native";
import { Button, Card, Field } from "@/components/ui";
import { API_BASE_URL, APP_VERSION } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { colors } from "@/lib/theme";

export default function MeScreen() {
  const { user, logout } = useAuth();
  return (
    <View style={styles.page}>
      <Card>
        <Text style={styles.name}>{user?.display_name || user?.username}</Text>
        <Field label="账号" value={user?.username} />
        <Field label="部门" value={user?.department} />
      </Card>
      <Card>
        <Field label="App 版本" value={APP_VERSION} />
        <Field label="服务器" value={API_BASE_URL.replace(/\/api\/v1$/, "")} />
      </Card>
      <View style={styles.actions}>
        <Button
          title="退出登录"
          kind="danger"
          onPress={() => Alert.alert("退出登录", "确定退出当前账号吗？", [{ text: "取消", style: "cancel" }, { text: "退出", style: "destructive", onPress: () => void logout() }])}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  name: { fontSize: 20, fontWeight: "700", color: colors.text, marginBottom: 6 },
  actions: { flexDirection: "row", margin: 12, marginTop: 24 },
});
