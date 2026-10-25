import type { ExpoConfig } from "expo/config";

// 默认连生产；本地联调时用 EXPO_PUBLIC_API_BASE_URL 指向开发后端（模拟器里是 http://10.0.2.2:8000/api/v1）。
const apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL || "https://huzhilawfirm.com/api/v1";
const allowCleartext = apiBaseUrl.startsWith("http://");

const config: ExpoConfig = {
  name: "沪知 OA",
  slug: "huzhi-oa",
  version: "0.1.0",
  scheme: "huzhioa",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "light",
  ios: {
    bundleIdentifier: "com.huzhilawfirm.oa",
    supportsTablet: false,
  },
  android: {
    package: "com.huzhilawfirm.oa",
    versionCode: 1,
    adaptiveIcon: {
      backgroundColor: "#ffffff",
      foregroundImage: "./assets/android-icon-foreground.png",
    },
    predictiveBackGestureEnabled: false,
  },
  plugins: [
    "expo-router",
    ["expo-splash-screen", { image: "./assets/splash-icon.png", imageWidth: 160, backgroundColor: "#ffffff" }],
    "expo-secure-store",
    ["expo-build-properties", { android: { usesCleartextTraffic: allowCleartext } }],
  ],
  extra: { apiBaseUrl },
};

export default config;
