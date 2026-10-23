# OA 系统字段与检索参数速查

## 一、案件检索工具

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `oa_case_statistics_post` | 全量统计（忽略分页），先看总数 | `body` |
| `oa_search_ordinary_cases_post` | 分页明细 | `body` + `page` / `page_size` |
| `oa_search_counsel_cases_post` | 法律顾问案件（默认列表已排除此类） | `body` |
| `oa_list_active_people_options_get` | 人员目录（102 人），确认 username | `query` |

**性能提示**：`page_size=100` 时MCP 响应超时返回空；用 `page_size=20`（单页约 700KB）。

## 二、人员字段双轨制（最易错）

| 用途 | 正确传值 | 例子 |
|---|---|---|
| 检索参数 `handling_lawyer` / `assistant` | **中文名** | `"范雨星"` |
| 数据字段 `data.case_lawyer` / `data.assistant` | **username** | `"fanyuxing"` |

共办时逗号分隔：`"shenjf,zhanghj"`。

人员目录返回结构：`{"items": [{"value":中文名, "label":中文名, "username": "xxx", "search_text": "..."}]}`

## 三、案件检索 body 常用字段

```
scope               业务范围，默认 "company"
keyword              模糊匹配（可命中 court_case_no / 当事人 / 案号数字）
serial_noOA 内部案号（GDMS/HZMS开头）
customer             客户全称
plaintiff            原告（包含匹配）
defendant            被告（包含匹配）
court                法院代字（如"皖0402"，非全称）
case_type            案件类型
case_status / case_statuses   阶段
cause_name           案由
hearing_lawyer       开庭律师
investigator         调查员
source_from / source_to       案源日期区间（非立案日期！）
filing/ counsel / assisted_* / finance_* / file_*  多组时间与人员口径
page / page_size     分页
```

## 四、案件数据字段速查

```python
data.case_lawyer        # 承办律师 username（可逗号分隔多人）
data.assistant          # 助理
data.court_case_no      # 官方案号（47.6% 有值）
data.court              # 法院代字（71.5% 有值）
data.cause_name         # 案由
data.plaintiff / data.plaintiffs    # 原告（单数 / 列表）
data.defendant / data.defendants    # 被告
data.filing_date / data.filing_time        # 立案日期
data.closing_time       # 结案时间
data.archived_at        # 归档时间
data.archived_at        # 归档时间
data.deadline           # 期限
data.notarial_no / data.notary_no         # 公证号
data.create_time        # 建档时间（**完整度最高，年份统计主用**）
data.change_time        # 最后变更时间
data.is_actived         # 是否有效（F/T）
data.legacy_record      # 旧系统全量冗余字段（体积大，含 CaseLawyerName 等中文名）
```

**顶层字段**：`serial_no`、`title`、`customer`、`status`、`department`、`owner`、`id`、`module`

**年份口径选择**（统计案件年份时）：
- `filing_date`/`filing_time`（立案）：仅 64.5% 有值，**不适合作主口径**
- `create_time`（建档）：**100% 有值**，最可靠
- 案号第 5-6 位（HZMS**25**00143）：仅 38% 可识别，且与立案年份有 55 件不一致
- → **推荐：立案时间优先，无则回退建档时间**

## 五、费用模块（官方费用相关）

### 5.1 费用类型码全表（实测 200 条样本）

`fee_type_path` 是费用类目的全路径，**首层即大类**：

**官方费用类**（缴纳通知书记这类）：

| 类型码 | fee_type_id | 名称 | 全路径 |
|---|---|---|---|
| 1101010 | 19 | 一审诉讼费 | 官方费用 / 一审诉讼费 |
| 1101020 | 20 | 二审诉讼费 | 官方费用 / 二审诉讼费 |
| 1101040 | 22 | 公证费 | 官方费用 / 公证费 |
| 1101090 | 27 | 官费 | 官方费用 / 官费 |

