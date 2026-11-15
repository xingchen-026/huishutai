/**
 * workflow API 契约测试：真实加载 src/api/workflow.ts（mock 掉 axios 实例），
 * 逐一断言 19 个导出函数的 HTTP method / URL / payload / params，
 * 并与 backend/Workflow/urls.py + views.py 的路由、方法契约逐条对齐。
 */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { after, before, test } from 'node:test'
import { createHarness, frontendRoot, repoRoot } from './helpers/harness.mjs'
import { resetTestState } from './helpers/test-utils.mjs'

const DOCUMENT = {
  format: 'huishutai-workflow',
  format_version: 1,
  name: '示例',
  description: '',
  nodes: [{ key: 'n1', type: 'start', name: '开始', position: { x: 0, y: 0 }, config: {} }],
  relations: [],
}

/** 每个导出函数的期望 HTTP 调用（URL 中的 id 用固定值代替）。 */
const CASES = [
  {
    fn: 'listWorkflows',
    args: [],
    method: 'get',
    url: '/workflow/workflows/',
    backend: 'workflows/',
    view: 'workflows',
  },
  {
    fn: 'createWorkflow',
    args: [{ name: '新流程', description: '描述' }],
    method: 'post',
    url: '/workflow/workflows/',
    second: { name: '新流程', description: '描述' },
    backend: 'workflows/',
    view: 'workflows',
  },
  {
    fn: 'getWorkflow',
    args: [7],
    method: 'get',
    url: '/workflow/workflows/7/',
    backend: 'workflows/<int:workflow_id>/',
    view: 'workflow_detail',
  },
  {
    fn: 'updateWorkflow',
    args: [7, { name: '改名' }],
    method: 'patch',
    url: '/workflow/workflows/7/',
    second: { name: '改名' },
    backend: 'workflows/<int:workflow_id>/',
    view: 'workflow_detail',
  },
  {
    fn: 'deleteWorkflow',
    args: [7],
    method: 'delete',
    url: '/workflow/workflows/7/',
    backend: 'workflows/<int:workflow_id>/',
    view: 'workflow_detail',
  },
  {
    fn: 'listWorkflowEvents',
    args: [7],
    method: 'get',
    url: '/workflow/workflows/7/events/',
    second: { params: { after: 0, limit: 100 } },
    backend: 'workflows/<int:workflow_id>/events/',
    view: 'workflow_events',
  },
  {
    fn: 'addWorkflowNode',
    args: [7, { node_type: 'start', name: '开始', position: { x: 1, y: 2 }, config: {} }],
    method: 'post',
    url: '/workflow/workflows/7/nodes/',
    second: { node_type: 'start', name: '开始', position: { x: 1, y: 2 }, config: {} },
    backend: 'workflows/<int:workflow_id>/nodes/',
    view: 'workflow_nodes',
  },
  {
    fn: 'updateWorkflowNode',
    args: [7, 'node-a', { base_version: 3, position: { x: 5, y: 6 } }],
    method: 'patch',
    url: '/workflow/workflows/7/nodes/node-a/',
    second: { base_version: 3, position: { x: 5, y: 6 } },
    backend: 'workflows/<int:workflow_id>/nodes/<str:node_key>/',
    view: 'workflow_node_detail',
  },
  {
    fn: 'deleteWorkflowNode',
    args: [7, 'node-a'],
    method: 'delete',
    url: '/workflow/workflows/7/nodes/node-a/',
    backend: 'workflows/<int:workflow_id>/nodes/<str:node_key>/',
    view: 'workflow_node_detail',
  },
  {
    fn: 'addWorkflowRelation',
    args: [7, { source_key: 'a', target_key: 'b' }],
    method: 'post',
    url: '/workflow/workflows/7/edges/',
    second: { source_key: 'a', target_key: 'b' },
    backend: 'workflows/<int:workflow_id>/edges/',
    view: 'workflow_edges',
  },
  {
    fn: 'deleteWorkflowRelation',
    args: [7, 12],
    method: 'delete',
    url: '/workflow/workflows/7/edges/12/',
    backend: 'workflows/<int:workflow_id>/edges/<int:edge_id>/',
    view: 'workflow_edge_detail',
  },
  {
    fn: 'importWorkflow',
    args: [7, DOCUMENT],
    method: 'post',
    url: '/workflow/workflows/7/import/',
    second: DOCUMENT,
    backend: 'workflows/<int:workflow_id>/import/',
    view: 'workflow_import',
  },
  {
    fn: 'exportWorkflow',
    args: [7],
    method: 'get',
    url: '/workflow/workflows/7/export/',
    backend: 'workflows/<int:workflow_id>/export/',
    view: 'workflow_export',
  },
  {
    fn: 'runWorkflow',
    args: [7],
    method: 'post',
    url: '/workflow/workflows/7/run/',
    second: {},
    third: { timeout: 120_000 },
    backend: 'workflows/<int:workflow_id>/run/',
    view: 'workflow_run',
  },
  {
    fn: 'listWorkflowMembers',
    args: [7],
    method: 'get',
    url: '/workflow/workflows/7/members/',
    backend: 'workflows/<int:workflow_id>/members/',
    view: 'workflow_members',
  },
  {
    fn: 'addWorkflowMember',
    args: [7, { username: 'alice', role: 'viewer' }],
    method: 'post',
    url: '/workflow/workflows/7/members/',
    second: { username: 'alice', role: 'viewer' },
    backend: 'workflows/<int:workflow_id>/members/',
    view: 'workflow_members',
  },
  {
    fn: 'removeWorkflowMember',
    args: [7, 5],
    method: 'delete',
    url: '/workflow/workflows/7/members/5/',
    backend: 'workflows/<int:workflow_id>/members/<int:user_id>/',
    view: 'workflow_member_detail',
  },
  {
    fn: 'listNodeTypes',
    args: [],
    method: 'get',
    url: '/workflow/node-types/',
    backend: 'node-types/',
    view: 'node_types',
  },
  {
    fn: 'getNodeTypeMeta',
    args: ['llm'],
    method: 'get',
    url: '/workflow/node-types/llm/',
    backend: 'node-types/<str:node_type>/',
    view: 'node_type_detail',
  },
]

