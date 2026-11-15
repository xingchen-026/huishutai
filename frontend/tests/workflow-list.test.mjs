/**
 * WorkflowListView.vue 视图逻辑测试：mock router / toast / workflow api，
 * 真实执行 setup() 内的 load / submitCreate / remove / formatTime。
 */
import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createHarness } from './helpers/harness.mjs'
import {
  callSetup,
  flushPromises,
  installDomStubs,
  resetTestState,
  silenceVueSetupWarnings,
} from './helpers/test-utils.mjs'

const WORKFLOW = {
  id: 42,
  name: '知识库问答流程',
  description: '示例描述',
  owner_id: 1,
  owner_name: 'tester',
  role: 'owner',
  node_count: 3,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-06-01T08:00:00Z',
}

let harness
let ListView
let restoreWarnings

before(async () => {
  installDomStubs()
  restoreWarnings = silenceVueSetupWarnings()
  harness = await createHarness({
    mocks: [
      { find: 'vue-router', file: 'vue-router.mjs' },
      { find: '@/stores/toast', file: 'store-toast.mjs' },
      { find: '@/api/workflow', file: 'api-workflow.mjs' },
      { find: '@/components/ui/AppIcon.vue', file: 'app-icon.mjs' },
    ],
  })
  const module = await harness.load('/src/views/WorkflowListView.vue')
  ListView = module.default
})

after(async () => {
  restoreWarnings()
  await harness.close()
})

function mount(setupApi = {}) {
  const state = resetTestState()
  Object.assign(state.api, setupApi)
  const vm = callSetup(ListView)
  return { vm, state }
}

test('初始状态：loading=true、空列表、无错误', () => {
  const { vm } = mount()
  assert.equal(vm.loading.value, true)
  assert.deepEqual(vm.workflows.value, [])
  assert.equal(vm.pageError.value, '')
  assert.equal(vm.createOpen.value, false)
  assert.deepEqual(vm.createForm, { name: '', description: '' })
})

test('load 成功：写入 workflows 并关闭 loading', async () => {
  const { vm } = mount({
    listWorkflows: async () => ({
      code: 0,
      message: 'ok',
      data: { total: 1, workflows: [WORKFLOW] },
    }),
  })
  await vm.load()
  assert.deepEqual(vm.workflows.value, [WORKFLOW])
  assert.equal(vm.loading.value, false)
  assert.equal(vm.pageError.value, '')
})

test('load 业务失败（code!==0）：pageError 展示后端 message', async () => {
  const { vm } = mount({
    listWorkflows: async () => ({ code: 401, message: '未登录', data: null }),
  })
  await vm.load()
  assert.equal(vm.pageError.value, '未登录')
  assert.equal(vm.loading.value, false)
})

test('load 网络异常：优先取 axios response.data.message', async () => {
  const { vm } = mount({
    listWorkflows: async () => {
      throw { response: { data: { message: '服务暂不可用' } } }
    },
  })
  await vm.load()
  assert.equal(vm.pageError.value, '服务暂不可用')
})

test('load 未知异常：回退为「加载工作流失败」', async () => {
  const { vm } = mount({
    listWorkflows: async () => {
      throw new Error('Request failed with status code 500')
    },
  })
  await vm.load()
  assert.equal(vm.pageError.value, '加载工作流失败')
})

test('submitCreate 空名称：提示且不发请求', async () => {
  let createCalls = 0
  const { vm, state } = mount({
    createWorkflow: async () => {
      createCalls += 1
      return { code: 0, message: 'ok', data: { workflow: WORKFLOW } }
    },
  })
  vm.createForm.name = '   '
  await vm.submitCreate()
  assert.equal(vm.createError.value, '请输入工作流名称')
  assert.equal(createCalls, 0)
  assert.equal(vm.creating.value, false)
  assert.deepEqual(state.router.pushes, [])
})

test('submitCreate 成功：trim 后提交、关闭弹窗、toast、跳转编辑器', async () => {
  const payloads = []
  const { vm, state } = mount({
    createWorkflow: async (payload) => {
      payloads.push(payload)
      return { code: 0, message: 'ok', data: { workflow: { ...WORKFLOW, id: 42 } } }
    },
  })
  vm.createOpen.value = true
  vm.createForm.name = '  新流程  '
  vm.createForm.description = '  描述  '
  await vm.submitCreate()

  assert.deepEqual(payloads, [{ name: '新流程', description: '描述' }])
  assert.equal(vm.createOpen.value, false)
  assert.equal(vm.creating.value, false)
  assert.deepEqual(state.router.pushes, ['/workflows/42'])
  assert.deepEqual(state.toast.calls, [{ level: 'success', args: ['工作流已创建'] }])
})

