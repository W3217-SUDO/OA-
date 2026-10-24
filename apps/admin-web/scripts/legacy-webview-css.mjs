// 钉钉 Android 内置浏览器是 Chrome 100 内核，不认识 color-mix()、dvh 等新语法：整条声明被丢掉，
// 主题色推出来的颜色全部失效（头像变黑、图标透明、底栏没底色）。构建时给这些声明补上旧内核能用的回退：
// - 普通属性：在原声明前插一条算好的静态颜色；新浏览器仍以后面的 color-mix 为准。
// - 自定义属性（--x）：旧内核里 color-mix 要到使用时才失效，前置回退没用，改为在
//   @supports not (color: color-mix(...)) 里给同一选择器写静态值，只有旧内核会用到。
// - 夜间模式按夜间变量另算一份（只在旧内核、夜间生效）。
// - dvh/svh/lvh 前插一条 vh 版本。
import fs from 'node:fs';
import postcss from 'postcss';

export const LEGACY_SUPPORTS = 'not (color: color-mix(in srgb, red 50%, blue))';
export const LEGACY_HAS_SUPPORTS = 'not selector(:has(*))';
const DARK = '[data-theme="dark"]';

const NAMED = { transparent: [0, 0, 0, 0], white: [255, 255, 255, 1], black: [0, 0, 0, 1] };

export function parseColor(text) {
  const value = text.trim().toLowerCase();
  if (value in NAMED) return NAMED[value].slice();
  let match = /^#([0-9a-f]{3,8})$/.exec(value);
  if (match) {
    let hex = match[1];
    if (hex.length === 3 || hex.length === 4) hex = [...hex].map((char) => char + char).join('');
    if (hex.length !== 6 && hex.length !== 8) return null;
    const channels = [0, 2, 4].map((index) => parseInt(hex.slice(index, index + 2), 16));
    return [...channels, hex.length === 8 ? parseInt(hex.slice(6), 16) / 255 : 1];
  }
  match = /^rgba?\((.*)\)$/.exec(value);
  if (match) {
    const parts = match[1].split(/[\s,/]+/).filter(Boolean);
    if (parts.length < 3) return null;
    const channels = parts.slice(0, 3).map((part) => (part.endsWith('%') ? parseFloat(part) * 2.55 : parseFloat(part)));
    const alpha = parts[3] === undefined ? 1 : parts[3].endsWith('%') ? parseFloat(parts[3]) / 100 : parseFloat(parts[3]);
    if ([...channels, alpha].some(Number.isNaN)) return null;
    return [...channels, alpha];
  }
  return null;
}

export function formatColor([red, green, blue, alpha]) {
  const channels = [red, green, blue].map((channel) => Math.round(Math.min(255, Math.max(0, channel))));
  if (alpha >= 0.999) return `#${channels.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`;
  return `rgba(${channels.join(', ')}, ${Number(Math.max(0, alpha).toFixed(3))})`;
}

// 按 CSS Color 5 的 srgb 规则混色：百分比归一化、预乘透明度，两者之和不足 100% 时整体降低不透明度。
export function mixColors(first, firstPercent, second, secondPercent) {
  let p1 = firstPercent;
  let p2 = secondPercent;
  if (p1 == null && p2 == null) [p1, p2] = [50, 50];
  else if (p1 == null) p1 = 100 - p2;
  else if (p2 == null) p2 = 100 - p1;
  const sum = p1 + p2;
  if (sum <= 0) return null;
  const alphaScale = sum < 100 ? sum / 100 : 1;
  const w1 = p1 / sum;
  const w2 = p2 / sum;
  const alpha = first[3] * w1 + second[3] * w2;
  const channels = [0, 1, 2].map((index) => (alpha === 0 ? 0 : (first[index] * first[3] * w1 + second[index] * second[3] * w2) / alpha));
  return [...channels, alpha * alphaScale];
}

// 找到从 start 处“(”开始的配对“)”位置。
function closingParen(text, open) {
  let depth = 0;
  for (let index = open; index < text.length; index += 1) {
    if (text[index] === '(') depth += 1;
    else if (text[index] === ')') {
      depth -= 1;
      if (depth === 0) return index;
    }
  }
  return -1;
}

