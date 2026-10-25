import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { ActivityIndicator, View } from "react-native";
import { ApiError } from "@/lib/api";
import { AuthProvider, useAuth } from "@/lib/auth";
import { colors } from "@/lib/theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // 权限或登录类错误重试没有意义。
      retry: (count, error) => count < 2 && !(error instanceof ApiError && [401, 403, 404].includes(error.status)),
    },
  },
});

function AuthGate() {
  const { ready, user } = useAuth();

  useEffect(() => {
    if (!user) queryClient.clear();
  }, [user]);

  if (!ready) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background }}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.primary },
        headerTintColor: "#fff",
        headerBackTitle: "返回",
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      {/* 未登录时受保护页面不挂载，避免无 token 先发请求。 */}
      <Stack.Protected guard={!!user}>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="case/[id]" options={{ title: "案件详情" }} />
        <Stack.Screen name="task/[id]" options={{ title: "任务详情" }} />
      </Stack.Protected>
      <Stack.Protected guard={!user}>
        <Stack.Screen name="login" options={{ headerShown: false }} />
      </Stack.Protected>
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <StatusBar style="light" />
        <AuthGate />
      </AuthProvider>
    </QueryClientProvider>
  );
}
