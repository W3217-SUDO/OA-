import type { FeeTypeOption } from "./FeeTypePicker";

export function buildFeeTypeTree(items: FeeTypeOption[], editing = false, scope?: string) {
  const byCode = new Map(items.map(item => [item.code, item]));
  const build = (parent: string, seen = new Set<string>()): any[] => items
    .filter(item => (byCode.has(item.parent_code) ? item.parent_code : "") === parent && !seen.has(item.code))
    .map(item => {
      const children = build(item.code, new Set([...seen, item.code]));
      return {
        key: item.code, value: editing ? item.id : item.code, title: item.name,
        selectable: editing && item.selectable && (!scope || item.expense_scopes.includes(scope)),
        disabled: !children.length && (editing ? !item.selectable || Boolean(scope && !item.expense_scopes.includes(scope)) : item.code.startsWith("-") || item.name.startsWith("请选择")),
        children: children.length ? children : undefined,
      };
    });
  return build("");
}
