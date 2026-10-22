"""随 MCP 一起下发给用户智能体的“使用技能”：连接后先读它，学会怎么用这个 MCP。

三条路径同时提供，因为不同客户端处理方式不同：握手说明（INSTRUCTIONS）、工具 oa_get_usage_guide、资源 oa-mcp-skill://usage、提示 oa-usage。
"""

SKILL_NAME = "oa-mcp-usage"
SKILL_URI = "oa-mcp-skill://usage"
PROMPT_NAME = "oa-usage"
GUIDE_TOOL = "oa_get_usage_guide"

# 握手时随 initialize 返回，支持 instructions 的客户端会放进系统提示；保持简短，细节在技能里。
INSTRUCTIONS = (
    "这是沪知办公系统（OA）的 MCP。开始操作前，先调用工具 oa_get_usage_guide（或读取资源 oa-mcp-skill://usage、使用提示 oa-usage）阅读使用指南。"
    "要点：权限等同用户本人账号；调用接口前先用 oa_describe_tool 取参数定义；新增、修改、删除会直接执行，必须先把将要执行的内容展示给用户并取得确认；"
    "缺少必填参数时先问用户，不要猜测编号、金额、日期、人名；系统管理类接口不开放。"
)

_BODY = """\
## 一、你在做什么

你通过用户本人的 OA 账号操作沪知办公系统。**权限和用户在 OA 里的权限完全一致**：用户看不到、办不了的，你也看不到、办不了。系统参数、菜单、角色权限、用户授权、回收站、技能插件管理等系统管理类接口不开放；OA 里的删除都是**逻辑删除**（管理员可在回收站恢复）。

## 二、先做什么（每次连接后）

1. 读完本指南。
2. 看上面的“当前连接”：它写明了这次连接的**业务范围**和**读写权限**。范围外的接口调用会被拒绝（403），不要反复尝试；告诉用户需要把对应业务加进连接地址的 `biz=` 里。
3. 用户的需求属于哪个业务？只围绕这个业务找接口。

## 三、怎么找接口、怎么调用

**连接地址选了业务**（地址里有 `biz=`）：工具列表里已经列出所选业务的接口，名字前带标记——**【查询】**、**【写入】**、**【删除】**。列表里只有标题和“方法 路径”，没有参数定义。

1. 选定接口后，先调用 `oa_describe_tool`（参数 `name` 为接口名），拿到完整参数定义（`path`、`query`、`body`、`files` 和必填项）。
2. 然后直接调用该接口工具，参数按定义填写。

**连接地址没选业务**：工具列表里只有入口工具，按这个顺序用：

1. `oa_list_tool_groups`：看有哪些业务分组及可用接口数；
2. `oa_list_group_tools`（参数 `group_id`）：看分组里的接口清单；或用 `oa_search_tools`（参数 `query`）按关键词找接口，它会直接返回完整参数定义；
3. `oa_describe_tool`：取某个接口的完整参数定义；
4. 调用：查询类用 `oa_call_read_tool`，新增、修改、删除类用 `oa_call_write_tool`（参数 `name` 和 `arguments`）。两个入口不能混用。

## 四、调用规则（必须遵守）

- **先 describe，再调用。** 不要凭印象编参数。
- **缺少必填参数，先问用户。** 不要猜编号、金额、日期、人名、案号、客户名称。
- **编号类参数先查询取真实值。** 例如案件 ID、客户 ID、合同 ID，先用查询接口取到，不要把不同业务的 ID 混用。
- **新增前先查是否已存在**（客户、案件、合同等），避免重复。
- **列表接口注意分页。** 常见参数是 `page` 和 `page_size`，不要一次拉全量；只取用户要的信息。
- **按用户的要求做，不多做。** 不要顺手修改用户没提到的数据。

## 五、写入前的确认（最重要）

【写入】和【删除】类接口**会直接执行，服务端不再二次确认**，确认由你向用户负责：

1. 调用前，用自然语言把**将要执行的内容**列给用户：对象（哪个案件/客户/合同）、哪些字段、新值是什么；删除类要明确说删哪一条。
2. **等用户明确说“确认/可以/执行”**，再调用。用户没明确同意，不要调用。
3. 批量操作：先汇总让用户确认一次范围，不要对每条悄悄重复调用。
4. 不要用写入接口“试探”接口是否可用。
5. **不确定写入是否成功时（超时、报错），先用查询接口核对结果，不要直接重试写入**，避免重复提交。如实告诉用户结果，不要声称成功。

## 六、遇到错误怎么办

| 提示 | 含义 | 你该做的 |
|---|---|---|
| 401 | 令牌无效、已过期或已撤销 | 告诉用户到 OA“电脑连接 OA”重新生成令牌 |
| 403 “不在这个连接地址选定的业务范围内” | 接口不属于选定业务 | 告诉用户把业务加进 `biz=` |
| 403 “没有 MCP 写入授权” | 账号只有查询权限 | 告诉用户联系管理员开通 |
| 403 “当前账号没有该菜单的操作权限” | OA 本身不允许该账号做这件事 | 如实告诉用户，不要绕过 |
| 403 “属于系统管理类” | 系统管理接口不开放 | 告诉用户需在 OA 页面由管理员操作 |
| 422 | 参数不符合定义 | 重新 `oa_describe_tool`，对照必填项修正；缺信息就问用户 |
| 429 | 调用太频繁 | 等一分钟再试，并减少调用次数 |

## 七、隐私与保密

- OA 数据涉及客户和案件保密信息：只汇总用户要的内容，不要把数据发到其他外部服务或写进无关文件。
- 不要在对话里显示、复述或保存令牌。
- 用户让你处理涉密案件时，提醒用户这些数据会进入当前使用的模型。
"""


def _scope_line(context, catalog) -> str:
    from app.agent_mcp.tool_groups import BUSINESS_BUNDLES, GROUPS
    from app.agent_mcp.service import token_visible_tools

    if getattr(context, "readonly", False):
        tools = token_visible_tools(context, catalog)
    else:
        tools = list(catalog.tools)
    write = "可新增、修改、删除（写入前必须先让用户确认）" if getattr(context, "write_allowed", False) or not getattr(context, "readonly", False) else "只读（不能新增、修改、删除）"
    groups = getattr(context, "groups", None)
    if groups:
        names = [label for _, (label, ids) in BUSINESS_BUNDLES.items() if set(ids) <= set(groups)]
        covered = {g for key, (_, ids) in BUSINESS_BUNDLES.items() if set(ids) <= set(groups) for g in ids}
        names += [GROUPS[g][0] for g in sorted(set(groups) - covered)]
        scope = "、".join(names) or "所选分组"
    else:
        scope = "未选业务（只有入口工具，需要按分组查找接口）"
    return f"- 业务范围：{scope}\n- 读写权限：{write}\n- 当前可用接口：{len(tools)} 个"


def build_skill(context, catalog) -> str:
    """完整技能文本（Markdown，带 frontmatter），开头按当前连接动态写明业务范围和读写权限。"""
    return (
        f"---\nname: {SKILL_NAME}\n"
        "description: 沪知办公系统（OA）MCP 的使用方法：如何查找接口、查询与写入分开、写入前向用户确认、权限与错误处理。连接 OA 后先读它。\n---\n\n"
        "# 沪知办公系统（OA）MCP 使用指南\n\n"
        f"## 当前连接\n\n{_scope_line(context, catalog)}\n\n" + _BODY
    )
