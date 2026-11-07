// 501742：带时间的日期选择（DatePicker showTime）统一用这组属性。手机上面板默认约 460px 宽，会超出屏幕，
// 样式 .oa-datetime-popup 在窄屏改成上下排并固定在屏幕内；挂到 body，页面容器的 transform 才不影响定位。
export const DATETIME_POPUP_PROPS = {
  classNames: { popup: { root: "oa-datetime-popup" } },
  getPopupContainer: () => document.body,
};
