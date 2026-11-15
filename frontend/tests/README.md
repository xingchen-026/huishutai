# 前端工作流模块测试（frontend/tests）

本目录是 **Workflow 模块前端**的验证与回归测试。项目当前没有 vitest / jsdom / @vue/test-utils，
因此测试**不新增任何依赖**，只使用：

- Node.js 24 内置测试运行器 `node:test`（测试文件命名 `*.test.mjs`）；
- 项目已有的 `vite` + `@vitejs/plugin-vue`（程序化创建 Vite SSR 加载器，真实编译并加载 `src` 源码）；
- `tests/mocks/` 下的 ESM 替身模块（替换 axios 实例、vue-router、@vue-flow/*、@vueuse/core、pinia stores、workflow API、AppIcon 等）。

## 运行

```powershell
cd frontend
node --test tests/
```

预期结果（Node v24.20，不含依赖安装/构建）：

```text
ℹ tests 97
ℹ pass 97
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms ≈ 1200
```

其中 7 个 todo 是已知缺陷的修复目标（详见下文 D1–D6），不计失败。分文件统计：

| 文件                            | 用例 | pass | todo |
| ------------------------------- | ---- | ---- | ---- |
| workflow-api.test.mjs           | 26   | 26   | 0    |
| workflow-node.test.mjs          | 7    | 7    | 0    |
| workflow-list.test.mjs          | 16   | 16   | 0    |
| workflow-editor.test.mjs        | 34   | 32   | 2    |
| workflow-integration.test.mjs   | 14   | 13   | 1    |
| workflow-known-defects.test.mjs | 9    | 5    | 4    |
| 合计                            | 106  | 99   | 7    |

> 兼容说明：Node 24 的 `node --test <目录>` 会把目录解析为入口文件（不是在目录内递归发现测试文件），
> 因此 `tests/index.js` 聚合导入全部测试文件，保证验收命令 `node --test tests/` 可运行。
> 等价的、按文件隔离进程的写法是 `node --test "tests/*.test.mjs"`（两者结果一致）。

说明：

- 每个测试文件内部复用同一个 Vite 开发服务器（`middlewareMode`，关闭 HMR/ws/watch）；
- 不加载项目 `vite.config.ts`（其中的 `vite-plugin-vue-devtools` 在纯 Node 环境不可用），
  在 `tests/helpers/harness.mjs` 中以 `configFile: false` 重建最小配置；
- 不联网、不连接后端服务、不写数据库；`node --test` 退出码 0 即通过（`todo` 不计失败）；
- 测试文件本身必须通过 `npx --no-install prettier --check tests` 与 `npx --no-install eslint tests`。

## 目录

```
frontend/tests/
├── helpers/
│   ├── harness.mjs          # Vite SSR 加载器 + 模块 mock（resolve.alias）
│   └── test-utils.mjs       # mock 全局状态、DOM 桩、setup() 调用、异步等待、Vue 告警过滤
├── mocks/                   # 被测源码依赖的 ESM 替身模块（详见各文件头部注释）
├── index.js                 # 聚合入口：兼容 `node --test tests/`（Node 24 目录参数语义）
├── workflow-api.test.mjs             # API 契约 + 与 backend/Workflow/urls.py 对齐
├── workflow-node.test.mjs            # WorkflowNode.vue 组件逻辑（icon/端口/百分比）
├── workflow-list.test.mjs            # WorkflowListView.vue 视图逻辑
├── workflow-editor.test.mjs          # WorkflowEditorView.vue 视图逻辑（主覆盖）
├── workflow-integration.test.mjs     # 路由/导航/入口/图标/main.ts/依赖 集成契约
└── workflow-known-defects.test.mjs   # 已知缺陷的 file:line 固定 + todo 修复目标
```

## 覆盖点

### 1. API 契约（`workflow-api.test.mjs`，26 个用例）

- 真实加载 `src/api/workflow.ts`（mock 掉 `./request`），**逐一断言 19 个导出函数**的
  HTTP method / URL（`/workflow/...` 前缀、路径参数插值）/ payload / query params；
- `runWorkflow` 的 `timeout: 120_000`；`listWorkflowEvents` 的 `after/limit` 自定义值；返回值透传；
- 与 `backend/Workflow/urls.py` 的 14 条路由逐条对齐（前端 URL 必须命中唯一后端 path），
  并与 `backend/Workflow/views.py` 的 `@api_view` 方法集合逐条校验（GET/POST/PATCH/DELETE 一致）；
- 静态确认 `src/api/request.ts` 的 `baseURL: '/api'` 与 `vite.config.ts` 的 `/api` 代理去前缀约定。

### 2. WorkflowNode 组件逻辑（`workflow-node.test.mjs`，7 个用例）

SSR 加载 `src/components/workflow/WorkflowNode.vue`，直接调用编译后的 setup() 断言模板绑定：

- icon 映射：start→play、llm→sparkles、http→globe、condition→branch、未知/空→workflow；
- meta 缺省时 inputs/outputs 回退 `in/out`；meta 自定义端口（condition 的 true/false）；空数组尊重原值；
- `portTop(index,total)` 百分比分布（含 total=0 边界）。

### 3. WorkflowListView 视图逻辑（`workflow-list.test.mjs`，16 个用例）

- `load` 成功赋值、业务错误（code!==0）、axios 错误优先取 `response.data.message`、未知错误回退；
- `submitCreate` 空名称提示、trim 后提交、成功 toast + `router.push('/workflows/{id}')`、失败展示错误；
- `remove` 的 `window.confirm` 取消/确认两分支、删除后重新 load、失败 toast；
- `formatTime` 合法日期格式化与非法日期回退。

### 4. WorkflowEditorView 视图逻辑（`workflow-editor.test.mjs`，34 个用例 / 2 个 todo）

- `buildNode` / `buildEdge` 映射；`applyState` 状态映射、事件序号单调、选中重置；`ensureMeta` 缓存；
- `defaultConfig`（json 序列化、boolean、空值）与 `coerceParam`（json/非法 JSON、number/NaN、boolean、string）；
- `canEdit` 角色矩阵（owner/editor/viewer/未加载）；
- 乐观锁：`savePosition` 成功回写版本、409 冲突时 toast.warning + 静默 refresh；
- `onConnect` 成功/默认端口回退/失败/只读守卫；`deleteSelection` 节点/连线/无选中三分支；
- `run` 成功/业务失败/网络异常/运行中防重；
- `openConfig` / `saveConfig` 参数回填、必填校验、coerce 后提交与版本回写；`addNode` 默认配置提交与只读守卫；
- 无效 `workflowId`（abc/0/-3）不请求后端且 pageError 提示；
- **已知缺陷**：members 数据来源、json 默认值二次编码（todo + 现状断言）。

### 5. 集成契约（`workflow-integration.test.mjs`，14 个用例 / 1 个 todo）

- 真实加载 `router/index.ts`（mock vue-router 工厂）：`/workflows`、`/workflows/:id` 的 path/name/meta.title，
  以及 `component()` 动态导入真实视图（`WorkflowListView` / `WorkflowEditorView`）与 AppLayout 布局路由；
- 导航守卫（requiresAuth / guestOnly / redirect）与 `afterEach` 的 `document.title`；
- `AppLayout` NAV_GROUPS 的工作流入口、id 与路由 name 对齐、to 与路由 path 对齐；
- `HomeView` 应用入口「工作流」可点击且路由存在；
- 真实加载 `AppIcon.vue`（使用真实 @lucide/vue）：workflow 组件映射、未知键回退 Circle；
  扫描 `src/**/*.vue` 的静态 `:name` / 动态 `:name` 字面量并真实执行 AppLayout/HomeView/App/WorkflowNode 的 setup，
  校验所有引用的图标名都已注册；
- 静态校验 `main.ts` 的 4 套 vue-flow 样式导入顺序、`package.json` 依赖/脚本且未引入测试框架依赖、
  `vite.config.ts` 的 @ 别名与 /api 代理、`backend/api/urls.py` 的 `workflow/` include。

### 6. 已知缺陷固定（`workflow-known-defects.test.mjs`，9 个用例 / 4 个 todo）

用 `file:line` 静态证据锁定缺陷位置，并用 `{ todo }` 标记修复目标；缺陷修复前测试套件保持绿色。

## 已知缺陷（被测模块，非测试代码）

| ID  | 级别 | 位置                                                                            | 现象                                                                                                                                     | 证据                                                                                                                         | 修复方向                                                                                 | 置信度                           |
| --- | ---- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------------------------- |
| D1  | P1   | `src/api/workflow.ts:97`、`src/views/WorkflowEditorView.vue:692,796`            | 协作人数/成员列表恒为空：`WorkflowState.members` 是顶层字段，编辑器只读 `workflow.members`，setup 也没有 members 状态                    | 实测（editor 用例 + setup 绑定无 members）；`npm run type-check` 报 692/796 TS2339                                           | 增加顶层 `members` ref，applyState/refreshMembers 同步 `state.members`，模板改读 members | 高（实测）                       |
| D2  | P1   | `src/views/WorkflowEditorView.vue:211`                                          | json 参数默认值为字符串时被二次 JSON 编码：`JSON.stringify("{}")` → `'"{}"'`，新增 start/http 节点后后端 `json.loads` 得到字符串而非对象 | 实测 `defaultConfig` / `addNode` 提交 payload；后端后果为静态推断（`backend/Workflow/node/start.py:28-40`、`http.py:58-66`） | 字符串默认值直接透传，仅对象默认值 stringify；或统一改为对象存储                         | 高（前端实测，后端后果静态推断） |
| D3  | P2   | `src/views/WorkflowEditorView.vue:300`                                          | eslint `preserve-caught-error` error：catch 后重抛 `new Error(msg)` 未带 `cause`，导致 `npm run lint:check` 失败                         | 实测 `npx eslint src/views/WorkflowEditorView.vue` → 300:7 error                                                             | `throw new Error(msg, { cause: err })`                                                   | 高（实测）                       |
| D4  | P2   | `src/views/WorkflowEditorView.vue:96,237,636,692,796`                           | `npm run type-check` 失败 5 个 TS 错误（96 TS2769 / 237 TS2589 / 636 TS2322 / 692、796 TS2339）                                          | 实测 `npm run type-check` 输出                                                                                               | 补全 nodeMetas 索引类型、Node 泛型、NodeTypes 类型、成员字段（与 D1 同源）               | 高（实测）                       |
| D5  | P3   | `src/views/WorkflowEditorView.vue:613` + `src/components/ui/AppIcon.vue:56-104` | 导出按钮使用 `name="download"`，AppIcon.ICONS 未注册该键，渲染回退为默认圆点（功能不受影响）                                             | 实测（组件逻辑 + 图标扫描断言）；静态证据 613 行                                                                             | 在 AppIcon.ICONS 补充 download（如 `Download`）                                          | 高（实测）                       |
| D6  | P3   | 项目根 `README.md`                                                              | 未记录 Workflow 模块（当前进度/功能特性/目录结构均无工作流）                                                                             | 静态：根 README 不含「工作流」                                                                                               | 补充模块说明与接口/页面清单                                                              | 高（静态）                       |

> D1–D5 属于「被测源码缺陷」，按任务要求**不修改生产代码**，也不让测试套件失败（todo 不计失败）。
> 修复缺陷后需要同步更新 `workflow-known-defects.test.mjs` 中的行号断言与 todo。

### 本次实测的基线（与 Lead 提供一致）

```text
$ npm run type-check
src/views/WorkflowEditorView.vue(96,21): error TS2769
src/views/WorkflowEditorView.vue(237,19): error TS2589
src/views/WorkflowEditorView.vue(636,10): error TS2322
src/views/WorkflowEditorView.vue(692,22): error TS2339
src/views/WorkflowEditorView.vue(796,42): error TS2339