function splitTopLevel(text, separator = ',') {
  const parts = [];
  let depth = 0;
  let start = 0;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '(') depth += 1;
    else if (char === ')') depth -= 1;
    else if (char === separator && depth === 0) {
      parts.push(text.slice(start, index));
      start = index + 1;
    }
  }
  parts.push(text.slice(start));
  return parts.map((part) => part.trim());
}

// 把 var(--x[, 备用]) 换成变量的值（递归展开）；lookup 找不到且没有备用值时报错。
export function substituteVars(text, lookup, depth = 0) {
  if (depth > 24) throw new Error('变量嵌套过深或循环引用');
  let output = '';
  let cursor = 0;
  for (;;) {
    const start = text.indexOf('var(', cursor);
    if (start < 0) break;
    const end = closingParen(text, start + 3);
    if (end < 0) throw new Error('var() 括号不匹配');
    const [name, ...fallbackParts] = splitTopLevel(text.slice(start + 4, end));
    const fallback = fallbackParts.length ? fallbackParts.join(',') : undefined;
    const found = lookup(name.trim());
    let replacement;
    if (found !== undefined) replacement = substituteVars(found, lookup, depth + 1);
    else if (fallback !== undefined) replacement = substituteVars(fallback, lookup, depth + 1);
    else throw new Error(`无法解析变量 ${name.trim()}`);
    output += text.slice(cursor, start) + replacement;
    cursor = end + 1;
  }
  return output + text.slice(cursor);
}

function evaluateMixCall(args) {
  const [space, ...colors] = splitTopLevel(args);
  if (!/^in\s+srgb$/i.test(space.trim()) || colors.length !== 2) throw new Error(`不支持的 color-mix 参数：${args}`);
  const parsed = colors.map((part) => {
    // 百分比可以写在颜色前面或后面。
    const leading = /^(-?\d*\.?\d+)%\s+(.*)$/.exec(part.trim());
    const match = leading ? [part, leading[2], leading[1]] : /^(.*?)(?:\s+(-?\d*\.?\d+)%)?$/.exec(part.trim());
    const color = parseColor(match[1]);
    if (!color) throw new Error(`无法解析颜色：${match[1]}`);
    return { color, percent: match[2] === undefined ? undefined : parseFloat(match[2]) };
  });
  const mixed = mixColors(parsed[0].color, parsed[0].percent, parsed[1].color, parsed[1].percent);
  if (!mixed) throw new Error('混色比例无效');
  return formatColor(mixed);
}

// 依次计算最里层的 color-mix()（最后出现的那个一定不再包含别的 color-mix）。
export function evaluateColorMix(text) {
  let value = text;
  for (let guard = 0; guard < 64; guard += 1) {
    const start = value.lastIndexOf('color-mix(');
    if (start < 0) return value;
    const end = closingParen(value, start + 9);
    if (end < 0) throw new Error('color-mix() 括号不匹配');
    value = value.slice(0, start) + evaluateMixCall(value.slice(start + 10, end)) + value.slice(end + 1);
  }
  throw new Error('color-mix 嵌套过多');
}

// 只替换声明里的 color-mix() 调用，其余部分（包括别的 var()）原样保留。
export function staticValue(value, lookup) {
  let output = '';
  let cursor = 0;
  for (;;) {
    const start = value.indexOf('color-mix(', cursor);
    if (start < 0) break;
    const end = closingParen(value, start + 9);
    if (end < 0) throw new Error('color-mix() 括号不匹配');
    output += value.slice(cursor, start) + evaluateColorMix(substituteVars(value.slice(start, end + 1), lookup));
    cursor = end + 1;
  }
  return output + value.slice(cursor);
}

// 从主题文件读出白天、夜间两套变量（默认侧栏为深色）。
export function loadThemeVars(themeCss) {
  const root = postcss.parse(themeCss);
  const light = new Map();
  const darkOnly = new Map();
  const assign = (target, rule) => rule.each((node) => {
    if (node.type === 'decl' && node.prop.startsWith('--')) target.set(node.prop, node.value);
  });
  root.walkRules((rule) => {
    if (rule.parent.type !== 'root') return;
    const selectors = rule.selectors.map((selector) => selector.trim());
    if (selectors.includes(':root')) assign(light, rule);
    else if (selectors.every((selector) => selector === ':root[data-sidebar="dark"]')) assign(light, rule);
    else if (selectors.every((selector) => selector === ':root[data-theme="dark"]' || selector === ':root[data-theme="dark"][data-sidebar="dark"]')) assign(darkOnly, rule);
  });
  const dark = new Map([...light, ...darkOnly]);
  return { light, dark };
}

