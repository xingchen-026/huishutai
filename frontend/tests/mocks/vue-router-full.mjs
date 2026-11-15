/** 供 router/index.ts 集成测试使用的 vue-router mock：捕获 routes 与导航守卫。 */
const state = () => globalThis.__wfTestState

export function createWebHistory() {
  return { mode: 'web-history' }
}

export function createRouter(options) {
  const router = {
    options,
    beforeGuards: [],
    afterHooks: [],
    pushes: [],
    beforeEach(fn) {
      this.beforeGuards.push(fn)
    },
    afterEach(fn) {
      this.afterHooks.push(fn)
    },
    push(to) {
      this.pushes.push(to)
      return Promise.resolve()
    },
  }
  state().router = router
  return router
}

export function useRoute() {
  return state().route
}

export function useRouter() {
  return state().router
}
