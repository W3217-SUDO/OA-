// 钉钉 Android 内置浏览器（Chrome 100）不支持 :has()。构建时（scripts/legacy-webview-css.mjs）把每条 A:has(B)
// 另写成 A.oa-has-<编号>，并在样式表里登记 .oa-has-<编号>{--oa-has:"A|B"}（只在不支持 :has 的浏览器生效）。
// 这里读出登记表，给满足条件的元素加上对应类名；页面结构或类名变化时（合并到下一帧）重新计算。
type Condition = { compound: string; relative: string };

export function installHasPolyfill() {
  if (typeof CSS === "undefined" || typeof CSS.supports !== "function" || CSS.supports("selector(:has(*))")) return;
  const conditions = new Map<string, Condition>();
  const seenSheets = new WeakSet<CSSStyleSheet>();

  const readRules = (rules: CSSRuleList) => {
    for (const rule of Array.from(rules)) {
      if (rule instanceof CSSStyleRule) {
        const match = /^\.(oa-has-[a-z0-9]+)$/.exec(rule.selectorText);
        if (!match || conditions.has(match[1])) continue;
        const raw = rule.style.getPropertyValue("--oa-has").trim().replace(/^["']|["']$/g, "");
        try {
          const text = decodeURIComponent(raw);
          const split = text.indexOf("|");
          if (split > 0) conditions.set(match[1], { compound: text.slice(0, split), relative: text.slice(split + 1) });
        } catch {
          // 登记格式不对时跳过这一条，不影响其他规则。
        }
      } else if ("cssRules" in rule) {
        readRules((rule as CSSGroupingRule).cssRules);
      }
    }
  };
  const readSheets = () => {
    for (const sheet of Array.from(document.styleSheets)) {
      if (seenSheets.has(sheet)) continue;
      try {
        readRules(sheet.cssRules);
        seenSheets.add(sheet);
      } catch {
        // 跨域样式表读不到规则，跳过。
      }
    }
  };

  let observer: MutationObserver | null = null;
  const apply = () => {
    readSheets();
    for (const [name, { compound, relative }] of conditions) {
      // “> .x” 这种以组合符开头的条件要从元素自身开始找。
      const query = /^[>+~]/.test(relative) ? `:scope ${relative}` : relative;
      let candidates: Element[];
      try {
        candidates = Array.from(document.querySelectorAll(compound));
      } catch {
        continue;
      }
      const matched = new Set<Element>();
      for (const element of candidates) {
        try {
          if (element.querySelector(query)) matched.add(element);
        } catch {
          break;
        }
      }
      document.querySelectorAll(`.${name}`).forEach((element) => {
        if (!matched.has(element)) element.classList.remove(name);
      });
      matched.forEach((element) => element.classList.add(name));
    }
    // 自己改类名产生的变化不再触发下一轮。
    observer?.takeRecords();
  };

  let frame = 0;
  const schedule = () => {
    if (frame) return;
    frame = window.requestAnimationFrame(() => {
      frame = 0;
      apply();
    });
  };
  observer = new MutationObserver(schedule);
  observer.observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ["class", "style"] });
  schedule();
}