$ npx eslint src/views/WorkflowEditorView.vue
300:7  error  There is no 'cause' attached to the symptom error being thrown  preserve-caught-error
```

另有 Lead 已确认的全项目基线：`npm run build` 退出码 1、`ruff check`/格式化问题（后端）、README 未记录工作流模块。

## 限制与未覆盖项

- **无浏览器/DOM/e2e**：测试不渲染组件（模板只做 SSR 编译、不执行渲染），因此
  Teleport 弹窗、CSS、拖拽、Vue Flow 画布交互、轮询定时器实际触发、键盘快捷键、
  导入文件选择器、导出 Blob 下载等**仅验证 setup 内的逻辑与 API 调用**，未验证真实 DOM 行为；
- 组件测试通过直接调用 `component.setup()` 断言模板绑定；`onMounted` / `onBeforeUnmount`
  等生命周期钩子在没有组件实例时不会执行（测试中手动调用 load/refresh 等函数）；
- `@vue-flow/*`、`@vueuse/core`、pinia stores、vue-router 等被 mock，集成行为以 mock 契约验证，
  不覆盖第三方库自身行为；
- 未与真实 Django 后端联调：HTTP 契约按 `urls.py`/`views.py` 静态对齐，响应数据结构按 `services.py` 的
  `_state/_node_dict/...` 形状夹具模拟；后端行为由 backend/tests 负责；
- 行号断言（known-defects）与现状断言（D1/D2 的「现状固定」用例）在缺陷修复后会失败，属于**有意设计**，
  修复时需同步更新；
- 任务描述称 workflow.ts 有 20 个导出函数，实测为 **19 个**（列表见 `workflow-api.test.mjs` 的 CASES），
  本报告按实测 19 个覆盖。
