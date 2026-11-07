// 501742：带时间的日期选择（DatePicker showTime）统一用这组属性。手机上面板默认约 460px 宽，会超出屏幕，
// 样式 .oa-datetime-popup 在窄屏改成上下排并固定在屏幕内。面板仍挂在页面容器里，缓存页签隐藏时一起隐藏。
export const DATETIME_POPUP_PROPS = {
  classNames: { popup: { root: "oa-datetime-popup" } },
};
