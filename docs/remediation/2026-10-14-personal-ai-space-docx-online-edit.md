# 个人AI空间DOCX在线编辑：新增需求定位

## 1. 清单原文

- 原始问题（逐字）：这个文件我需要可以在线编辑
- 补充原文（逐字）：你去找github找到对应的在线编辑了吗 我之前好像是装过的
- 非Excel批次；当前状态：只读定位完成；用户补充“可以”，已授权阿里云补装/启用Collabora并接个人AI空间。基础设施精确脚本与回滚待PM审查，尚未服务器写入。
- 基线：正式dev `f4a2a65c57b9abb8e77eb36971cf3aa88586c9c1` / 1.1.370；独立候选树 `/tmp/oa-release-candidate-20261013-FSJmPo`。

## 2. 唯一截图分析

- 图片：`codex-clipboard-f2ec462f-6241-4f22-b75b-dcd3675f129e.png`。主会话已单图分析并持久化 `/tmp/oa-personal-docx-online-edit-20261014-screenshot.md`；本子任务读取该分析，不冒称亲自浏览器验收。
- 页面：AI助手 → 「管理员的个人AI空间」抽屉。红框指两张DOCX卡，来源分别为助手回答与案件AI迁移，显示格式、大小、保存时间和可下载状态。
- 按钮：「查看来源会话」「下载DOCX」存在；卡片缺在线编辑。背景「保存Word」是生成文件入口，不应被替换成修改旧来源消息。
- 期望：打开有权限的已保存DOCX进行真实Office编辑，成功保存后刷新和下载得到新版本；保留下载和来源会话，桌面/手机同时适配，失败不能假称已保存。

## 3. 旧系统实现

不适用：用户提出新增在线编辑能力，不进行旧站对齐或连接退役腾讯系统。主会话已查询GitHub `CollaboraOnline/online`；当前仓库已有Collabora/CODE WOPI链，优先复用，不另行引入OnlyOffice。

## 4. 新系统当前实现

### 前端

- `personal-agent/PersonalAiSpace.tsx` 查询 `/personal-agent/ai-space` 与 `/files`，使用 `PersonalAiSpaceFiles.tsx` 显示卡片，现仅来源会话与下载。
- `personalAiSpaceApi.ts` 下载先回查file状态，再下载二进制；`usePersonalWorkspace.ts::saveWord` 仍是助手回答→人工确认→新增文件，不是编辑既有Word。
- 已有 `office/LibreOfficeEditorModal.tsx`、`LibreOfficeFrame.tsx`、`useLibreOfficeSession.ts`、`libreOfficeApi.ts`、`types.ts`。Frame用POST传WOPI令牌；通信校验origin/frame，保存/关闭等后端状态确认、超时保留编辑器、beforeunload保护已存在。
- target与API目前强制 `caseId/attachmentId`，不能把个人file_id冒充case_id。当前Modal视口高度及按钮需同步手机991断点、320/375/390/414/768宽度、44px和安全区适配。

### 后端

- `areas/personal_agent/ai_space.py`：列表、单条、download及保存助手消息；没有个人编辑会话入口。
- `ai_space_service.py::space_file_record/space_file_bytes`：通过 `ai_generated_file` 索引查文件，读索引固定path并核size/hash，附件pointer变化不会自动改变下载版本。
- `core/generated_file_records.py`：`personal_ai_space` 与 `ai_generated_file` 私有模块、真实owner_user_id/管理员读取权限、病例关联权限、配置映射和文件元数据。
- `core/generated_file_storage.py::save_generated_file`：新文件采用计划→私有OSS不可变对象→回读校验→available及附件；个人空间明确拒绝 `attachment` 覆盖（422）。不能去掉保护来复用新增接口。
- 已有 `areas/legal/libreoffice.py` 与 `core/libreoffice_{config,security,state,sessions,files,save}.py`：完整DOCX二进制、WOPI proof、锁/CAS、pending计划、不可变版本及失败状态。但 `create_session` 明确排除AI空间类别，context/签名令牌/保存审计硬绑定case_id及案件权限。

### 数据库与历史关系

