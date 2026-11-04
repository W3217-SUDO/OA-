// 501325（fwl 11-04）：选好公证处后按“公证处设置”里的公证号模板填好公证书号，年份按取证日期，编号留 xxxxx 给调查员补。
const PLACEHOLDER = /[x×Ｘ]{2,}|\{serial\}|yyyy|\{year\}/i;

/** 按模板生成公证书号；模板为空返回空串。 */
export function fillNotaryNumber(template: string | undefined, year: number): string {
  let text = String(template || "").trim();
  if (!text) return "";
  text = text.replace(/\{year\}|yyyy/gi, String(year));
  text = text.replace(/^([（(]\s*)\d{4}(\s*[)）])/, `$1${year}$2`);
  text = text.replace(/\{serial\}/gi, "xxxxx").replace(/[x×Ｘ]{2,}/gi, "xxxxx");
  // 旧系统个别模板写的是样例编号（如“第3360号”），编号部分也换成 xxxxx。
  if (!/xxxxx/.test(text)) text = text.replace(/(第|笫)\s*\d+\s*号/, "$1xxxxx号");
  return text;
}

/** 公证书号里还留着没补的编号或年份。 */
export function hasNotaryPlaceholder(value: unknown): boolean {
  return PLACEHOLDER.test(String(value || ""));
}
