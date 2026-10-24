import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ConfigProvider, theme as antdTheme, type ThemeConfig } from "antd";
import zhCN from "antd/locale/zh_CN";

// 主题模式：auto 按本地时间在白天/夜间之间切换（07:00–18:30 为白天），system 跟随操作系统。
export type ThemeMode = "auto" | "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";
export type SidebarStyle = "light" | "dark";
export type HeaderStyle = "primary" | "light";

export type ThemePreset = { key: string; label: string; light: string; dark: string };

// 主题色预设：白天用饱和色，夜间换成同色系的浅一档，保证深色背景上对比度。
export const THEME_PRESETS: ThemePreset[] = [
  { key: "classic", label: "经典绿", light: "#00a65a", dark: "#2fbf7f" },
  { key: "blue", label: "科技蓝", light: "#2563eb", dark: "#4f86f7" },
  { key: "navy", label: "藏青", light: "#1e3a8a", dark: "#6b8be0" },
  { key: "ink", label: "墨黑", light: "#18181b", dark: "#e4e4e7" },
  { key: "green", label: "松绿", light: "#0f766e", dark: "#2dd4bf" },
  { key: "violet", label: "紫罗兰", light: "#6d28d9", dark: "#a78bfa" },
  { key: "rose", label: "绛红", light: "#be123c", dark: "#fb7185" },
  { key: "amber", label: "琥珀", light: "#b45309", dark: "#f59e0b" },
];

// 主题方案：一次性设置主题色、顶栏和侧栏，用户也可以在方案基础上单独微调。
export type ThemeScheme = { key: string; label: string; preset: string; header: HeaderStyle; sidebar: SidebarStyle };
export const THEME_SCHEMES: ThemeScheme[] = [
  { key: "classic", label: "经典绿", preset: "classic", header: "primary", sidebar: "dark" },
  { key: "business", label: "商务蓝", preset: "blue", header: "light", sidebar: "dark" },
  { key: "navy", label: "藏青", preset: "navy", header: "primary", sidebar: "dark" },
  { key: "minimal", label: "简约白", preset: "ink", header: "light", sidebar: "light" },
  { key: "teal", label: "松石", preset: "green", header: "light", sidebar: "light" },
  { key: "violet", label: "雅紫", preset: "violet", header: "primary", sidebar: "dark" },
];

type ThemePrefs = { mode: ThemeMode; preset: string; sidebar: SidebarStyle; header: HeaderStyle };

const STORAGE_KEY = "oa:theme-prefs";
const LEGACY_MODE_KEY = "oa:theme-mode";
const DEFAULT_PREFS: ThemePrefs = { mode: "light", preset: "classic", sidebar: "dark", header: "primary" };
const DAY_START_MINUTES = 7 * 60;
const NIGHT_START_MINUTES = 18 * 60 + 30;

const neutral = {
  light: {
    bg: "#f5f6f8",
    surface: "#ffffff",
    elevated: "#ffffff",
    fill: "#f4f4f5",
    border: "#e4e4e7",
    borderStrong: "#d4d4d8",
    text: "#18181b",
    textSecondary: "#52525b",
  },
  dark: {
    bg: "#09090b",
    surface: "#111113",
    elevated: "#18181b",
    fill: "#1c1c1f",
    border: "#27272a",
    borderStrong: "#3f3f46",
    text: "#fafafa",
    textSecondary: "#a1a1aa",
  },
} as const;

function isMode(value: unknown): value is ThemeMode {
  return value === "auto" || value === "system" || value === "light" || value === "dark";
}

function readStoredPrefs(): ThemePrefs {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const value = JSON.parse(raw) as Partial<ThemePrefs>;
      return {
        mode: isMode(value.mode) ? value.mode : DEFAULT_PREFS.mode,
        preset: THEME_PRESETS.some((item) => item.key === value.preset) ? String(value.preset) : DEFAULT_PREFS.preset,
        sidebar: value.sidebar === "light" ? "light" : "dark",
        header: value.header === "light" ? "light" : "primary",
      };
    }
    const legacyMode = localStorage.getItem(LEGACY_MODE_KEY);
    if (isMode(legacyMode)) return { ...DEFAULT_PREFS, mode: legacyMode };
  } catch {
    // 隐私模式等场景下读不到存储，使用默认偏好。
  }
  return DEFAULT_PREFS;
}