- 既有 `BusinessRecord(module=ai_generated_file).data` 存file_id、owner_user_id、attachment_id、path、sha256、size、source_kind、conversation_id及可选case_id；`FileAttachment` 已有word_editor锁token/期限/操作者字段。
- 个人新附件通常挂file记录，案件AI附件挂案件记录。截图中的case_migration只是来源标签，不能据标签/文件名判断真实所有者及附件归属；本轮不读用户业务DB，所以具体迁移关系仍未验证。
- 编辑保存需在同一DB事务更新当前个人文件索引path/hash/size与其附件引用，并保留原版本/来源。若迁移索引仍指案件附件，不能在个人入口覆盖案件原文件；须明确独立个人副本及正确归属适配或阻断。
- 计划优先复用JSON及既有锁列，无新表迁移结论尚待B具体设计确认。

### 实际生产依赖只读事实

- 阿里云有效API进程仅白名单字段读取：OFFICE_EDITOR_ENABLED、CODE_SERVER_URL、CODE_BROWSER_URL、OFFICE_WOPI_BASE_URL、OFFICE_FRONTEND_ORIGIN、OFFICE_TRUSTED_ORIGINS、OFFICE_OSS_WRITE_PREFIX、OFFICE_EDITOR_VALIDATION_CASE_CODES均not-set；WOPI签名secret_present=false，未输出秘密。
- 源码默认 `office_editor_enabled=False`，当前不是启用的Office环境。`docker ps`没有运行容器，systemd无CODE/coolwsd，OA服务仍正常。
- 补查 `docker ps -a` 确有旧 `CODEX-collabora-engine-20261011`，Exited(0)，绑定127.0.0.1:19980→9980；镜像ID `sha256:bb8f3c9c5c9016045f25fccb5f0649be94469ebc7c7cc379f3576e470cccf33d`，无RepoTags/RepoDigests/source/version标签。不能据此宣布正式引擎可用或盲目启动未知试验容器。
- 当前没有有效CODE公开origin，未猜地址请求discovery；公开OA首页HTTP200但本次响应无CSP头。引擎discovery/WOPI回调/浏览器iframe/外部origin及证书全链仍未验证。
- 用户曾装过的说法与已退出旧容器相符，但是否可按可核验官方镜像复用仍待依赖评估。当前只读调查，不安装、启用、改配置、生成凭据或重启。

## 5. 需求与当前实现差距

| 编号 | 需求 | 当前差距 | 根因与依据 |
|---|---|---|---|
| D1 | 个人DOCX在线编辑 | 只有下载/来源入口 | PersonalAiSpaceFiles无编辑target，已有Office API仅案件 |
| D2 | 保存后下载新版 | 当前下载读索引固定path/hash | 只更新FileAttachment不足，需generated索引原子同步 |
| D3 | 已有编辑器可复用 | 源码完整，但生产未启用 | 配置not-set、引擎容器退出、discovery与WOPI链未验证 |
| D4 | 来源/权限/格式保留 | 个人/迁移/案件归属不同 | case context与个人权限不能混用，不能纯文本再生成DOCX |

## 6. 精确拟修改清单与分工