function ruleModes(rule) {
  const selectors = rule.selectors.map((selector) => selector.trim());
  const withoutNot = selectors.map((selector) => selector.replace(/:not\([^)]*\)/g, ''));
  if (withoutNot.every((selector) => selector.includes(DARK))) return ['dark'];
  if (selectors.some((selector) => selector.includes(':not([data-theme="dark"])')) || withoutNot.every((selector) => selector.includes('[data-theme="light"]'))) return ['light'];
  return ['light', 'dark'];
}

function darkSelector(selector) {
  const value = selector.trim();
  if (value.startsWith(':root')) return `:root${DARK}${value.slice(5)}`;
  if (/^html\b/.test(value)) return `html${DARK}${value.slice(4)}`;
  return `:root${DARK} ${value}`;
}

function inKeyframes(rule) {
  return rule.parent && rule.parent.type === 'atrule' && /keyframes$/i.test(rule.parent.name);
}

// :has() 改写：A:has(B) → A.oa-has-<编号>。编号由“A|B”算出，同一条件全站同一个类名；
// 运行时脚本读 .oa-has-<编号>{--oa-has:"..."} 登记表，给满足条件的元素加类。
function hashText(text) {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(36);
}

// 取出 :has( 前面紧挨着的复合选择器（遇到顶层空白或组合符为止，括号内的内容整体跳过）。
function compoundBefore(selector, index) {
  let depth = 0;
  let start = index;
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    const char = selector[cursor];
    if (char === ')') depth += 1;
    else if (char === '(') depth -= 1;
    else if (depth === 0 && /[\s>+~,]/.test(char)) break;
    start = cursor;
  }
  return start;
}

export function rewriteHasSelector(selector, register) {
  let output = selector;
  for (let guard = 0; guard < 16; guard += 1) {
    const at = output.indexOf(':has(');
    if (at < 0) return output;
    const end = closingParen(output, at + 4);
    if (end < 0) throw new Error(':has() 括号不匹配');
    const start = compoundBefore(output, at);
    const compound = output.slice(start, at) || '*';
    const relative = output.slice(at + 5, end).trim();
    const name = register(compound, relative);
    output = `${output.slice(0, start)}${output.slice(start, at)}.${name}${output.slice(end + 1)}`;
  }
  throw new Error(':has() 过多');
}

const VIEWPORT_UNIT = /(\d*\.?\d+)(dvh|svh|lvh|dvw|svw|lvw)\b/g;
const HAS_VIEWPORT_UNIT = /\d(dvh|svh|lvh|dvw|svw|lvw)\b/;

