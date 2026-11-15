/**
 * WorkflowEditorView.vue 视图逻辑测试。
 *
 * 无浏览器环境：SSR 加载真实 .vue（模板编译为 SSR 渲染函数但不渲染），
 * 直接调用 setup() 拿到模板绑定，mock 掉 vue-router / vue-flow / vueuse / stores / workflow api。
 */
import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createHarness } from './helpers/harness.mjs'
import {
  callSetup,
  installDomStubs,
  resetTestState,
  silenceVueSetupWarnings,
  waitFor,
} from './helpers/test-utils.mjs'

/** 与后端 node_loader.get_node_meta 的默认 meta 结构一致（见 backend/Workflow/node/start.py:9） */
const METAS = {
  start: {
    type: 'start',
    name: '开始',
    description: '工作流入口，向后传递初始数据。',
    category: '触发器',
    inputs: [],
    outputs: [{ id: 'out', label: '输出' }],
    params: [
      {
        key: 'payload',
        label: '初始数据（JSON）',
        type: 'json',
        default: '{}',
        required: false,
        help: '',
      },
    ],
  },
  llm: {
    type: 'llm',
    name: '大模型',
    description: '调用「模型服务」中已启用的对话模型。',
    category: 'AI',
    inputs: [{ id: 'in', label: '输入' }],
    outputs: [{ id: 'out', label: '输出' }],
    params: [
      { key: 'model_id', label: '模型 ID', type: 'number', required: true },
      {
        key: 'temperature',
        label: 'temperature',
        type: 'number',
        default: 0.7,
        required: false,
      },
      {
        key: 'system_prompt',
        label: '系统提示词',
        type: 'textarea',
        default: '你是一个简洁的助手。',
        required: false,
      },
    ],
  },
}

