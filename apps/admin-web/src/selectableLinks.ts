// 10.26 第2行：蓝色可跳转字段（type="link" 按钮）要能拖选复制。
// 按钮文字默认不可选；样式放开后，拖选松开时浏览器仍会派发 click，这里在捕获阶段拦下：
// 只有“按下后拖动过且选中了文字”才视为复制操作，其余单击照常跳转。
const LINK_SELECTOR = ".ant-btn-variant-link, .ant-btn-link";
const DRAG_DISTANCE = 4;

export function installSelectableLinks(doc: Document = document): void {
  let pressed: { x: number; y: number } | null = null;
  doc.addEventListener("mousedown", (event) => { pressed = { x: event.clientX, y: event.clientY }; }, true);
  doc.addEventListener(
    "click",
    (event) => {
      const start = pressed;
      pressed = null;
      const link = (event.target as Element | null)?.closest?.(LINK_SELECTOR);
      if (!link || !start) return;
      if (Math.hypot(event.clientX - start.x, event.clientY - start.y) < DRAG_DISTANCE) return;
      const selection = doc.getSelection?.();
      if (!selection || selection.isCollapsed || !selection.toString().trim()) return;
      event.preventDefault();
      event.stopPropagation();
    },
    true,
  );
}
