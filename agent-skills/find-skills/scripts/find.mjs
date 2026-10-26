// OA 版 find-skills：在 OA 的受控技能容器里运行（Node 22，只能访问公网 HTTP/HTTPS，没有 npx）。
// search：直接调用 skills.sh 的公开搜索接口，按安装量列出技能；
// link：到 GitHub 找到技能目录，给出固定到当前提交、可在 OA「新增或导入 → GitHub 链接」里安装的链接，并判断装上后在 OA 里能不能用。
const SEARCH_API = "https://skills.sh/api/search";
const GITHUB_API = "https://api.github.com";
const TIMEOUT_MS = 15000;
const SCRIPT_SUFFIXES = [".py", ".js", ".mjs", ".cjs", ".sh"];
// 与 OA 判断“需要外部命令”的规则一致：出现 bash 代码块或 npx/uvx/pip/npm 命令。
const EXTERNAL_COMMANDS = /```(?:bash|sh|shell)|\b(?:npx|uvx|pip3?|npm)\s/i;

const USAGE = `用法：
  find.mjs search <关键词...> [--owner <GitHub 用户或组织>] [--limit <1-50>]
  find.mjs link <owner/repo> <skillId>`;

function fail(message, code = 1) {
  console.log(JSON.stringify({ ok: false, error: message }, null, 2));
  process.exit(code);
}

// 第三方返回的文本只保留可读字符并限制长度，避免把控制字符或超长内容带进对话。
function clean(value, max = 200) {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").trim().slice(0, max);
}

async function getJson(url, accept = "application/json") {
  let response;
  try {
    response = await fetch(url, {
      headers: { Accept: accept, "User-Agent": "huzhi-oa-find-skills" },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (error) {
    throw new Error(`无法连接 ${new URL(url).host}：${error?.name === "TimeoutError" ? "请求超时" : error?.message || error}`);
  }
  if (response.status === 403 && response.headers.get("x-ratelimit-remaining") === "0") {
    throw new Error("GitHub 查询额度暂时用完（每小时 60 次），请稍后再试");
  }
  if (!response.ok) throw new Error(`${new URL(url).host} 返回 HTTP ${response.status}`);
  return accept.includes("raw") ? response.text() : response.json();
}

function option(args, name) {
  const index = args.indexOf(name);
  if (index < 0) return undefined;
  const value = args[index + 1];
  if (!value || value.startsWith("--")) fail(`${name} 需要一个值\n${USAGE}`, 2);
  args.splice(index, 2);
  return value;
}

async function search(args) {
  const owner = option(args, "--owner");
  const limit = Number(option(args, "--limit") ?? 10);
  if (!Number.isInteger(limit) || limit < 1 || limit > 50) fail("--limit 只能是 1 到 50", 2);
  if (owner && !/^[A-Za-z0-9-]{1,39}$/.test(owner)) fail("--owner 不是有效的 GitHub 用户或组织名", 2);
  const query = args.join(" ").trim();
  if (!query) fail(`请提供搜索关键词\n${USAGE}`, 2);
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (owner) params.set("owner", owner.toLowerCase());
  const data = await getJson(`${SEARCH_API}?${params}`);
  const skills = (Array.isArray(data?.skills) ? data.skills : []).map((item) => {
    const id = clean(item.id);
    return {
      name: clean(item.name),
      source: clean(item.source),
      skillId: clean(item.skillId || id.split("/").pop()),
      installs: Number(item.installs) || 0,
      page: id ? `https://skills.sh/${id}` : "",
    };
  }).sort((a, b) => b.installs - a.installs);
  console.log(JSON.stringify({
    ok: true, query, owner: owner || undefined, count: skills.length, skills,
    next: skills.length ? "要安装某个技能时，用 link <source> <skillId> 取得 OA 可导入的 GitHub 链接" : "没有找到匹配的技能",
  }, null, 2));
}

async function link(args) {
  const [source, skillId] = args;
  if (!source || !skillId || args.length !== 2) fail(`link 需要两个参数\n${USAGE}`, 2);
  if (!/^[A-Za-z0-9-]{1,39}\/[A-Za-z0-9_.-]{1,100}$/.test(source)) fail("来源应为 owner/repo 格式", 2);
  if (!/^[A-Za-z0-9_.@-]{1,100}$/.test(skillId)) fail("skillId 格式不正确", 2);
  const repo = await getJson(`${GITHUB_API}/repos/${source}`);
  const branch = clean(repo.default_branch, 100);
  const commit = await getJson(`${GITHUB_API}/repos/${source}/commits/${encodeURIComponent(branch)}`);
  const sha = clean(commit.sha, 40);
  if (!/^[a-f0-9]{40}$/.test(sha)) fail("GitHub 返回的提交无效");
  const tree = await getJson(`${GITHUB_API}/repos/${source}/git/trees/${sha}?recursive=1`);
  const paths = (Array.isArray(tree?.tree) ? tree.tree : []).filter((item) => item.type === "blob").map((item) => item.path);
  const skillFiles = paths.filter((path) => path === "SKILL.md" || path.endsWith("/SKILL.md"));
  const wanted = skillId.toLowerCase();
  const matches = skillFiles.filter((path) => (path.split("/").slice(-2, -1)[0] || "").toLowerCase() === wanted)
    .sort((a, b) => a.length - b.length);
  const skillPath = matches[0] || (skillFiles.length === 1 ? skillFiles[0] : "");
  if (!skillPath) {
    fail(`在 ${source} 里没有找到 ${skillId} 的 SKILL.md${tree?.truncated ? "（仓库太大，GitHub 目录被截断）" : ""}`);
  }
  const directory = skillPath.split("/").slice(0, -1).join("/");
  const inDirectory = paths.filter((path) => !directory || path.startsWith(directory + "/"));
  const scripts = inDirectory.filter((path) => SCRIPT_SUFFIXES.some((suffix) => path.toLowerCase().endsWith(suffix)));
  const text = await getJson(`${GITHUB_API}/repos/${source}/contents/${skillPath.split("/").map(encodeURIComponent).join("/")}?ref=${sha}`,
    "application/vnd.github.raw+json");
  const external = EXTERNAL_COMMANDS.test(text);
  const oaCompatibility = scripts.length
    ? `带 ${scripts.length} 个脚本，可在 OA 受控容器里运行（只能访问公网 HTTP/HTTPS，没有 OA 凭据）`
    : external
      ? "需要 npx/pip 等命令行工具，技能包里没有脚本；装到 OA 后会显示“依赖未就绪”，不建议安装"
      : "纯指令技能，装上即可用";
  console.log(JSON.stringify({
    ok: true,
    name: skillId,
    source,
    stars: Number(repo.stargazers_count) || 0,
    archived: Boolean(repo.archived),
    commit: sha,
    import_url: `https://github.com/${source}/tree/${sha}${directory ? "/" + directory : ""}`,
    skill_md_url: `https://github.com/${source}/blob/${sha}/${skillPath}`,
    files: inDirectory.length,
    scripts: scripts.length,
    oa_compatibility: oaCompatibility,
  }, null, 2));
}

const [command, ...rest] = process.argv.slice(2);
try {
  if (command === "search") await search(rest);
  else if (command === "link") await link(rest);
  else fail(USAGE, 2);
} catch (error) {
  fail(error?.message || String(error));
}
