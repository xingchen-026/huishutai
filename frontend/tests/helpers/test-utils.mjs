/**
 * 组件逻辑测试工具：不渲染 DOM，直接调用 `<script setup>` 编译产物里的 setup()，
 * 断言其返回的模板绑定（ref / computed / 函数）。适用于无 jsdom 的环境。
 */

/** 每个测试文件在加载被测模块前重置的全局 mock 状态。 */
export function resetTestState(partial = {}) {
  const state = {
    /** vue-router 的 useRoute() 返回值 */
    route: { params: {}, meta: {}, name: '' },
    /** vue-router 的 useRouter() 返回值 */
    router: { pushes: [] },
    /** toast store 记录：{ level, args } */
    toast: { calls: [] },
    /** auth store */
    auth: { userId: 1, username: 'tester', cleared: false },
    /** theme store */
    theme: { isDark: false },
    /** vue-flow 的 useVueFlow().addEdges 调用记录 */
    vueFlow: { addEdgesCalls: [] },
    /** @vueuse/core 的 useIntervalFn().resume 调用记录 */
    interval: { resumeCalls: 0 },
    /** mock 的 axios request 实例调用记录与返回值处理器 */
    request: { calls: [], handler: null },
    /** mock 的 workflow api：{ listWorkflows: fn(...) } */
    api: {},
    ...partial,
  }

  state.router.push = (to) => {
    state.router.pushes.push(to)
    return Promise.resolve()
  }

  globalThis.__wfTestState = state
  return state
}

export function getTestState() {
  return globalThis.__wfTestState
}

/** 为 SSR 中的 Vue 运行时与组件代码提供最小 document/window 桩（不渲染 DOM）。 */
export function installDomStubs() {
  const noop = () => {}
  const classList = { add: noop, remove: noop, toggle: noop, contains: () => false }
  const element = () => ({
    style: {},
    classList,
    nodeType: 1,
    tagName: 'DIV',
    setAttribute: noop,
    removeAttribute: noop,
    appendChild: noop,
    insertBefore: noop,
    removeChild: noop,
    addEventListener: noop,
    removeEventListener: noop,
    click: noop,
  })

  globalThis.document = {
    hidden: false,
    title: '',
    body: { ...element(), classList },
    documentElement: element(),
    head: element(),
    createElement: element,
    createTextNode: (text) => ({ nodeType: 3, textContent: text }),
    createComment: () => ({ nodeType: 8 }),
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: noop,
    removeEventListener: noop,
  }
  globalThis.window = {
    confirm: () => true,
    location: { pathname: '/', assign: noop },
    setTimeout,
    clearTimeout,
  }
  globalThis.localStorage = {
    getItem: () => null,
    setItem: noop,
    removeItem: noop,
    clear: noop,
  }
}

/** 调用 script setup 编译后的 setup()，返回模板可用的绑定对象。 */
export function callSetup(component, props = {}, extraContext = {}) {
  if (typeof component.setup !== 'function') {
    throw new Error('组件没有 setup，无法做逻辑测试')
  }
  return component.setup(props, {
    expose: () => {},
    emit: () => {},
    attrs: {},
    slots: {},
    ...extraContext,
  })
}

/** 让出一轮事件循环，用于等待组件内部的异步加载。 */
export async function flushPromises(rounds = 4) {
  for (let index = 0; index < rounds; index += 1) {
    await new Promise((resolve) => setTimeout(resolve, 0))
  }
}

/** 轮询等待条件成立（有超时保护，避免挂死）。 */
export async function waitFor(predicate, options = {}) {
  const { timeout = 3000, interval = 10 } = options
  const startedAt = Date.now()
  for (;;) {
    const value = predicate()
    if (value) return value
    if (Date.now() - startedAt > timeout) {
      throw new Error('waitFor 超时')
    }
    await new Promise((resolve) => setTimeout(resolve, interval))
  }
}

/**
 * 组件在无组件实例时调用 onMounted/onBeforeUnmount 会触发 Vue 开发警告；
 * 逻辑测试不渲染组件，这类警告是预期的，过滤掉其余警告仍打印。
 */
export function silenceVueSetupWarnings() {
  const originalWarn = console.warn
  const ignored = [
    'onMounted is called when there is no active component instance',
    'onBeforeUnmount is called when there is no active component instance',
    'onUnmounted is called when there is no active component instance',
  ]
  console.warn = (...args) => {
    const message = String(args[0] ?? '')
    if (ignored.some((item) => message.includes(item))) return
    originalWarn(...args)
  }
  return () => {
    console.warn = originalWarn
  }
}