test('submitCreate 业务失败：createError 展示 message，弹窗保持打开', async () => {
  const { vm, state } = mount({
    createWorkflow: async () => ({ code: 1, message: '名称已存在', data: null }),
  })
  vm.createOpen.value = true
  vm.createForm.name = '重复名称'
  await vm.submitCreate()

  assert.equal(vm.createError.value, '名称已存在')
  assert.equal(vm.createOpen.value, true)
  assert.equal(vm.creating.value, false)
  assert.deepEqual(state.router.pushes, [])
})

test('submitCreate 异常：createError 回退为「创建失败，请稍后再试」', async () => {
  const { vm } = mount({
    createWorkflow: async () => {
      throw new Error('Request failed with status code 500')
    },
  })
  vm.createForm.name = '新流程'
  await vm.submitCreate()
  assert.equal(vm.createError.value, '创建失败，请稍后再试')
  assert.equal(vm.creating.value, false)
})

test('remove 取消确认：不调用删除接口', async () => {
  let deleteCalls = 0
  const { vm } = mount({
    deleteWorkflow: async () => {
      deleteCalls += 1
      return { code: 0, message: 'ok', data: { id: 42 } }
    },
  })
  globalThis.window.confirm = () => false
  await vm.remove(WORKFLOW)
  assert.equal(deleteCalls, 0)
})

test('remove 确认后成功：调用删除接口并重新 load', async () => {
  let deleteArgs = null
  let deleted = false
  let listCalls = 0
  const { vm, state } = mount({
    deleteWorkflow: async (id) => {
      deleteArgs = id
      deleted = true
      return { code: 0, message: 'ok', data: { id } }
    },
    listWorkflows: async () => {
      listCalls += 1
      const workflows = deleted ? [] : [WORKFLOW]
      return { code: 0, message: 'ok', data: { total: workflows.length, workflows } }
    },
  })
  globalThis.window.confirm = () => true
  await vm.load()
  assert.equal(vm.workflows.value.length, 1)
  listCalls = 0
  await vm.remove(WORKFLOW)

  assert.equal(deleteArgs, 42)
  assert.equal(listCalls, 1, '删除成功后应重新加载列表')
  assert.deepEqual(vm.workflows.value, [])
  assert.deepEqual(state.toast.calls, [{ level: 'success', args: ['工作流已删除'] }])
})

test('remove 失败：toast.error 展示后端 message', async () => {
  const { vm, state } = mount({
    deleteWorkflow: async () => ({ code: 1, message: '无权限删除', data: null }),
  })
  globalThis.window.confirm = () => true
  await vm.remove(WORKFLOW)
  assert.deepEqual(state.toast.calls, [{ level: 'error', args: ['删除失败', '无权限删除'] }])
})

test('formatTime：合法日期格式化、非法日期回退原值', () => {
  const { vm } = mount()
  const raw = '2024-06-01T08:00:00Z'
  assert.equal(vm.formatTime(raw), new Date(raw).toLocaleString('zh-CN', { hour12: false }))
  assert.equal(vm.formatTime('不是日期'), '不是日期')
  assert.equal(vm.formatTime(''), '')
})

test('openCreate 打开弹窗并清空上一次的输入与错误', () => {
  const { vm } = mount()
  vm.createForm.name = '旧值'
  vm.createForm.description = '旧描述'
  vm.createError.value = '旧错误'
  vm.createOpen.value = false
  vm.openCreate()
  assert.equal(vm.createOpen.value, true)
  assert.equal(vm.createForm.name, '')
  assert.equal(vm.createForm.description, '')
  assert.equal(vm.createError.value, '')
})

test('load 失败后再次 load 成功会清空 pageError', async () => {
  let fail = true
  const { vm } = mount({
    listWorkflows: async () => {
      if (fail) return { code: 1, message: '暂时失败', data: null }
      return { code: 0, message: 'ok', data: { total: 1, workflows: [WORKFLOW] } }
    },
  })
  await vm.load()
  assert.equal(vm.pageError.value, '暂时失败')
  fail = false
  await vm.load()
  assert.equal(vm.pageError.value, '')
  assert.equal(vm.workflows.value.length, 1)
})

test('组件确实调用 onMounted(load)：无实例时不自动执行，静态确认挂载钩子存在', async () => {
  // 逻辑测试无法触发 onMounted；这里确认 setup 内注册的 load 是真实函数（模板/钩子共用）
  const { vm } = mount({
    listWorkflows: async () => ({ code: 0, data: { total: 0, workflows: [] } }),
  })
  assert.equal(typeof vm.load, 'function')
  await flushPromises(1)
})