**审级 → 类型对应（用户 2026-10-22 确立的规则）**：
一审案件 → 一审诉讼费（1101010）；二审案件 → 二审诉讼费（1101020）。**按案件审级定，不按文书里的费用项目名猜**——通知书上"案件受理费"是一审二审共有的笼统说法。

**审级判定依据优先级**：

1. **法院案号类型代码**（最可靠）：
   - 一审：`民初`、`知民初`、`刑初`、`行初`
   - 二审：`民终`、`知民终`、`刑终`
   - 再审：`民申`、`知民申`
2. **案件阶段**（`status` / `data.case_phase`）：含「二审」→ 二审；含「一审」→ 一审
3. 都判断不出 → 问律师

**⚠️ 实测警示（403 件样本）**：阶段与案号可能不一致。「二审庭后待判」9 件中 **8 件法院案号实为一审**（如 `（2026）苏0581民初7641号`），说明历史数据存在阶段误填。**案号已登记时优先以案号类型代码判审级**；案号为空才退用阶段。

**全部案件阶段清单**（用于阶段判审级）：

一审类：提交立案、新案待分配、文书准备、等待立案、客户盖章、一审立案受理、一审准备开庭、一审再次开庭、一审庭后待判、一审和解中、一审和解结案、一审判决结案、一审等待上诉、一审待执行、一审待客户回款

二审类：二审立案受理、二审庭后待判、二审和解结案

执行类：执行立案、执行受理、执行中止、执行终本

内部流程：亏损审核、亏损内审、亏损归档、亏损拒绝、归档审核、待分配、已归档

**非官方费用类**（别与官方费用混填）：

| 类型码 | fee_type_id | 名称 | 全路径 |
|---|---|---|---|
| 1102010 | 30 | 律师代理费 | 代理费 / 律师代理费 |
| 1103020 | 38 | 公告费 | 其他费用 / 公告费 |
| 1103010 | 37 | 检索费 | 其他费用 / 检索费 |
| AGENCY-REFUND | 35 | 律师代理费(退费) | 代理费 / 律师代理费(退费) |

**内部类目**（`expense_scope = 内部`，无 type_code）：调档费、品牌管理费、文书提成、调查提成、开庭提成、案源提成、调查固定提成、文书退费提成、任务逾期扣款，以及各类"服务费(案源/品管/文书/调查/开庭)"。

`expense_scope` 取值：**律所** / **内部**。

### 5.1.1 最后缴费期限与提醒任务（用户 2026-10-22 确立）

- **系统在提交缴费时会要求填写「最后缴费期限」**，必须按文书原文的预交天数算出**具体日期**（不是"N 日内"这种相对表述）。
  - 例：文书写"收到本通知书次日起七日内向本院预交"，出具日 2026-10-22 → 最后缴费期限 = **2026-10-29**。
  - 注意口径是"**收到次日起**"算，即出具日次日开始计日。
- **每次收到缴纳通知书都要询问律师：是否设定缴费期限提醒任务。** 不得自行决定，也不得默认不设。
- 缴费期限字段：`data.deadline`。

### 5.2 费用记录关键字段

```python
data.fee_type_id / fee_type_code / fee_type_name
data.fee_type_path                # 类目全路径，如"官方费用 / 一审诉讼费"
data.expense_scope                # 律所 / 内部
data.expense_subtype
data.amount / data.base_amount
data.case_no / data.case_id/ data.case_title
data.case_type                    # 民事案件等
data.case_stage                   # 案件当前阶段
data.contract_id / data.contract_no
data.deadline                     # ⭐ 缴费期限（缴纳通知书必填）
data.payee                # 收款人
data.court / data.court_name        # 受理机关
data.court_case_no                  # 法院案号
data.certificate_no                 # 公证号
data.document_no
data.handler / data.handler_display_name    # 经办人（存 username）
data.investigator
data.plaintiff / data.opponent
data.assistant / data.hearing_lawyer
data.invoice_status / data.invoice_amount / data.invoice_no
data.paid_date / data.paid_amount / data.paid_organization
data.cashed_date / data.cashed_amount
data.is_refund / data.refunded_amount
data.fee_inform_ids                # 关联缴费通知
data.receipt_files
data.commission_mode / data.commission_details    # 提成模式（内部类目用）
data.serial_no                    # 费用单号，形如 FY20261021102129273871
```