function resolveByClock(now = new Date()): ResolvedTheme {
  const minutes = now.getHours() * 60 + now.getMinutes();
  return minutes >= DAY_START_MINUTES && minutes < NIGHT_START_MINUTES ? "light" : "dark";
}

function resolveMode(mode: ThemeMode): ResolvedTheme {
  if (mode === "light" || mode === "dark") return mode;
  if (mode === "system") return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  return resolveByClock();
}

function presetColor(presetKey: string, resolved: ResolvedTheme) {
  const preset = THEME_PRESETS.find((item) => item.key === presetKey) ?? THEME_PRESETS[0];
  return preset[resolved];
}

function mixHex(color: string, base: string, weight: number) {
  const parse = (hex: string) => [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
  const a = parse(color);
  const b = parse(base);
  return `#${a.map((value, index) => Math.round(value * weight + b[index] * (1 - weight)).toString(16).padStart(2, "0")).join("")}`;
}

export function buildAntdTheme(resolved: ResolvedTheme, primary: string): ThemeConfig {
  const c = neutral[resolved];
  const dark = resolved === "dark";
  // 墨黑预设在夜间是浅色按钮，实底按钮上的文字要反成深色。
  const lightPrimary = dark && primary === "#e4e4e7";
  const primarySoft = mixHex(primary, c.surface, dark ? 0.18 : 0.09);
  const primarySoftHover = mixHex(primary, c.surface, dark ? 0.24 : 0.14);
  return {
    algorithm: dark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      colorPrimary: primary,
      colorInfo: primary,
      colorLink: primary,
      colorSuccess: dark ? "#22c55e" : "#16a34a",
      colorWarning: dark ? "#f59e0b" : "#d97706",
      colorError: dark ? "#f87171" : "#dc2626",
      colorTextLightSolid: lightPrimary ? "#18181b" : "#ffffff",
      colorBgLayout: c.bg,
      colorBgContainer: c.surface,
      colorBgElevated: c.elevated,
      colorBorder: c.borderStrong,
      colorBorderSecondary: c.border,
      colorSplit: c.border,
      colorText: c.text,
      colorTextSecondary: c.textSecondary,
      colorTextTertiary: dark ? "#71717a" : "#a1a1aa",
      colorFillAlter: c.fill,
      colorPrimaryBg: primarySoft,
      colorPrimaryBgHover: primarySoftHover,
      controlItemBgActive: primarySoft,
      controlItemBgActiveHover: primarySoftHover,
      controlItemBgHover: c.fill,
      controlOutline: mixHex(primary, c.surface, 0.22),
      borderRadius: 8,
      borderRadiusSM: 6,
      borderRadiusLG: 12,
      fontSize: 13,
      fontFamily:
        'Inter, -apple-system, BlinkMacSystemFont, "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "Helvetica Neue", Arial, sans-serif',
      controlHeight: 32,
      boxShadow: dark
        ? "0 8px 24px rgba(0,0,0,.5), 0 1px 3px rgba(0,0,0,.4)"
        : "0 8px 24px rgba(24,24,27,.08), 0 1px 3px rgba(24,24,27,.06)",
      boxShadowSecondary: dark
        ? "0 16px 40px rgba(0,0,0,.6), 0 2px 8px rgba(0,0,0,.4)"
        : "0 16px 40px rgba(24,24,27,.12), 0 2px 8px rgba(24,24,27,.06)",
      motionDurationMid: "0.18s",
      zIndexPopupBase: 1300,
    },
    components: {
      Button: {
        fontWeight: 500,
        primaryShadow: "none",
        defaultShadow: "none",
        dangerShadow: "none",
        paddingInline: 14,
      },
      Card: {
        headerBg: "transparent",
        headerFontSize: 15,
        headerHeight: 48,
        bodyPadding: 16,
        headerPadding: 16,
      },
      Table: {
        headerBg: c.fill,
        headerColor: c.textSecondary,
        headerSplitColor: "transparent",
        rowHoverBg: c.fill,
        borderColor: c.border,
        cellPaddingBlock: 12,
        cellPaddingBlockMD: 10,
        cellPaddingBlockSM: 7,
      },
      Modal: {
        titleFontSize: 16,
        headerBg: "transparent",
        contentBg: c.elevated,
        footerBg: "transparent",
      },
      Drawer: { colorBgElevated: c.elevated },
      Tabs: { itemSelectedColor: primary, inkBarColor: primary },
      Menu: {
        itemBg: "transparent",
        subMenuItemBg: "transparent",
        itemColor: c.textSecondary,
        itemHoverColor: c.text,
        itemHoverBg: c.fill,
        itemSelectedBg: primarySoft,
        itemSelectedColor: primary,
        itemActiveBg: c.fill,
        darkItemBg: "transparent",
        // 深色侧栏沿用原系统配色：#222d32 底、#2c3b41 子菜单、#1e282c 选中。
        darkSubMenuItemBg: dark ? "transparent" : "#2c3b41",
        darkPopupBg: dark ? "#18181b" : "#222d32",
        darkItemColor: dark ? "rgba(244,244,245,.66)" : "#b8c7ce",
        darkItemHoverColor: "#ffffff",
        darkItemHoverBg: dark ? "rgba(255,255,255,.06)" : "#1e282c",
        darkItemSelectedBg: dark ? "rgba(255,255,255,.1)" : "#1e282c",
        darkItemSelectedColor: "#ffffff",
        itemBorderRadius: 8,
        itemMarginInline: 8,
        itemHeight: 38,
        subMenuItemBorderRadius: 8,
        iconSize: 15,
      },
      Tag: { borderRadiusSM: 6 },
      Segmented: { itemSelectedBg: c.surface, trackBg: c.fill },
      Tooltip: { colorBgSpotlight: dark ? "#27272a" : "#18181b" },
    },
  };
}