const INITIAL_STATE = {
  workflow: {
    id: 7,
    name: '主流程',
    description: '描述',
    owner_id: 1,
    owner_name: 'tester',
    role: 'owner',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
  nodes: [
    {
      key: 'n1',
      node_type: 'start',
      name: '开始',
      position: { x: 10, y: 20 },
      config: { payload: '{}' },
      version: 1,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      key: 'n2',
      node_type: 'llm',
      name: '大模型',
      position: { x: 100, y: 20 },
      config: {},
      version: 2,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
  ],
  relations: [
    {
      id: 3,
      source_key: 'n1',
      source_port: 'out',
      target_key: 'n2',
      target_port: 'in',
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
  members: [
    { user_id: 1, username: 'tester', role: 'owner', created_at: null },
    { user_id: 2, username: 'bob', role: 'editor', created_at: null },
  ],
  last_event_seq: 9,
  node_types: ['start', 'llm'],
}

function freshState(overrides = {}) {
  return structuredClone({ ...INITIAL_STATE, ...overrides })
}

let harness
let EditorView
let restoreWarnings

before(async () => {
  installDomStubs()
  restoreWarnings = silenceVueSetupWarnings()
  harness = await createHarness({
    mocks: [
      { find: 'vue-router', file: 'vue-router.mjs' },
      { find: '@vue-flow/core', file: 'vue-flow-core.mjs' },
      { find: '@vue-flow/background', file: 'vue-flow-background.mjs' },
      { find: '@vue-flow/controls', file: 'vue-flow-controls.mjs' },
      { find: '@vue-flow/minimap', file: 'vue-flow-minimap.mjs' },
      { find: '@vueuse/core', file: 'vueuse-core.mjs' },
      { find: '@/stores/auth', file: 'store-auth.mjs' },
      { find: '@/stores/theme', file: 'store-theme.mjs' },
      { find: '@/stores/toast', file: 'store-toast.mjs' },
      { find: '@/api/workflow', file: 'api-workflow.mjs' },
      { find: '@/components/ui/AppIcon.vue', file: 'app-icon.mjs' },
      { find: '@/components/workflow/WorkflowNode.vue', file: 'component-stub.mjs' },
    ],
  })
  const module = await harness.load('/src/views/WorkflowEditorView.vue')
  EditorView = module.default
})

after(async () => {
  restoreWarnings()
  await harness.close()
})

/** 同步调用 setup（有效 id 时 setup 内部会异步发起 refresh） */
function setupEditor(options = {}) {
  const { id = '7', api: apiOverrides = {} } = options
  const state = resetTestState({
    route: { params: { id }, meta: { title: '工作流编辑器' }, name: 'workflow-editor' },
  })
  const calls = {
    getWorkflow: 0,
    getNodeTypeMeta: [],
    addWorkflowNode: [],
    updateWorkflowNode: [],
    deleteWorkflowNode: [],
    deleteWorkflowRelation: [],
    addWorkflowRelation: [],
    runWorkflow: 0,
  }
  state.api = {
    getWorkflow: async () => {
      calls.getWorkflow += 1
      return { code: 0, message: 'ok', data: freshState() }
    },
    getNodeTypeMeta: async (type) => {
      calls.getNodeTypeMeta.push(type)
      return { code: 0, message: 'ok', data: { meta: structuredClone(METAS[type]) } }
    },
    ...apiOverrides,
  }
  const vm = callSetup(EditorView, {})
  return { vm, state, calls }
}

/** 等有效 workflowId 的初始 refresh/applyState 完成 */
async function mountEditor(options = {}) {
  const mounted = setupEditor(options)
  await waitFor(() => mounted.vm.loading.value === false)
  return mounted
}

/* ---------------- 初始化 / 数据转换 ---------------- */

test('初始化：refresh + applyState 把 WorkflowState 映射到画布状态', async () => {
  const { vm, state, calls } = await mountEditor()

  assert.equal(vm.workflowId.value, 7)
  assert.deepEqual(vm.workflow.value, INITIAL_STATE.workflow)
  assert.deepEqual(vm.nodeCatalog.value, ['start', 'llm'])
  assert.equal(vm.lastEventSeq.value, 9)
  assert.equal(vm.loading.value, false)
  assert.equal(vm.pageError.value, '')
  assert.equal(vm.syncing.value, false)
  assert.equal(vm.patternColor.value, '#dbe3f2')

  assert.equal(vm.nodes.value.length, 2)
  const startNode = vm.nodes.value[0]
  assert.equal(startNode.id, 'n1')
  assert.equal(startNode.type, 'start')
  assert.deepEqual(startNode.position, { x: 10, y: 20 })
  assert.equal(startNode.data.name, '开始')
  assert.equal(startNode.data.nodeType, 'start')
  assert.deepEqual(startNode.data.config, { payload: '{}' })
  assert.equal(startNode.data.version, 1)
  assert.equal(startNode.data.meta, vm.nodeMetas.start)
  assert.equal(vm.nodeMetas.start.name, '开始')

  assert.deepEqual(vm.edges.value, [
    {
      id: 'e-3',
      type: 'smoothstep',
      source: 'n1',
      sourceHandle: 'out',
      target: 'n2',
      targetHandle: 'in',
      data: { relationId: 3 },
    },
  ])

  assert.deepEqual(Object.keys(vm.nodeTypes.value).sort(), ['llm', 'start'])
  assert.equal(vm.nodeTypes.value.start, vm.nodeTypes.value.llm)
  assert.equal(vm.nodeTypes.value.start.name, 'ComponentStub')

  // 用到的节点类型按需拉取 meta，且轮询在 refresh 完成后启动
  assert.deepEqual(calls.getNodeTypeMeta.sort(), ['llm', 'start'])
  assert.equal(state.interval.resumeCalls, 1)
})

test('buildNode：WorkflowNodeState → Vue Flow Node（含 meta 注入）', async () => {
  const { vm } = await mountEditor()
  const nodeState = {
    key: 'n9',
    node_type: 'llm',
    name: '模型节点',
    position: { x: 3, y: 4 },
    config: { model_id: 2 },
    version: 6,
    created_at: '',
    updated_at: '',
  }
  const node = vm.buildNode(nodeState)
  assert.equal(node.id, 'n9')
  assert.equal(node.type, 'llm')
  assert.deepEqual(node.position, { x: 3, y: 4 })
  assert.deepEqual(node.data, {
    name: '模型节点',
    nodeType: 'llm',
    config: { model_id: 2 },
    version: 6,
    meta: vm.nodeMetas.llm,
  })

  const unknown = vm.buildNode({ ...nodeState, node_type: 'not-loaded' })
  assert.equal(unknown.data.meta, undefined)
})

test('buildEdge：WorkflowRelation → Vue Flow Edge（id 前缀 e-、relationId 放 data）', async () => {
  const { vm } = await mountEditor()
  const edge = vm.buildEdge({
    id: 12,
    source_key: 'a',
    source_port: 'true',
    target_key: 'b',
    target_port: 'in',
    created_at: '',
  })
  assert.deepEqual(edge, {
    id: 'e-12',
    type: 'smoothstep',
    source: 'a',
    sourceHandle: 'true',
    target: 'b',
    targetHandle: 'in',
    data: { relationId: 12 },
  })
})

test('applyState：lastEventSeq 单调递增、重置选中状态、节点/连线整体替换', async () => {
  const { vm } = await mountEditor()
  assert.equal(vm.lastEventSeq.value, 9)
  vm.selectedNodeId.value = 'n1'
  vm.selectedEdgeId.value = 'e-3'
  vm.selectedRelationId.value = 3

  await vm.applyState(freshState({ last_event_seq: 4 }))
  assert.equal(vm.lastEventSeq.value, 9, '事件序号不能被更小的值回退')
  assert.equal(vm.selectedNodeId.value, null)
  assert.equal(vm.selectedEdgeId.value, null)
  assert.equal(vm.selectedRelationId.value, null)

  await vm.applyState(freshState({ last_event_seq: 12, nodes: [], relations: [] }))
  assert.equal(vm.lastEventSeq.value, 12)
  assert.deepEqual(vm.nodes.value, [])
  assert.deepEqual(vm.edges.value, [])
})

test('ensureMeta：已加载的节点类型不会重复请求', async () => {
  const { vm, calls } = await mountEditor()
  const before = calls.getNodeTypeMeta.length
  await vm.ensureMeta('start')
  await vm.ensureMeta('llm')
  assert.equal(calls.getNodeTypeMeta.length, before)
})

/* ---------------- 参数默认值 / 类型转换 ---------------- */

test('defaultConfig：json 序列化、boolean 默认 false、其余空字符串', async () => {
  const { vm } = await mountEditor()
  const config = vm.defaultConfig({
    params: [
      { key: 'obj', type: 'json', default: { a: 1 } },
      { key: 'emptyJson', type: 'json' },
      { key: 'flag', type: 'boolean', default: true },
      { key: 'flagDefault', type: 'boolean' },
      { key: 'text', type: 'text' },
      { key: 'num', type: 'number', default: 15 },
      { key: 'zero', type: 'number', default: 0 },
      { key: 'list', type: 'select', default: 'GET' },
    ],
  })
  assert.deepEqual(config, {
    obj: '{"a":1}',
    emptyJson: '{}',
    flag: true,
    flagDefault: false,
    text: '',
    num: 15,
    zero: 0,
    list: 'GET',
  })
})

test('json 参数默认值为字符串时原样透传', async () => {
  const { vm } = await mountEditor()
  // 后端 start.NODE_META.params[0].default 与 http headers 的默认值都是字符串 "{}"
  const config = vm.defaultConfig(METAS.start)
  assert.equal(config.payload, '{}', '字符串默认值不应再 JSON.stringify')
  assert.deepEqual(JSON.parse(config.payload), {})
})

test(
  '已知缺陷（修复目标）：json 参数默认值应能被后端解析为 JSON 对象',
  { todo: 'defaultConfig 对字符串默认值再次 JSON.stringify，导致对象语义丢失；修复后移除待办' },
  async () => {
    const { vm } = await mountEditor()
    const config = vm.defaultConfig(METAS.start)
    const parsed = typeof config.payload === 'string' ? JSON.parse(config.payload) : config.payload
    assert.deepEqual(parsed, {})
  },
)

test('coerceParam：json 解析 / 非法 JSON、number / NaN、boolean、string', async () => {
  const { vm } = await mountEditor()
  const json = { key: 'json', label: 'JSON 参数', type: 'json' }
  const number = { key: 'num', label: '数字参数', type: 'number' }
  const boolean = { key: 'flag', label: '开关参数', type: 'boolean' }
  const text = { key: 'text', label: '文本参数', type: 'text' }

  assert.deepEqual(vm.coerceParam(json, ''), {})
  assert.deepEqual(vm.coerceParam(json, undefined), {})
  const objectValue = { a: 1 }
  assert.equal(vm.coerceParam(json, objectValue), objectValue)
  assert.deepEqual(vm.coerceParam(json, '{"a":1}'), { a: 1 })
  assert.throws(() => vm.coerceParam(json, '{oops'), /参数「JSON 参数」不是合法 JSON/)

  assert.equal(vm.coerceParam(number, ''), undefined)
  assert.equal(vm.coerceParam(number, undefined), undefined)
  assert.equal(vm.coerceParam(number, null), undefined)
  assert.equal(vm.coerceParam(number, '42'), 42)
  assert.equal(vm.coerceParam(number, '3.5'), 3.5)
  assert.throws(() => vm.coerceParam(number, 'abc'), /参数「数字参数」必须是数字/)

  assert.equal(vm.coerceParam(boolean, true), true)
  assert.equal(vm.coerceParam(boolean, false), false)
  assert.equal(
    vm.coerceParam(boolean, 'false'),
    true,
    'Boolean("false") 为 true：仅接受复选框的布尔输入',
  )

  assert.equal(vm.coerceParam(text, undefined), '')
  assert.equal(vm.coerceParam(text, 123), '123')
  assert.equal(vm.coerceParam(text, 'x'), 'x')
})

/* ---------------- 权限矩阵 ---------------- */

test('canEdit：owner/editor 可编辑，viewer 与未加载不可编辑', async () => {
  const { vm } = await mountEditor()
  const roles = [
    ['owner', true],
    ['editor', true],
    ['viewer', false],
  ]
  for (const [role, expected] of roles) {
    vm.workflow.value = { ...INITIAL_STATE.workflow, role }
    assert.equal(vm.canEdit.value, expected, role)
  }
  vm.workflow.value = null
  assert.equal(vm.canEdit.value, false)
})

/* ---------------- 加载失败 / 无效 id ---------------- */

test('refresh 业务失败：pageError 展示 message，画布保持为空', async () => {
  let calls = 0
  const { vm } = await mountEditor({
    api: {
      getWorkflow: async () => {
        calls += 1
        return { code: 1, message: '工作流不存在', data: null }
      },
    },
  })
  assert.equal(calls, 1)
  assert.equal(vm.pageError.value, '工作流不存在')
  assert.equal(vm.loading.value, false)
  assert.deepEqual(vm.nodes.value, [])
  assert.equal(vm.workflow.value, null)
})

test('refresh 网络异常：pageError 回退为「加载工作流失败」', async () => {
  const { vm } = await mountEditor({
    api: {
      getWorkflow: async () => {
        throw new Error('Request failed with status code 500')
      },
    },
  })
  assert.equal(vm.pageError.value, '加载工作流失败')
  assert.equal(vm.loading.value, false)
})

test('无效 workflowId（abc / 0 / -3）：不请求后端，pageError 提示，loading=false', async () => {
  for (const id of ['abc', '0', '-3']) {
    const { vm, calls } = setupEditor({ id })
    assert.ok(Number.isNaN(vm.workflowId.value) || vm.workflowId.value <= 0, id)
    assert.equal(vm.pageError.value, '无效的工作流 ID', id)
    assert.equal(vm.loading.value, false, id)
    assert.equal(calls.getWorkflow, 0, id)
  }
})

/* ---------------- 位置保存（乐观锁） ---------------- */

test('savePosition 成功：携带 base_version 提交位置并回写新版本号', async () => {
  const payloads = []
  const { vm } = await mountEditor({
    api: {
      updateWorkflowNode: async (workflowId, nodeKey, payload) => {
        payloads.push({ workflowId, nodeKey, payload })
        return { code: 0, message: 'ok', data: { node: { version: 6 } } }
      },
    },
  })
  const node = { id: 'n1', position: { x: 30, y: 40 }, data: { version: 5 } }
  await vm.savePosition(node)

  assert.deepEqual(payloads, [
    {
      workflowId: 7,
      nodeKey: 'n1',
      payload: { base_version: 5, position: { x: 30, y: 40 } },
    },
  ])
  assert.equal(node.data.version, 6)
})

test('savePosition 冲突：toast.warning 并 refresh 拉取最新状态', async () => {
  const { vm, calls } = await mountEditor({
    api: {
      updateWorkflowNode: async () => ({
        code: 409,
        message: '节点已被其他人修改，请刷新后重试',
        data: null,
      }),
    },
  })
  const node = { id: 'n1', position: { x: 99, y: 99 }, data: { version: 5 } }
  assert.equal(calls.getWorkflow, 1)
  await vm.savePosition(node)

  const state = globalThis.__wfTestState
  assert.deepEqual(
    state.toast.calls.filter((item) => item.level === 'warning'),
    [{ level: 'warning', args: ['节点位置保存失败', '节点已被其他人修改，请刷新后重试'] }],
  )
  assert.equal(calls.getWorkflow, 2, '冲突后应静默 refresh 一次')
  assert.equal(node.data.version, 5, '冲突时不应回写版本号')
  assert.deepEqual(vm.nodes.value[0].position, { x: 10, y: 20 }, 'refresh 应恢复服务端位置')
})

/* ---------------- 连线 ---------------- */

test('onConnect 成功：提交端口并 addEdges 到画布', async () => {
  const payloads = []
  const { vm, state } = await mountEditor({
    api: {
      addWorkflowRelation: async (workflowId, payload) => {
        payloads.push({ workflowId, payload })
        return {
          code: 0,
          message: 'ok',
          data: {
            relation: {
              id: 9,
              source_key: 'n1',
              source_port: 'out1',
              target_key: 'n2',
              target_port: 'in1',
              created_at: '',
            },
          },
        }
      },
    },
  })
  await vm.onConnect({
    source: 'n1',
    target: 'n2',
    sourceHandle: 'out1',
    targetHandle: 'in1',
  })

  assert.deepEqual(payloads, [
    {
      workflowId: 7,
      payload: { source_key: 'n1', source_port: 'out1', target_key: 'n2', target_port: 'in1' },
    },
  ])
  assert.deepEqual(state.vueFlow.addEdgesCalls, [
    [
      {
        id: 'e-9',
        type: 'smoothstep',
        source: 'n1',
        sourceHandle: 'out1',
        target: 'n2',
        targetHandle: 'in1',
        data: { relationId: 9 },
      },
    ],
  ])
  assert.deepEqual(state.toast.calls, [{ level: 'success', args: ['连线已添加'] }])
})

test('onConnect：未提供 handle 时回退 out / in 端口', async () => {
  const payloads = []
  const { vm } = await mountEditor({
    api: {
      addWorkflowRelation: async (workflowId, payload) => {
        payloads.push(payload)
        return { code: 0, message: 'ok', data: { relation: { id: 4, created_at: '' } } }
      },
    },
  })
  await vm.onConnect({ source: 'n1', target: 'n2' })
  assert.deepEqual(payloads, [
    { source_key: 'n1', source_port: 'out', target_key: 'n2', target_port: 'in' },
  ])
})

test('onConnect 失败：toast.error，不向画布加边', async () => {
  const { vm, state } = await mountEditor({
    api: {
      addWorkflowRelation: async () => ({ code: 400, message: '不允许形成环', data: null }),
    },
  })
  await vm.onConnect({ source: 'n1', target: 'n2' })
  assert.deepEqual(state.vueFlow.addEdgesCalls, [])
  assert.deepEqual(state.toast.calls, [{ level: 'error', args: ['连线失败', '不允许形成环'] }])
})

test('onConnect 只读角色：不请求后端', async () => {
  let calls = 0
  const { vm } = await mountEditor({
    api: {
      addWorkflowRelation: async () => {
        calls += 1
        return { code: 0, data: { relation: { id: 1 } } }
      },
    },
  })
  vm.workflow.value = { ...INITIAL_STATE.workflow, role: 'viewer' }
  await vm.onConnect({ source: 'n1', target: 'n2' })
  assert.equal(calls, 0)
})

/* ---------------- 删除选中 ---------------- */

test('deleteSelection：删除节点时同步清理关联连线', async () => {
  const deleted = []
  const { vm, state } = await mountEditor({
    api: {
      deleteWorkflowNode: async (workflowId, nodeKey) => {
        deleted.push({ workflowId, nodeKey })
        return { code: 0, message: 'ok', data: { key: nodeKey } }
      },
    },
  })
  vm.selectedNodeId.value = 'n1'
  vm.selectedEdgeId.value = 'e-3'
  vm.selectedRelationId.value = 3
  vm.configDrawer.value = true

  await vm.deleteSelection()

  assert.deepEqual(deleted, [{ workflowId: 7, nodeKey: 'n1' }])
  assert.deepEqual(
    vm.nodes.value.map((node) => node.id),
    ['n2'],
  )
  assert.deepEqual(vm.edges.value, [])
  assert.equal(vm.selectedNodeId.value, null)
  assert.equal(vm.configDrawer.value, false)
  assert.deepEqual(state.toast.calls, [{ level: 'success', args: ['节点已删除'] }])
})

test('deleteSelection：删除连线走 relation 接口并按 relationId 过滤', async () => {
  const deleted = []
  const { vm, state } = await mountEditor({
    api: {
      deleteWorkflowRelation: async (workflowId, relationId) => {
        deleted.push({ workflowId, relationId })
        return { code: 0, message: 'ok', data: { id: relationId } }
      },
    },
  })
  vm.edges.value = [
    { id: 'e-3', data: { relationId: 3 } },
    { id: 'e-4', data: { relationId: 4 } },
  ]
  vm.selectedEdgeId.value = 'e-3'
  vm.selectedRelationId.value = 3
  vm.selectedNodeId.value = null

  await vm.deleteSelection()

  assert.deepEqual(deleted, [{ workflowId: 7, relationId: 3 }])
  assert.deepEqual(vm.edges.value, [{ id: 'e-4', data: { relationId: 4 } }])
  assert.equal(vm.selectedEdgeId.value, null)
  assert.equal(vm.selectedRelationId.value, null)
  assert.deepEqual(state.toast.calls, [{ level: 'success', args: ['连线已删除'] }])
})

test('deleteSelection：无选中时不发请求', async () => {
  let calls = 0
  const { vm } = await mountEditor({
    api: {
      deleteWorkflowNode: async () => {
        calls += 1
        return { code: 0, data: {} }
      },
      deleteWorkflowRelation: async () => {
        calls += 1
        return { code: 0, data: {} }
      },
    },
  })
  await vm.deleteSelection()
  assert.equal(calls, 0)
})

/* ---------------- 运行 ---------------- */

const RUN_RESULT = {
  status: 'success',
  error: '',
  steps: [
    {
      node_key: 'n1',
      node_type: 'start',
      name: '开始',
      status: 'success',
      duration_ms: 3,
      output: { payload: {} },
    },
  ],
  output: { payload: {} },
  duration_ms: 12,
}

test('run 成功：写入 runResult 并打开结果弹窗', async () => {
  let calls = 0
  const { vm } = await mountEditor({
    api: {
      runWorkflow: async () => {
        calls += 1
        return { code: 0, message: 'ok', data: structuredClone(RUN_RESULT) }
      },
    },
  })
  await vm.run()
  assert.equal(calls, 1)
  assert.deepEqual(vm.runResult.value, RUN_RESULT)
  assert.equal(vm.runModal.value, true)
  assert.equal(vm.running.value, false)
})

test('run 业务失败：toast.error，不打开结果弹窗', async () => {
  const { vm, state } = await mountEditor({
    api: {
      runWorkflow: async () => ({ code: 1, message: '执行失败：开始节点配置错误', data: null }),
    },
  })
  await vm.run()
  assert.equal(vm.runResult.value, null)
  assert.equal(vm.runModal.value, false)
  assert.equal(vm.running.value, false)
  assert.deepEqual(state.toast.calls, [
    { level: 'error', args: ['运行失败', '执行失败：开始节点配置错误'] },
  ])
})

test('run 网络异常：toast.error 展示异常信息', async () => {
  const { vm, state } = await mountEditor({
    api: {
      runWorkflow: async () => {
        throw new Error('Request failed with status code 500')
      },
    },
  })
  await vm.run()
  // getErrorMessage 会跳过 axios 的 'Request failed...' 文案，回退到默认网络错误提示
  assert.deepEqual(state.toast.calls, [
    { level: 'error', args: ['运行失败', '网络错误，请稍后再试'] },
  ])
})

test('run 进行中重复点击：不重复请求', async () => {
  let calls = 0
  const { vm } = await mountEditor({
    api: {
      runWorkflow: async () => {
        calls += 1
        return { code: 0, data: structuredClone(RUN_RESULT) }
      },
    },
  })
  vm.running.value = true
  await vm.run()
  assert.equal(calls, 0)
})

/* ---------------- 节点配置抽屉 ---------------- */

test('openConfig：editingNodeKey 存 node_type（用于查 meta）、回填版本/名称/参数', async () => {
  const { vm } = await mountEditor()
  const node = vm.nodes.value[1]
  node.data.config = { model_id: 3, system_prompt: '自定义提示词' }
  vm.openConfig({ node })

  assert.equal(vm.selectedNodeId.value, 'n2')
  assert.equal(
    vm.editingNodeKey.value,
    'llm',
    '存储的是 node_type 而非节点 key（命名问题，非功能 bug）',
  )
  assert.equal(vm.editingVersion.value, 2)
  assert.equal(vm.nodeNameForm.value, '大模型')
  assert.equal(vm.configError.value, '')
  assert.equal(vm.configDrawer.value, true)
  assert.deepEqual(vm.configForm, {
    model_id: 3,
    temperature: 0.7,
    system_prompt: '自定义提示词',
  })
  assert.equal(vm.editingMeta.value, vm.nodeMetas.llm)
})

test('saveConfig：必填参数为空时给出错误且不发请求', async () => {
  let calls = 0
  const { vm } = await mountEditor({
    api: {
      updateWorkflowNode: async () => {
        calls += 1
        return { code: 0, data: { node: { version: 3 } } }
      },
    },
  })
  vm.openConfig({ node: vm.nodes.value[1] })
  vm.configForm.model_id = ''
  await vm.saveConfig()
  assert.equal(calls, 0)
  assert.equal(vm.configError.value, '参数「模型 ID」不能为空')
  assert.equal(vm.savingConfig.value, false)
})

test('saveConfig 成功：coerce 参数、提交 base_version、回写节点并关闭抽屉', async () => {
  const payloads = []
  const { vm, state } = await mountEditor({
    api: {
      updateWorkflowNode: async (workflowId, nodeKey, payload) => {
        payloads.push({ workflowId, nodeKey, payload })
        return {
          code: 0,
          message: 'ok',
          data: {
            node: {
              name: '模型节点',
              config: { model_id: 5, temperature: 0.7, system_prompt: '你是一个简洁的助手。' },
              version: 3,
            },
          },
        }
      },
    },
  })
  vm.openConfig({ node: vm.nodes.value[1] })
  vm.nodeNameForm.value = '  模型节点  '
  vm.configForm.model_id = '5'
  await vm.saveConfig()

  assert.deepEqual(payloads, [
    {
      workflowId: 7,
      nodeKey: 'n2',
      payload: {
        base_version: 2,
        name: '模型节点',
        config: { model_id: 5, temperature: 0.7, system_prompt: '你是一个简洁的助手。' },
      },
    },
  ])
  assert.equal(vm.nodes.value[1].data.name, '模型节点')
  assert.equal(vm.nodes.value[1].data.version, 3)
  assert.equal(vm.editingVersion.value, 3)
  assert.equal(vm.configDrawer.value, false)
  assert.deepEqual(state.toast.calls, [{ level: 'success', args: ['节点参数已保存'] }])
})

/* ---------------- 新增节点 ---------------- */

test('addNode：使用 meta 默认配置并追加节点（json 默认值现状见已知缺陷）', async () => {
  const payloads = []
  const { vm, state } = await mountEditor({
    api: {
      addWorkflowNode: async (workflowId, payload) => {
        payloads.push({ workflowId, payload })
        return {
          code: 0,
          message: 'ok',
          data: { node: { ...INITIAL_STATE.nodes[0], key: 'n3', name: '开始' } },
        }
      },
    },
  })
  await vm.addNode('start')

  assert.equal(payloads.length, 1)
  assert.equal(payloads[0].workflowId, 7)
  assert.equal(payloads[0].payload.node_type, 'start')
  assert.equal(payloads[0].payload.name, '开始')
  assert.deepEqual(payloads[0].payload.position, { x: 640, y: 80 })
  assert.equal(payloads[0].payload.config.payload, '{}')
  assert.equal(vm.nodes.value.length, 3)
  assert.equal(vm.paletteOpen.value, false)
  assert.deepEqual(state.toast.calls, [{ level: 'success', args: ['已添加节点：开始'] }])
})

test('addNode：只读角色不请求后端', async () => {
  let calls = 0
  const { vm } = await mountEditor({
    api: {
      addWorkflowNode: async () => {
        calls += 1
        return { code: 0, data: { node: { ...INITIAL_STATE.nodes[0], key: 'n3' } } }
      },
    },
  })
  vm.workflow.value = { ...INITIAL_STATE.workflow, role: 'viewer' }
  await vm.addNode('start')
  assert.equal(calls, 0)
})

/* ---------------- 协作者成员 ---------------- */

test('members 状态从 WorkflowState.members 同步', async () => {
  const { vm } = await mountEditor()
  assert.equal(Object.hasOwn(vm, 'members'), true)
  assert.equal(vm.members.value.length, 2)
  assert.equal(vm.workflow.value.members, undefined) // workflow 对象仍不含 members
})

test('编辑器协作人数/列表来自 WorkflowState.members', async () => {
  const { vm } = await mountEditor()
  assert.equal(vm.members.value.length, 2)
})

test('refreshMembers：同步 workflow 与 members', async () => {
  const { vm } = await mountEditor()
  await vm.openMembers()
  assert.equal(vm.membersModal.value, true)
  assert.equal(globalThis.__wfTestState.toast.calls.length, 0)
  assert.equal(vm.workflow.value.name, '主流程')
  assert.equal(vm.members.value.length, 2)
})
