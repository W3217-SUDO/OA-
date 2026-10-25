/**
 * 弹窗（Modal）和侧滑（Drawer）共用的四档宽度，单位 px。
 * 新页面只从这里选；手机端由 styles.css 统一改成全屏宽，这里只管电脑端。
 * 弹窗写 width={POPUP_WIDTH.md}，侧滑写 size={POPUP_WIDTH.md}（antd 6 的 Drawer 已不推荐 width）。
 */
export const POPUP_WIDTH = {
  /** 确认、填原因、少量字段 */
  sm: 520,
  /** 常规新增、编辑、详情 */
  md: 760,
  /** 分组表单、带明细表 */
  lg: 960,
  /** 多栏复杂编辑，尽量少用 */
  xl: 1200,
} as const;

export type PopupWidth = (typeof POPUP_WIDTH)[keyof typeof POPUP_WIDTH];