type ThemeModeContextValue = {
  mode: ThemeMode;
  resolved: ResolvedTheme;
  preset: string;
  primary: string;
  sidebar: SidebarStyle;
  header: HeaderStyle;
  setMode: (mode: ThemeMode, origin?: { x: number; y: number }) => void;
  setPreset: (preset: string) => void;
  setSidebar: (sidebar: SidebarStyle) => void;
  setHeader: (header: HeaderStyle) => void;
  applyScheme: (scheme: ThemeScheme) => void;
};

const ThemeModeContext = createContext<ThemeModeContextValue>({
  mode: DEFAULT_PREFS.mode,
  resolved: "light",
  preset: DEFAULT_PREFS.preset,
  primary: THEME_PRESETS[0].light,
  sidebar: DEFAULT_PREFS.sidebar,
  header: DEFAULT_PREFS.header,
  setMode: () => undefined,
  setPreset: () => undefined,
  setSidebar: () => undefined,
  setHeader: () => undefined,
  applyScheme: () => undefined,
});

export function useThemeMode() {
  return useContext(ThemeModeContext);
}

type ViewTransitionDocument = Document & {
  startViewTransition?: (callback: () => void) => { ready: Promise<void> };
};

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// 白天/夜间切换时颜色渐变：支持 View Transition 的浏览器从点击处圆形扩散，其余浏览器整体颜色过渡。
function runThemeTransition(apply: () => void, origin?: { x: number; y: number }) {
  const root = document.documentElement;
  if (prefersReducedMotion()) {
    apply();
    return;
  }
  const doc = document as ViewTransitionDocument;
  if (doc.startViewTransition) {
    const x = origin?.x ?? window.innerWidth / 2;
    const y = origin?.y ?? 0;
    const radius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    root.dataset.themeSwitching = "reveal";
    const transition = doc.startViewTransition(apply);
    transition.ready
      .then(() => {
        root.animate(
          { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
          { duration: 600, easing: "cubic-bezier(.22,.8,.26,1)", pseudoElement: "::view-transition-new(root)" },
        );
      })
      .catch(() => undefined);
    window.setTimeout(() => delete root.dataset.themeSwitching, 700);
    return;
  }
  root.dataset.themeSwitching = "fade";
  apply();
  window.setTimeout(() => delete root.dataset.themeSwitching, 650);
}

function applyDocumentTheme(resolved: ResolvedTheme, primary: string, sidebar: SidebarStyle, header: HeaderStyle) {
  const root = document.documentElement;
  root.dataset.theme = resolved;
  root.dataset.sidebar = sidebar;
  root.dataset.header = header;
  root.style.colorScheme = resolved;
  root.style.setProperty("--oa-primary", primary);
  const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (meta) meta.content = resolved === "light" && header === "primary" ? primary : neutral[resolved].surface;
}

function writePrefs(prefs: ThemePrefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // 存不下也不影响本次切换。
  }
}

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<ThemePrefs>(readStoredPrefs);
  const [resolved, setResolved] = useState<ResolvedTheme>(() => resolveMode(readStoredPrefs().mode));
  const primary = presetColor(prefs.preset, resolved);

  // 首帧同步，避免 CSS 变量先按默认渲染再闪成用户偏好。
  const root = document.documentElement;
  if (
    root.dataset.theme !== resolved
    || root.dataset.sidebar !== prefs.sidebar
    || root.dataset.header !== prefs.header
    || root.style.getPropertyValue("--oa-primary") !== primary
  ) {
    applyDocumentTheme(resolved, primary, prefs.sidebar, prefs.header);
  }

  const switchResolved = useCallback((nextResolved: ResolvedTheme, origin?: { x: number; y: number }) => {
    if (nextResolved === document.documentElement.dataset.theme) return;
    runThemeTransition(() => {
      document.documentElement.dataset.theme = nextResolved;
      setResolved(nextResolved);
    }, origin);
  }, []);

  const setMode = useCallback((mode: ThemeMode, origin?: { x: number; y: number }) => {
    setPrefs((current) => {
      const next = { ...current, mode };
      writePrefs(next);
      return next;
    });
    switchResolved(resolveMode(mode), origin);
  }, [switchResolved]);

  const setPreset = useCallback((preset: string) => {
    setPrefs((current) => {
      const next = { ...current, preset };
      writePrefs(next);
      return next;
    });
  }, []);

  const setSidebar = useCallback((sidebar: SidebarStyle) => {
    setPrefs((current) => {
      const next = { ...current, sidebar };
      writePrefs(next);
      return next;
    });
  }, []);

  const setHeader = useCallback((header: HeaderStyle) => {
    setPrefs((current) => {
      const next = { ...current, header };
      writePrefs(next);
      return next;
    });
  }, []);

  const applyScheme = useCallback((scheme: ThemeScheme) => {
    setPrefs((current) => {
      const next = { ...current, preset: scheme.preset, header: scheme.header, sidebar: scheme.sidebar };
      writePrefs(next);
      return next;
    });
  }, []);

  // 自动模式每分钟对一次时钟；跟随系统时监听系统明暗变化。到点切换时用整体颜色渐变。
  useEffect(() => {
    const { mode } = prefs;
    if (mode === "light" || mode === "dark") return;
    const sync = () => switchResolved(resolveMode(mode));
    if (mode === "system") {
      const query = window.matchMedia("(prefers-color-scheme: dark)");
      query.addEventListener("change", sync);
      return () => query.removeEventListener("change", sync);
    }
    const timer = window.setInterval(sync, 60_000);
    document.addEventListener("visibilitychange", sync);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", sync);
    };
  }, [prefs, switchResolved]);

  const themeConfig = useMemo(() => buildAntdTheme(resolved, primary), [resolved, primary]);

  // Modal.confirm / message 等静态方法渲染在 React 树外，需要单独套上当前主题。
  useEffect(() => {
    ConfigProvider.config({
      holderRender: (children) => (
        <ConfigProvider locale={zhCN} theme={themeConfig}>
          {children}
        </ConfigProvider>
      ),
    });
  }, [themeConfig]);

  const value = useMemo(
    () => ({
      mode: prefs.mode,
      resolved,
      preset: prefs.preset,
      primary,
      sidebar: prefs.sidebar,
      header: prefs.header,
      setMode,
      setPreset,
      setSidebar,
      setHeader,
      applyScheme,
    }),
    [prefs, resolved, primary, setMode, setPreset, setSidebar, setHeader, applyScheme],
  );

  return (
    <ThemeModeContext.Provider value={value}>
      <ConfigProvider locale={zhCN} theme={themeConfig}>
        {children}
      </ConfigProvider>
    </ThemeModeContext.Provider>
  );
}
