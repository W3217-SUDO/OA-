import { ActivityIndicator, Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from "react-native";
import { colors, statusTone } from "@/lib/theme";

export function Tag({ label }: { label: string }) {
  const tone = statusTone[label] || colors.textSecondary;
  return (
    <View style={[styles.tag, { borderColor: tone }]}>
      <Text style={[styles.tagText, { color: tone }]}>{label}</Text>
    </View>
  );
}

export function Card({ children, style, onPress }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void }) {
  if (!onPress) return <View style={[styles.card, style]}>{children}</View>;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.card, pressed && styles.pressed, style]}>
      {children}
    </Pressable>
  );
}

export function Field({ label, value }: { label: string; value?: unknown }) {
  const text = value === undefined || value === null || String(value).trim() === "" ? "—" : String(value);
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Text style={styles.fieldValue} selectable>{text}</Text>
    </View>
  );
}

export function Button({ title, onPress, kind = "primary", disabled, loading }: { title: string; onPress: () => void; kind?: "primary" | "ghost" | "danger"; disabled?: boolean; loading?: boolean }) {
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [styles.button, styles[kind], inactive && styles.disabled, pressed && styles.pressed]}
    >
      {loading ? <ActivityIndicator color={kind === "primary" ? "#fff" : colors.primary} /> : <Text style={[styles.buttonText, kind !== "primary" && { color: kind === "danger" ? colors.danger : colors.primary }]}>{title}</Text>}
    </Pressable>
  );
}

export function Empty({ text }: { text: string }) {
  return <Text style={styles.empty}>{text}</Text>;
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={styles.error}>
      <Text style={styles.errorText}>{message}</Text>
      {onRetry && <Text style={styles.retry} onPress={onRetry}>重试</Text>}
    </View>
  );
}

export function personName(displayName?: string | null, fallback?: string | null) {
  return String(displayName || "").trim() || String(fallback || "").trim() || "—";
}

const styles = StyleSheet.create({
  tag: { borderWidth: 1, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 1, alignSelf: "flex-start" },
  tagText: { fontSize: 12 },
  card: { backgroundColor: colors.surface, borderRadius: 10, padding: 14, marginHorizontal: 12, marginTop: 10, borderWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  pressed: { opacity: 0.7 },
  field: { flexDirection: "row", paddingVertical: 6 },
  fieldLabel: { width: 88, color: colors.textSecondary, fontSize: 14 },
  fieldValue: { flex: 1, color: colors.text, fontSize: 14 },
  button: { height: 44, borderRadius: 8, alignItems: "center", justifyContent: "center", paddingHorizontal: 16, flex: 1 },
  primary: { backgroundColor: colors.primary },
  ghost: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.primary },
  danger: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.danger },
  disabled: { opacity: 0.5 },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  empty: { textAlign: "center", color: colors.textMuted, marginTop: 48, fontSize: 14 },
  error: { flexDirection: "row", backgroundColor: "#fdeceb", margin: 12, padding: 10, borderRadius: 8, alignItems: "center" },
  errorText: { flex: 1, color: colors.danger },
  retry: { color: colors.primary, fontWeight: "600", marginLeft: 12 },
});
