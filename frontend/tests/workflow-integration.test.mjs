/**
 * 工作流前端集成契约测试：
 * - 真实加载 router/index.ts（mock vue-router 工厂），断言工作流路由、导航守卫、页面标题；
 * - 真实加载 AppLayout / HomeView / App / WorkflowNode 的 setup，断言导航入口与图标覆盖；
 * - 真实加载 AppIcon.vue（使用真实 @lucide/vue），断言图标映射与缺失图标；
 * - 静态读取 main.ts / package.json / vite.config.ts / 后端 api/urls.py 校验集成契约。
 */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { after, before, test } from 'node:test'
import { Circle, Workflow } from '@lucide/vue'
import { createHarness, frontendRoot, repoRoot, srcDir } from './helpers/harness.mjs'
import {
  callSetup,
  installDomStubs,
  resetTestState,
  silenceVueSetupWarnings,
} from './helpers/test-utils.mjs'

let appHarness
let iconHarness
let router
let AppLayout
let HomeView
let App
let WorkflowNode
let AppIcon
let restoreWarnings

before(async () => {
  installDomStubs()
  restoreWarnings = silenceVueSetupWarnings()
  resetTestState()

  appHarness = await createHarness({
    mocks: [
      { find: 'vue-router', file: 'vue-router-full.mjs' },
      { find: '@vueuse/core', file: 'vueuse-core.mjs' },
      { find: '@vue-flow/core', file: 'vue-flow-core.mjs' },
      { find: '@vue-flow/background', file: 'vue-flow-background.mjs' },
      { find: '@vue-flow/controls', file: 'vue-flow-controls.mjs' },
      { find: '@vue-flow/minimap', file: 'vue-flow-minimap.mjs' },
      { find: '@/stores/auth', file: 'store-auth.mjs' },
      { find: '@/stores/theme', file: 'store-theme.mjs' },
      { find: '@/stores/toast', file: 'store-toast.mjs' },
      { find: '@/api/workflow', file: 'api-workflow.mjs' },
      { find: '@/api/user', file: 'api-user.mjs' },
      { find: '@/components/ui/AppIcon.vue', file: 'app-icon.mjs' },
      { find: '@/components/workflow/WorkflowNode.vue', file: 'component-stub.mjs' },
    ],
  })
  router = (await appHarness.load('/src/router/index.ts')).default
  AppLayout = (await appHarness.load('/src/components/layout/AppLayout.vue')).default
  HomeView = (await appHarness.load('/src/views/HomeView.vue')).default
  App = (await appHarness.load('/src/App.vue')).default
  WorkflowNode = (await appHarness.load('/src/components/workflow/WorkflowNode.vue')).default

  // 真实 @lucide/vue（SSR 外部化后由 Node 原生 import 加载）
  iconHarness = await createHarness()
  AppIcon = (await iconHarness.load('/src/components/ui/AppIcon.vue')).default
})

after(async () => {
  restoreWarnings()
  await appHarness.close()
  await iconHarness.close()
})

function childRoutes() {
  const layout = router.options.routes.find((route) => route.path === '/')
  return layout.children
}

function useLoggedIn(loggedIn) {
  globalThis.localStorage.getItem = (key) => (loggedIn && key === 'access_token' ? 'token' : null)
}

/* ---------------- 路由 ---------------- */

test('router：/workflows 与 /workflows/:id 路由指向真实视图组件', async () => {
  const children = childRoutes()

  const listRoute = children.find((route) => route.name === 'workflows')
  assert.ok(listRoute, '缺少 name=workflows 的路由')
  assert.equal(listRoute.path, 'workflows')
  assert.equal(listRoute.meta.title, '工作流')
  assert.equal(typeof listRoute.component, 'function')
  const listModule = await listRoute.component()
  assert.equal(listModule.default.__name, 'WorkflowListView')

  const editorRoute = children.find((route) => route.name === 'workflow-editor')
  assert.ok(editorRoute, '缺少 name=workflow-editor 的路由')
  assert.equal(editorRoute.path, 'workflows/:id')
  assert.equal(editorRoute.meta.title, '工作流编辑器')
  assert.equal(typeof editorRoute.component, 'function')
  const editorModule = await editorRoute.component()
  assert.equal(editorModule.default.__name, 'WorkflowEditorView')
})