/** 后端 urls.py 中的 path 片段 → 测试里使用的具体值 */
const URL_VALUES = {
  '<int:workflow_id>': '7',
  '<str:node_key>': 'node-a',
  '<int:edge_id>': '12',
  '<int:user_id>': '5',
  '<str:node_type>': 'llm',
}

let harness
let api

before(async () => {
  resetTestState()
  harness = await createHarness({ mocks: [{ find: './request', file: 'request.mjs' }] })
  api = await harness.load('/src/api/workflow.ts')
})

after(async () => {
  await harness.close()
})

test('workflow.ts 恰有 19 个 API 导出函数，且全部被契约用例覆盖', () => {
  const exported = Object.keys(api)
    .filter((key) => typeof api[key] === 'function')
    .sort()
  const expected = CASES.map((item) => item.fn).sort()
  assert.deepEqual(exported, expected)
  assert.equal(exported.length, 19)
})

for (const item of CASES) {
  test(`${item.fn}: ${item.method.toUpperCase()} ${item.url}`, async () => {
    const state = resetTestState()
    await api[item.fn](...item.args)

    assert.equal(state.request.calls.length, 1, '应恰好发起一次请求')
    const call = state.request.calls[0]
    assert.equal(call.method, item.method)
    assert.equal(call.url, item.url)
    assert.deepEqual(call.second, item.second)
    assert.deepEqual(call.third, item.third)
  })
}

test('runWorkflow 显式设置 120000ms 超时（后端同步执行可能较慢）', async () => {
  resetTestState()
  await api.runWorkflow(7)
  const call = getCall()
  assert.deepEqual(call.third, { timeout: 120_000 })
})

test('listWorkflowEvents 支持自定义 after/limit', async () => {
  resetTestState()
  await api.listWorkflowEvents(7, 25, 50)
  const call = getCall()
  assert.deepEqual(call.second, { params: { after: 25, limit: 50 } })
})