export default function legacyWebviewCss(options = {}) {
  const themeVars = options.themeVars ?? loadThemeVars(fs.readFileSync(options.themeFile, 'utf8'));
  // 运行时主题色由偏好设置写在 <html> 上，样式表里的默认值不一定是实际默认主题，按传入值覆盖。
  for (const mode of ['light', 'dark']) {
    for (const [name, value] of Object.entries(options.overrides?.[mode] ?? {})) themeVars[mode].set(name, value);
  }
  return {
    postcssPlugin: 'oa-legacy-webview-css',
    OnceExit(root, { result }) {
      const fileVars = new Map();
      root.walkDecls((decl) => {
        if (decl.prop.startsWith('--') && !fileVars.has(decl.prop) && !inKeyframes(decl.parent)) fileVars.set(decl.prop, decl.value);
      });
      const pending = new Map();
      let unresolved = 0;
      root.walkDecls((decl) => {
        const rule = decl.parent;
        if (!rule || rule.type !== 'rule' || decl.raws.oaLegacy) return;
        if (HAS_VIEWPORT_UNIT.test(decl.value)) {
          const fallback = decl.value.replace(VIEWPORT_UNIT, (_, number, unit) => `${number}${unit.endsWith('w') ? 'vw' : 'vh'}`);
          const previous = decl.prev();
          if (!(previous && previous.type === 'decl' && previous.prop === decl.prop && previous.value === fallback)) {
            decl.cloneBefore({ value: fallback, raws: { ...decl.raws, oaLegacy: true } });
          }
        }
        if (!decl.value.includes('color-mix(')) return;
        const local = new Map();
        rule.each((node) => {
          if (node.type === 'decl' && node.prop.startsWith('--')) local.set(node.prop, node.value);
        });
        const keyframes = inKeyframes(rule);
        const modes = keyframes ? ['light'] : ruleModes(rule);
        const values = {};
        for (const mode of modes) {
          const lookup = (name) => local.get(name) ?? fileVars.get(name) ?? themeVars[mode].get(name);
          try {
            values[mode] = staticValue(decl.value, lookup);
          } catch {
            values[mode] = undefined;
          }
        }
        const primaryMode = modes[0];
        if (values[primaryMode] === undefined) {
          unresolved += 1;
          return;
        }
        const isCustom = decl.prop.startsWith('--');
        if (!isCustom || keyframes) {
          decl.cloneBefore({ value: values[primaryMode], raws: { ...decl.raws, oaLegacy: true } });
        }
        const entry = pending.get(rule) ?? { base: [], dark: [] };
        if (isCustom && !keyframes) entry.base.push({ prop: decl.prop, value: values[primaryMode], important: decl.important });
        if (modes.length === 2 && values.dark !== undefined && values.dark !== values.light) {
          entry.dark.push({ prop: decl.prop, value: values.dark, important: decl.important });
        }
        if (entry.base.length || entry.dark.length) pending.set(rule, entry);
      });
      // :has() 规则在旧内核里整条失效：另写一份类名版本，只在不支持 :has 的浏览器生效。
      const hasRegistry = new Map();
      const register = (compound, relative) => {
        const name = `oa-has-${hashText(`${compound}|${relative}`)}`;
        if (!hasRegistry.has(name)) hasRegistry.set(name, `${compound}|${relative}`);
        return name;
      };
      root.walkRules((rule) => {
        if (!rule.selector.includes(':has(') || inKeyframes(rule) || rule.raws.oaLegacy) return;
        let selectors;
        try {
          selectors = rule.selectors.map((selector) => rewriteHasSelector(selector, register));
        } catch {
          unresolved += 1;
          return;
        }
        const clone = rule.clone({ selectors });
        clone.raws.oaLegacy = true;
        clone.walkDecls((decl) => {
          decl.raws.oaLegacy = true;
        });
        const supports = postcss.atRule({ name: 'supports', params: LEGACY_HAS_SUPPORTS });
        supports.append(clone);
        rule.after(supports);
      });
      if (hasRegistry.size) {
        const supports = postcss.atRule({ name: 'supports', params: LEGACY_HAS_SUPPORTS });
        for (const [name, pair] of hasRegistry) {
          supports.append(postcss.rule({ selector: `.${name}`, nodes: [postcss.decl({ prop: '--oa-has', value: `"${encodeURIComponent(pair)}"` })] }));
        }
        root.append(supports);
      }
      for (const [rule, entry] of pending) {
        const supports = postcss.atRule({ name: 'supports', params: LEGACY_SUPPORTS });
        if (entry.base.length) {
          const baseRule = postcss.rule({ selector: rule.selector });
          entry.base.forEach((item) => baseRule.append(postcss.decl({ ...item, raws: { oaLegacy: true } })));
          supports.append(baseRule);
        }
        if (entry.dark.length) {
          const darkRule = postcss.rule({ selectors: rule.selectors.map(darkSelector) });
          entry.dark.forEach((item) => darkRule.append(postcss.decl({ ...item, raws: { oaLegacy: true } })));
          supports.append(darkRule);
        }
        rule.after(supports);
      }
      if (unresolved && options.report) result.warn(`旧内核回退：${unresolved} 条 color-mix 无法静态计算，保持原样`);
    },
  };
}
legacyWebviewCss.postcss = true;