### 5.3 缴纳流程状态机

`payment_status` 取值（实测分布）：

| 状态 | 含义 |
|---|---|
| 创建待提交 | 刚建单，尚未提交 |
| 待审批 | 已提交，等待审批 |
| 待付款 | 审批通过，待实际付款 |
| 待核销 | 已付款，待核销 |
| 待到账 | 付款后等待到账确认 |
| 已付款 | 终态：已完成 |
| 已撤回 | 已撤回 |

### 5.4 付款类型（缴费账户）

`oa_list_finance_fee_payment_types_get`，**必填 `path.fee_id`**（某条费用记录的 id，注意不是 case_id）。

返回 `items[]`：

| 字段 | 说明 |
|---|---|
| `id` / `code` | 标识 |
| `name` | 账户名，如"XX市财政局非税收入汇缴结算户" |
| **`nature`** | **`官费` / `其他费用`** —— 按此区分官方费用走哪个账户 |
| `payee` | 收款人 |
| `account_bank` | 开户行 |
| `account` | 账号 |

**用途**：缴纳通知书上的收款账户应与此处的 `name`/`account_bank`/`account` 核对。文书上的账户若在列表中找不到对应项，需询问律师。

### 5.5 费用查询工具

`oa_query_finance_fees_get`（`GET /api/v1/finance/fees/query`）常用 query 参数：

```
scope                  范围
unpaid_official        ⭐ 只看未缴官方费用（bool）
external_only          只看外部费用
case_no                律所案号
court_case_no          法院案号
customer / hearing_lawyer / assistant
fee_types              费用类型过滤
payment_status         付款状态
paid_from / paid_to    付款日期区间
page / page_size
```

**注意**：`case_id` 不是该接口的合法参数（会报 `extra_forbidden`），查某案件费用用 `case_no`。

## 六、写入接口现状（2026-10-23 起）

收文相关写入均已开放，普通写入参数齐全即直接执行，服务器留痕、管理员可还原：

| 顺序 | 操作 | 工具（用 `oa_search_tools` 搜中文名） |
|---|---|---|
| 0 | 下载法院送达文书并存为附件 | “下载法院送达文书”`POST /documents/court-service/fetch` |
| 1 | 官方收文入库（进收文列表，挂到案件） | “上传官方收文”`POST /documents/official/upload`，`files.file`=上一步附件 ID，`body.case_id`=匹配到的案件 ID，`body.court_case_no`=文书案号，`body.document_date`=落款日期 |
| 2 | 更新案件字段（开庭时间、法庭、判决日期等） | 案件更新接口（先搜索确认参数模式） |
| 3 | 官方费用建单并申请缴纳 | 费用登记模块 `/finance/...` |

案件未登记法院案号时，第 1 步会把文书案号回填到 `data.court_case_no`；已登记的不覆盖。
接口报错时如实说明，产出待填字段清单（字段名 + 值 + 来源文书），不谎称已完成。写入后须回查确认。

**权限缺口**：`oa_list_ipr_official_files_get` 可能返回 403「当前角色没有查看该业务模块的菜单权限」，需向管理员申请开通。

## 七、工具检索技巧

工具总量 840 个（tools/list 单次返 354），**不要全量载入**。用检索入口：

| 工具 | 用途 |
|---|---|
| `oa_search_tools` | 按业务目标搜索，返回真实参数模式、必填参数 |
| `oa_list_tool_groups` | 24 个一级业务域 + 第 25 组 4 子组概览 |

**参数报错处理**：
- `422缺少必填参数，请先向用户询问这一项，不要猜测或用默认值补填` → 必须问用户，不能猜
- `不允许未声明的参数` → 该工具不支持此参数，先查 schema