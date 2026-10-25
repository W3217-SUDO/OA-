import { useState } from "react";
import { KeyboardAvoidingView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Button, ErrorBanner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { colors } from "@/lib/theme";

export default function LoginScreen() {
  const { login, changePassword } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mustChange, setMustChange] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const submitLogin = async () => {
    if (!username.trim() || !password) {
      setError("请输入账号和密码");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await login(username, password);
      if (result.must_change_password) setMustChange(true);
    } catch (e) {
      setError((e as Error).message || "登录失败");
    } finally {
      setBusy(false);
    }
  };

  const submitChange = async () => {
    if (newPassword.length < 8) {
      setError("新密码至少 8 位");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("两次输入的新密码不一致");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await changePassword(password, newPassword);
      setMustChange(false);
      setPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setNotice("密码已修改，请用新密码登录");
    } catch (e) {
      setError((e as Error).message || "修改密码失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.page}>
      <KeyboardAvoidingView behavior="padding" style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
        <Text style={styles.brand}>沪知 OA</Text>
        <Text style={styles.subtitle}>上海沪知律师事务所协作平台</Text>
        <View style={styles.form}>
          {mustChange ? (
            <>
              <Text style={styles.hint}>首次登录需要修改初始密码</Text>
              <TextInput style={styles.input} placeholder="新密码" secureTextEntry value={newPassword} onChangeText={setNewPassword} autoComplete="new-password" />
              <TextInput style={styles.input} placeholder="再次输入新密码" secureTextEntry value={confirmPassword} onChangeText={setConfirmPassword} autoComplete="new-password" />
              <View style={styles.row}><Button title="修改密码" onPress={submitChange} loading={busy} /></View>
            </>
          ) : (
            <>
              <TextInput style={styles.input} placeholder="OA 账号" autoCapitalize="none" autoCorrect={false} value={username} onChangeText={setUsername} autoComplete="username" />
              <TextInput style={styles.input} placeholder="密码" secureTextEntry value={password} onChangeText={setPassword} autoComplete="current-password" onSubmitEditing={submitLogin} />
              <View style={styles.row}><Button title="登录" onPress={submitLogin} loading={busy} /></View>
            </>
          )}
          {!!notice && <Text style={styles.notice}>{notice}</Text>}
        </View>
        {!!error && <ErrorBanner message={error} />}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.primary },
  body: { flexGrow: 1, justifyContent: "center", padding: 24 },
  brand: { color: "#fff", fontSize: 30, fontWeight: "700", textAlign: "center" },
  subtitle: { color: "#cfe0db", fontSize: 14, textAlign: "center", marginTop: 6, marginBottom: 32 },
  form: { backgroundColor: colors.surface, borderRadius: 12, padding: 20 },
  hint: { color: colors.textSecondary, marginBottom: 12 },
  input: { height: 46, borderWidth: 1, borderColor: colors.border, borderRadius: 8, paddingHorizontal: 12, fontSize: 16, marginBottom: 12, color: colors.text },
  row: { flexDirection: "row", marginTop: 4 },
  notice: { color: colors.success, marginTop: 12, textAlign: "center" },
});