- [ ] B后端独占：`areas/personal_agent/ai_space.py` 新增个人file会话创建/状态/关闭；个人Office适配模块由B明确命名。`core/libreoffice_security.py/state.py/sessions.py/save.py/files.py` 及 `areas/legal/libreoffice.py` 如需共用WOPI路由分型，保持案件旧token/API兼容，不扩大原权限；`generated_file_records.py` 仅必要可编辑能力/版本信息。
- [ ] B保存：基于个人目标类型、真实登录账号与owner或真实admin权限即时回查，签名token按scope分型，锁/CAS与expected版本匹配；私有个人folder不可变写入→回读→索引/附件同事务，保留历史和pending失败事实。WOPI不能伪造MCP authenticated_identity上下文。
- B具体适配落点：新增 `core/personal_libreoffice.py`，个人JWT带scope/file_id/owner_user_id而旧case令牌兼容；3个个人session API及editable/reason能力。迁移attachment仅在真实case_id匹配时建立挂generatedrecord的独立个人附件并切该file索引attachment_id，原案件附件不动；缺真实case_id的错挂一律409。版本键来自owner已验证SPACE_MODULE.folder与AI bucket，同事务CAS切索引/附件，旧来源及版本保留，新增文件接口422保护不删除。无schema迁移。
- B独占 `config.py` 新增office_personal_editor_enabled默认false；libreoffice_config.py的configuration/discovery/editor_url增加personal参数，WOPI依据已验证scope选择flag。infra仅启用OFFICE_PERSONAL_EDITOR_ENABLED，OFFICE_EDITOR_ENABLED保持false，不顺便启用案件编辑。
- [ ] C前端独占：`office/types.ts` target联合类型、`libreOfficeApi.ts` scope路由、`useLibreOfficeSession.ts` 依赖和保存刷新、`LibreOfficeEditorModal.tsx` 及必要新CSS手机适配；`PersonalAiSpace.tsx/PersonalAiSpaceFiles.tsx/personalAiSpaceApi.ts/personal-ai-space.css` 编辑入口及服务器确认刷新，保留来源和下载。
- C新增 `office/libreoffice-editor.css`：<=991全视口safe-area/44px/错误区滚动，匹配Ant6 ant-modal-container；编辑器为个人Drawer的sibling，不被列表loading卸载。`CaseCenterPage.tsx` 仅typeimport及officeTarget state缩窄为LibreOfficeCaseEditorTarget，零案件业务逻辑变化。
- C同类类型引用横向审计确认 `legal/services/documentsActions.tsx` 的import/context两处也需收窄LibreOfficeCaseEditorTarget；两文件总5个类型token适配，PM已批准，不改案件业务行为。
- C关闭保护沿用beforeunload和正常Modal关闭，不宣称SPA全局路由卸载阻止或跨路由草稿持久化；PM当前不加全局routerblock。
- [ ] A仅主定位文档、最终候选整合、准确发布门禁与树外交接，不与B/C并改业务文件。
- [ ] 生产引擎依赖：待用户明确决定补装或启用可验证的既有CODE；固定可信镜像及最小网络/HTTPS/WOPI配置方案另审，不盲启旧试验容器。此依赖未获落实前不称功能可用。
- 风险：伪scope越权、旧token兼容、CAS冲突、停用用户、保存超时、OSS回写与DB提交失败、迁移附件交叉归属、Office版式兼容和手机输入遮挡；已有案件链不得回归破坏。

## 7. 验证清单（当前未执行）

| 原文片段 | 真实入口与来源 | 预期结果 | 当前状态 |
|---|---|---|---|
| 这个文件我需要可以在线编辑 | 个人AI空间DOCX卡→个人scope会话 | 真实引擎打开、保存、刷新/下载新版本，原来源保留 | 未验证 |
| 我之前好像是装过的 | 既有CODE源码与生产旧容器 | 确认正式服务身份和可复用依赖，不把源码或退出容器称安装可用 | 只读事实已核，启用待决定 |

- [ ] 个人/真实admin/跨账号/停用/非DOCX/未available/缺实体/迁移归属拒绝；案件旧链及token不变。
- [ ] 格式保持用完整DOCX二进制读写与Office引擎，不靠纯文本重建。
- [ ] 保存成功状态、下载回读、冲突/失效锁/pending写入和失败保留编辑器。
- [ ] 实际生产CODE discovery proof、WOPI可达、浏览器origin与iframe/CSP、证书和保存权限验证。
- [ ] PC/手机样式及实际最终构建；按独立问题skill必要源码门禁及构建，不先做浏览器或真实业务写测试。
- 定时业务、业务汇总计数：不涉及。生产迁移/用户文件写入：本轮无授权、未执行。
- 测试数据/进程清理：本轮未创建数据、标签或服务，无清理项；将来仅操作任务专属CODEX文件。
- 页面及真机由用户验收，不能从源码/构建/HTTP200推导已验收。

## 8. 实施记录与当前状态

