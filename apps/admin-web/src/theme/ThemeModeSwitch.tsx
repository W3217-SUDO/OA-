import { useState } from "react";
import { Button, Drawer, Segmented, Tooltip } from "antd";
import { BgColorsOutlined, CheckOutlined, MoonOutlined, SettingOutlined, SunOutlined } from "@ant-design/icons";
import { THEME_PRESETS, THEME_SCHEMES, useThemeMode, type HeaderStyle, type SidebarStyle, type ThemeMode } from "./ThemeModeProvider";

const MODE_OPTIONS: { value: ThemeMode; label: string }[] = [
  { value: "light", label: "白天" },
  { value: "dark", label: "夜间" },
  { value: "auto", label: "随时间" },
  { value: "system", label: "跟随系统" },
];

// 顶栏的白天/夜间一键切换：从按钮位置圆形扩散过渡。
export default function ThemeModeSwitch({ className }: { className?: string }) {
  const { resolved, setMode } = useThemeMode();
  const title = resolved === "dark" ? "切换到白天" : "切换到夜间";
  return (
    <Tooltip title={title}>
      <Button
        type="text"
        className={`theme-mode-switch ${className ?? ""}`}
        aria-label={title}
        onClick={(event) => setMode(resolved === "dark" ? "light" : "dark", { x: event.clientX, y: event.clientY })}
        icon={
          <span className={`theme-mode-glyph is-${resolved}`} aria-hidden="true">
            <SunOutlined className="theme-mode-sun" />
            <MoonOutlined className="theme-mode-moon" />
          </span>
        }
      />
    </Tooltip>
  );
}

// compact：手机顶栏用调色板图标，抽屉宽度不超过屏幕的 88%。
export function ThemeSettingsButton({ compact = false }: { compact?: boolean }) {
  const { mode, preset, sidebar, header, setMode, setPreset, setSidebar, setHeader, applyScheme } = useThemeMode();
  const [open, setOpen] = useState(false);
  return (
    <>
      <Tooltip title={compact ? "主题与外观" : "偏好设置"}>
        <Button type="text" aria-label={compact ? "主题与外观" : "偏好设置"} icon={compact ? <BgColorsOutlined /> : <SettingOutlined />} onClick={() => setOpen(true)} />
      </Tooltip>
      <Drawer
        title="偏好设置"
        open={open}
        onClose={() => setOpen(false)}
        size={compact ? "min(340px, 88vw)" : 340}
        rootClassName="theme-settings-drawer"
      >
        <section className="theme-settings-section">
          <h4>外观</h4>
          <div className="theme-appearance-grid">
            {MODE_OPTIONS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={`theme-appearance-card is-${item.value}${mode === item.value ? " is-active" : ""}`}
                aria-pressed={mode === item.value}
                onClick={(event) => setMode(item.value, { x: event.clientX, y: event.clientY })}
              >
                <span className="theme-appearance-preview" aria-hidden="true">
                  <i />
                  <b />
                </span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
          {mode === "auto" && <p className="theme-settings-hint">07:00 自动切到白天，18:30 自动切到夜间，颜色渐变过渡。</p>}
        </section>
        <section className="theme-settings-section">
          <h4>主题方案</h4>
          <div className="theme-scheme-grid">
            {THEME_SCHEMES.map((scheme) => {
              const color = THEME_PRESETS.find((item) => item.key === scheme.preset)?.light ?? "#00a65a";
              const active = scheme.preset === preset && scheme.header === header && scheme.sidebar === sidebar;
              return (
                <button
                  key={scheme.key}
                  type="button"
                  className={`theme-scheme-card${active ? " is-active" : ""}`}
                  aria-pressed={active}
                  onClick={() => applyScheme(scheme)}
                >
                  <span
                    className={`theme-scheme-preview header-${scheme.header} sidebar-${scheme.sidebar}`}
                    style={{ ["--scheme-color" as string]: color }}
                    aria-hidden="true"
                  >
                    <i className="theme-scheme-top" />
                    <i className="theme-scheme-side" />
                    <i className="theme-scheme-body" />
                  </span>
                  <span>{scheme.label}</span>
                  {active && <CheckOutlined className="theme-scheme-check" />}
                </button>
              );
            })}
          </div>
        </section>
        <section className="theme-settings-section">
          <h4>主题色</h4>
          <div className="theme-swatch-grid">
            {THEME_PRESETS.map((item) => (
              <Tooltip key={item.key} title={item.label}>
                <button
                  type="button"
                  className={`theme-swatch${preset === item.key ? " is-active" : ""}`}
                  style={{ background: item.light }}
                  aria-label={`主题色：${item.label}`}
                  aria-pressed={preset === item.key}
                  onClick={() => setPreset(item.key)}
                >
                  {preset === item.key && <CheckOutlined />}
                </button>
              </Tooltip>
            ))}
          </div>
        </section>
        <section className="theme-settings-section">
          <h4>顶栏</h4>
          <Segmented
            block
            value={header}
            onChange={(value) => setHeader(value as HeaderStyle)}
            options={[
              { value: "primary", label: "主题色" },
              { value: "light", label: "白色" },
            ]}
          />
        </section>
        <section className="theme-settings-section">
          <h4>侧边栏</h4>
          <Segmented
            block
            value={sidebar}
            onChange={(value) => setSidebar(value as SidebarStyle)}
            options={[
              { value: "light", label: "浅色" },
              { value: "dark", label: "深色" },
            ]}
          />
        </section>
      </Drawer>
    </>
  );
}