test('router：/ 布局路由受登录保护，首页重定向 /home，登录/注册为 guestOnly', async () => {
  const layout = router.options.routes.find((route) => route.path === '/')
  assert.ok(layout)
  assert.equal(layout.meta.requiresAuth, true)
  assert.equal(typeof layout.component, 'function')
  const layoutModule = await layout.component()
  assert.equal(layoutModule.default.__name, 'AppLayout')

  const indexRoute = layout.children.find((route) => route.path === '')
  assert.deepEqual(indexRoute.redirect, '/home')

  const login = router.options.routes.find((route) => route.path === '/login')
  const register = router.options.routes.find((route) => route.path === '/register')
  assert.equal(login.meta.guestOnly, true)
  assert.equal(login.meta.title, '登录')
  assert.equal(register.meta.guestOnly, true)
  assert.equal(register.meta.title, '注册')

  const fallback = router.options.routes.find((route) => route.path === '/:pathMatch(.*)*')
  assert.deepEqual(fallback.redirect, '/home')
})

test('router 守卫：未登录访问受保护页跳登录并带 redirect', () => {
  useLoggedIn(false)
  const guard = router.beforeGuards[0]
  assert.deepEqual(guard({ meta: { requiresAuth: true }, fullPath: '/workflows/7' }), {
    name: 'login',
    query: { redirect: '/workflows/7' },
  })
  assert.equal(guard({ meta: { requiresAuth: false }, fullPath: '/home' }), undefined)
})

test('router 守卫：已登录访问 guestOnly 页跳首页，受保护页放行', () => {
  useLoggedIn(true)
  const guard = router.beforeGuards[0]
  assert.deepEqual(guard({ meta: { guestOnly: true }, fullPath: '/login' }), { name: 'home' })
  assert.equal(guard({ meta: { requiresAuth: true }, fullPath: '/workflows' }), undefined)
})

test('router.afterEach：document.title 使用「页面标题 · 汇书台」', () => {
  const afterEach = router.afterHooks[0]
  afterEach({ meta: { title: '工作流' } })
  assert.equal(globalThis.document.title, '工作流 · 汇书台')
  afterEach({ meta: {} })
  assert.equal(globalThis.document.title, '汇书台')
  afterEach({ meta: { title: 123 } })
  assert.equal(globalThis.document.title, '汇书台')
})

/* ---------------- 导航入口 ---------------- */

test('AppLayout：侧边栏「工作区」包含工作流导航项，且 id 与路由 name 对齐', () => {
  resetTestState()
  const vm = callSetup(AppLayout, {})
  const groups = vm.NAV_GROUPS
  assert.deepEqual(
    groups.map((group) => group.label),
    ['工作区', '服务'],
  )
  const items = groups.flatMap((group) => group.items)
  const workflowItem = items.find((item) => item.id === 'workflows')
  assert.deepEqual(workflowItem, {
    id: 'workflows',
    label: '工作流',
    icon: 'workflow',
    to: '/workflows',
  })

  const routes = childRoutes().filter((route) => route.name && route.path)
  for (const item of items) {
    const route = routes.find((entry) => entry.name === item.id)
    assert.ok(route, `导航项 ${item.id} 没有对应路由`)
    assert.equal('/' + route.path, item.to, `导航项 ${item.id} 的 to 与路由 path 不一致`)
  }
})

test('HomeView：应用入口「工作流」可点击并指向 /workflows', () => {
  resetTestState()
  const vm = callSetup(HomeView, {})
  const workflowApp = vm.apps.find((app) => app.title === '工作流')
  assert.deepEqual(workflowApp, {
    title: '工作流',
    desc: '无限画布编排 AI 与 HTTP 能力',
    icon: 'workflow',
    to: '/workflows',
  })
  const children = childRoutes()
  for (const app of vm.apps.filter((entry) => entry.to)) {
    assert.ok(
      children.some((route) => '/' + route.path === app.to),
      `应用入口 ${app.title} 的路由不存在：${app.to}`,
    )
  }
})

/* ---------------- 图标 ---------------- */

function mountIcon(name) {
  return callSetup(AppIcon, { name })
}

test('AppIcon：workflow/play/sparkles/globe/branch 等图标键可用，未知键回退 Circle', () => {
  const vm = mountIcon('workflow')
  assert.equal(vm.icon.value, Workflow)
  for (const name of ['play', 'sparkles', 'globe', 'branch', 'trash', 'arrow-right']) {
    assert.ok(name in vm.ICONS, `图标名 ${name} 未注册`)
  }
  assert.equal(mountIcon('not-exist-icon').icon.value, Circle)
})

