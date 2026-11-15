/**
 * WorkflowNode.vue 组件逻辑测试：SSR 加载真实 .vue 源码（模板编译为 SSR 渲染函数，
 * 不执行渲染），直接调用 setup() 断言模板绑定的 computed 与函数。
 */
import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createHarness } from './helpers/harness.mjs'
import { callSetup, resetTestState, silenceVueSetupWarnings } from './helpers/test-utils.mjs'

let harness
let WorkflowNode
let restoreWarnings

before(async () => {
  resetTestState()
  restoreWarnings = silenceVueSetupWarnings()
  harness = await createHarness({
    mocks: [
      { find: '@vue-flow/core', file: 'vue-flow-core.mjs' },
      { find: '@/components/ui/AppIcon.vue', file: 'app-icon.mjs' },
    ],
  })
  const module = await harness.load('/src/components/workflow/WorkflowNode.vue')
  WorkflowNode = module.default
})

after(async () => {
  restoreWarnings()
  await harness.close()
})

function mount(data, props = {}) {
  return callSetup(WorkflowNode, { id: 'node-1', data, ...props })
}

function nodeData(overrides = {}) {
  return {
    name: '开始',
    nodeType: 'start',
    config: {},
    version: 1,
    ...overrides,
  }
}

test('默认 props 下 icon 映射：start→play、llm→sparkles、http→globe、condition→branch、未知→workflow', () => {
  const cases = [
    ['start', 'play'],
    ['llm', 'sparkles'],
    ['http', 'globe'],
    ['condition', 'branch'],
    ['agent', 'workflow'],
    ['', 'workflow'],
    [undefined, 'workflow'],
  ]
  for (const [nodeType, expected] of cases) {
    const vm = mount(nodeData({ nodeType }))
    assert.equal(vm.icon.value, expected, `nodeType=${String(nodeType)}`)
  }
})

test('ICONS 映射表与源码一致（4 个内置节点类型）', () => {
  const vm = mount(nodeData())
  assert.deepEqual(vm.ICONS, {
    start: 'play',
    llm: 'sparkles',
    http: 'globe',
    condition: 'branch',
  })
})

test('meta 缺省时 inputs/outputs 回退为 in/out 单端口', () => {
  const vm = mount(nodeData({ meta: undefined }))
  assert.deepEqual(vm.inputs.value, [{ id: 'in', label: '输入' }])
  assert.deepEqual(vm.outputs.value, [{ id: 'out', label: '输出' }])

  const noPorts = mount(nodeData({ meta: { name: '开始', category: '触发器' } }))
  assert.deepEqual(noPorts.inputs.value, [{ id: 'in', label: '输入' }])
  assert.deepEqual(noPorts.outputs.value, [{ id: 'out', label: '输出' }])
})

test('meta 存在时使用自定义端口（condition 的 true/false 输出）', () => {
  const meta = {
    name: '条件分支',
    category: '逻辑',
    inputs: [{ id: 'in', label: '输入' }],
    outputs: [
      { id: 'true', label: '是' },
      { id: 'false', label: '否' },
    ],
  }
  const vm = mount(nodeData({ nodeType: 'condition', meta }))
  assert.deepEqual(vm.inputs.value, [{ id: 'in', label: '输入' }])
  assert.deepEqual(vm.outputs.value, [
    { id: 'true', label: '是' },
    { id: 'false', label: '否' },
  ])
})

test('meta 的 inputs/outputs 为空数组时尊重空数组而非回退', () => {
  const vm = mount(
    nodeData({ meta: { name: '开始', category: '触发器', inputs: [], outputs: [] } }),
  )
  assert.deepEqual(vm.inputs.value, [])
  assert.deepEqual(vm.outputs.value, [])
})

test('portTop 按端口序号均匀分布百分比', () => {
  const vm = mount(nodeData())
  const cases = [
    [0, 1, '50%'],
    [0, 2, '33%'],
    [1, 2, '67%'],
    [0, 3, '25%'],
    [1, 3, '50%'],
    [2, 3, '75%'],
    [0, 4, '20%'],
    [3, 4, '80%'],
    [0, 0, '100%'],
  ]
  for (const [index, total, expected] of cases) {
    assert.equal(vm.portTop(index, total), expected, `portTop(${index}, ${total})`)
  }
})

test('selected 透传：setup 接收的 props 不被改写', () => {
  const data = nodeData()
  mount(data, { selected: true })
  assert.equal(data.name, '开始')
})