test('API 返回值原样透传 request 的结果（不二次包装）', async () => {
  const state = resetTestState()
  const marker = { code: 0, message: 'ok', data: { total: 0, workflows: [] } }
  state.request.handler = () => Promise.resolve(marker)
  const result = await api.listWorkflows()
  assert.equal(result, marker)
})

test('request.ts 使用 /api 作为 baseURL（前端 URL 与后端 /workflow/ 前缀之间的约定）', () => {
  const source = fs.readFileSync(path.join(frontendRoot, 'src/api/request.ts'), 'utf8')
  assert.match(source, /baseURL:\s*'\/api'/)
  // 开发环境由 vite proxy 去掉 /api 前缀（vite.config.ts）
  const viteConfig = fs.readFileSync(path.join(frontendRoot, 'vite.config.ts'), 'utf8')
  assert.match(viteConfig, /rewrite:\s*\(path\)\s*=>\s*path\.replace\(\/\^\\\/api\//)
})

function getCall() {
  const state = globalThis.__wfTestState
  assert.equal(state.request.calls.length, 1)
  return state.request.calls[0]
}

function readBackendUrls() {
  const source = fs.readFileSync(path.join(repoRoot, 'backend/Workflow/urls.py'), 'utf8')
  const entries = []
  const pattern = /path\(\s*"([^"]+)"\s*,\s*views\.(\w+)/g
  let match
  while ((match = pattern.exec(source)) !== null) {
    entries.push({ path: match[1], view: match[2] })
  }
  return entries
}

function readBackendViewMethods() {
  const source = fs.readFileSync(path.join(repoRoot, 'backend/Workflow/views.py'), 'utf8')
  const methodsByView = new Map()
  const pattern = /@api_view\(\[([^\]]+)\]\)\s*\ndef\s+(\w+)/g
  let match
  while ((match = pattern.exec(source)) !== null) {
    const methods = [...match[1].matchAll(/"([A-Z]+)"/g)].map((item) => item[1].toLowerCase())
    methodsByView.set(match[2], methods)
  }
  return methodsByView
}

/**
 * 把后端 path() 模板替换成具体值，得到前端 axios 请求行里的相对 URL。
 * 最终网络 URL = baseURL('/api') + url，开发代理再去掉 /api 前缀转发到后端。
 */
function concreteBackendUrl(template) {
  let suffix = template
  for (const [token, value] of Object.entries(URL_VALUES)) {
    suffix = suffix.split(token).join(value)
  }
  return `/workflow/${suffix}`
}

test('前端每个 API URL/method 都能在 backend/Workflow/urls.py 中命中唯一路由', () => {
  const backendUrls = readBackendUrls()
  assert.ok(backendUrls.length >= 14, `后端应至少注册 14 条工作流路由，实际 ${backendUrls.length}`)

  const usedBackendPaths = new Set()
  for (const item of CASES) {
    const expectedUrl = concreteBackendUrl(item.backend)
    assert.equal(item.url, expectedUrl, `${item.fn} 的 URL 与后端路由不一致`)

    const matched = backendUrls.filter((entry) => entry.path === item.backend)
    assert.equal(matched.length, 1, `${item.fn} 应命中唯一后端路由 ${item.backend}`)
    assert.equal(matched[0].view, item.view)
    usedBackendPaths.add(item.backend)
  }

  const allBackendPaths = new Set(backendUrls.map((entry) => entry.path))
  assert.deepEqual(
    [...usedBackendPaths].sort(),
    [...allBackendPaths].sort(),
    '后端路由应全部被前端 API 覆盖',
  )
})

test('前端 HTTP method 均被对应 DRF 视图的 @api_view 允许', () => {
  const methodsByView = readBackendViewMethods()
  assert.ok(methodsByView.size >= 14, `应解析到至少 14 个 DRF 视图，实际 ${methodsByView.size}`)
  for (const item of CASES) {
    const allowed = methodsByView.get(item.view)
    assert.ok(allowed, `views.py 中不存在视图 ${item.view}`)
    assert.ok(
      allowed.includes(item.method),
      `${item.fn} 使用 ${item.method}，但 ${item.view} 只允许 ${allowed.join('/')}`,
    )
  }
})