function collectUsedIconNames() {
  const names = new Set()
  const vueFiles = []
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(full)
      else if (entry.name.endsWith('.vue')) vueFiles.push(full)
    }
  }
  walk(srcDir)

  for (const file of vueFiles) {
    const source = fs.readFileSync(file, 'utf8')
    // 只匹配静态 name="x"；动态 :name="expr" 由下一个循环解析其中的字符串字面量
    for (const match of source.matchAll(/<AppIcon\b[^>]*?\sname="([^"]+)"/g)) {
      names.add(match[1])
    }
    for (const match of source.matchAll(/<AppIcon\b[^>]*?:name="([^"]+)"/g)) {
      for (const literal of match[1].matchAll(/'([a-z][a-z0-9-]*)'|"([a-z][a-z0-9-]*)"/g)) {
        names.add(literal[1] || literal[2])
      }
    }
  }

  // 动态数据源里的图标名（真实执行各组件的 setup 读取）
  resetTestState()
  const layoutVm = callSetup(AppLayout, {})
  for (const item of layoutVm.NAV_GROUPS.flatMap((group) => group.items)) names.add(item.icon)
  const homeVm = callSetup(HomeView, {})
  for (const app of homeVm.apps) names.add(app.icon)
  const appVm = callSetup(App, {})
  for (const icon of Object.values(appVm.TOAST_ICONS)) names.add(icon)
  const nodeVm = callSetup(WorkflowNode, {
    id: 'n1',
    data: { name: '开始', nodeType: 'start', config: {}, version: 1 },
  })
  for (const icon of Object.values(nodeVm.ICONS)) names.add(icon)
  names.add(nodeVm.icon.value)

  return names
}

test('AppIcon：源码引用的图标名全部注册', () => {
  const used = collectUsedIconNames()
  const registered = mountIcon('workflow').ICONS
  const missing = [...used].filter((name) => !(name in registered)).sort()

  assert.deepEqual(missing, [], '所有被引用的图标名都应注册')
  assert.notEqual(mountIcon('download').icon.value, Circle)
})

/* ---------------- main.ts / 依赖 / 代理 / 后端前缀 ---------------- */

test('main.ts：先引入 4 套 vue-flow 样式，再引入 main.css 与创建应用', () => {
  const source = fs.readFileSync(path.join(srcDir, 'main.ts'), 'utf8')
  const expected = [
    "import '@vue-flow/core/dist/style.css'",
    "import '@vue-flow/core/dist/theme-default.css'",
    "import '@vue-flow/controls/dist/style.css'",
    "import '@vue-flow/minimap/dist/style.css'",
    "import './assets/main.css'",
  ]
  let lastIndex = -1
  for (const line of expected) {
    const index = source.indexOf(line)
    assert.ok(index > lastIndex, `缺少或顺序错误：${line}`)
    lastIndex = index
  }
  assert.match(source, /import { createApp } from 'vue'/)
  assert.match(source, /import { createPinia } from 'pinia'/)
  assert.match(source, /import router from '\.\/router'/)
  assert.match(source, /app\.mount\('#app'\)/)
})

test('package.json：包含工作流前端依赖，未引入 vitest/jsdom/@vue/test-utils', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(frontendRoot, 'package.json'), 'utf8'))
  const expectedDeps = [
    '@lucide/vue',
    '@vue-flow/background',
    '@vue-flow/controls',
    '@vue-flow/core',
    '@vue-flow/minimap',
    '@vueuse/core',
    'axios',
    'pinia',
    'vue',
    'vue-router',
  ]
  for (const dep of expectedDeps) assert.ok(pkg.dependencies[dep], `缺少依赖 ${dep}`)
  assert.ok(pkg.devDependencies.vite)
  assert.ok(pkg.devDependencies['@vitejs/plugin-vue'])
  assert.ok(pkg.devDependencies['vue-tsc'])
  for (const script of ['dev', 'build', 'build-only', 'type-check', 'lint:check', 'format:check']) {
    assert.ok(pkg.scripts[script], `缺少脚本 ${script}`)
  }
  for (const banned of ['vitest', 'jsdom', '@vue/test-utils', 'happy-dom']) {
    assert.equal(pkg.dependencies[banned], undefined, `测试不应新增依赖 ${banned}`)
    assert.equal(pkg.devDependencies[banned], undefined, `测试不应新增依赖 ${banned}`)
  }
})

test('vite.config.ts：@ 别名与 /api 代理（去掉 /api 前缀）', () => {
  const source = fs.readFileSync(path.join(frontendRoot, 'vite.config.ts'), 'utf8')
  assert.match(source, /'@': fileURLToPath\(new URL\('\.\/src', import\.meta\.url\)\)/)
  assert.match(source, /target: 'http:\/\/127\.0\.0\.1:8000'/)
  assert.ok(source.includes("rewrite: (path) => path.replace(/^\\/api/, '')"))
})

test('后端在 /workflow/ 前缀下注册 Workflow.urls（与前端 /workflow/* 请求对齐）', () => {
  const source = fs.readFileSync(path.join(repoRoot, 'backend/api/urls.py'), 'utf8')
  assert.match(source, /path\("workflow\/",\s*include\("Workflow\.urls"\)\)/)
})
