/** mock `vue-router` 组合式 API：route/router 由测试状态注入。 */
const state = () => globalThis.__wfTestState

export function useRoute() {
  return state().route
}

export function useRouter() {
  return state().router
}