- A仅维护本定位Markdown及树外基础设施脚本；B/C在PM授权后分别实现各自文件，当前未暂存/提交/推送/部署。
- CodeGraph status/explore不可用，使用真实源码调用追踪；未伪图谱证据。
- 当前生产依赖缺口与旧容器已核；用户“可以”后进入已授权方案准备，B/C业务实现以PM分工为准，A先只读基础设施调查及精确脚本/回滚审查，不先执行服务器写入。
- 历史环境参考中的Windows路径/腾讯地址不作为当前操作目标；本任务以当前Mac正式clone与阿里云事实为准。
- B阶段：9个后端文件及纯安全回归personal_office_security_test.py；5项配置/tokenscope/旧caseJWT/个人revisionfolder检查通过，无DB/OSS写；历史None/non-dict元数据明确409，不让列表500。requirements不变，无schema迁移。定向检查不冒充真实保存/页面验收。
- C阶段：11前端文件，TypeScript与既有28测试通过；新OfficeCSS解析无warning。最终compiled样式和真实引擎保存/手机页面尚未验证。
- A基础设施方案：`deploy/setup-personal-collabora.py`（树外副本 `/tmp/oa-collabora-infra-20261014.py`），最终已审sha256 `5a94fab2f20f4103dd4975c1eb9e3837409d04a0b0bad0c616a254f7c0fb9ba5`，ruff与py_compile通过，尚未执行。原4d格式化前后AST sha均 `1712eb1927a50eaec5552479767508e124bd04c9d524aa175831901bc7d7b961`，该机械步骤逻辑等价；其后新增16行idlequeue安全门禁经PM独立审准，不冒充无逻辑变化。固定官方collabora/code amd64 digest `56541aad09403975646dfb87a3716e38afecce09b5f853391eb6d937a0ccd402`；仅loopback9980、2CPU/2GB、新自有unit和同域局部反代。禁止宏/admin/外部AI、不用privileged/SYSADMIN；相关CODE/WOPI URL不记accesslog，显式保全代理Host/Proto/For及21MB回调上限。只personal flag启用，case保持false。备份配置仅生产私有目录0600，独立CODE proof私钥与app WOPIsecret仅生产随机生成，不输出或上传仓库。三既存formal锁/准确currentSHA/配置hash及无assigned/activating队列保证互斥与拒第三方覆盖，malformed队列同样拒绝；pull失败保留备份可严格resume，其他中间失败自动guarded rollback。PM已批准精确脚本，等待实际外部372收口后再执行。
- WOPI host策略按官方HostUtil/PocoXML精确键显式groups及唯一https://huzhilawfirm.com:443/allow，不依赖legacy aliasgroup1或firsthost。loopback及公开discovery公钥n/e均须匹配本次私有RSA对应public numbers，不能只判断存在。
- 最终运输扩展已独立审准：helper最终SHA `34a5ffb514a3dbfbb4ec95e2c05825136be75f0a3781bce554496b2cb6ae7c9f` 取代5a，cool location显式HTTP1.1（原server已1.1但不只依赖继承）。服务器官方registry直连timeout，Mac Colima官方pin/linux-amd64 pull成功；专属Docker archive490721280字节/SHA `2fb39049d6395fb841f636617314bc6831bedf5e2e650abb584320e34879808b`，manifest5654→config16c→5个compressed层及uncompressed diffIDs全核，无RepoTags/多余或非法成员。加载后完整Config/RootFS/Arch/Entrypoint/Cmd核对，Docker29 manifest-ID及legacy config-ID只在完整官方证明后兼容，不允许任意本地镜像替换。旧容器/旧包保留，无商业采购或Docker凭据传输。
- 镜像独立身份核验：固定官方Registry manifest的config digest `16cff53bb18c856f288a255c8f84cbec32fb5a0afdf52dd46b404ae868ccf2f7`，entrypoint为/usr/bin/coolwsd --use-env-vars固定参数，Cmd=null，User=1001，版本26.04.5.1；脚本强核这些字段后追加CLI参数，不假设旧image启动行为。
- 资源只读核验：4CPU、约15.6GB RAM/12.8GB available、66GB磁盘可用，Docker29.9；Nginx已配置huzhilawfirm.com真实TLS。官方资料为[Collabora镜像README](https://raw.githubusercontent.com/CollaboraOnline/online.mirror/master/docker/README)及[默认配置](https://raw.githubusercontent.com/CollaboraOnline/online.mirror/master/coolwsd.xml.in)，SDK网页bot challenge不绕过。选用免费CODE开发版，不采购商业企业许可；企业支持能力不等同。
