/**
 * mock 'vue'：plugin-vue 的 SSR 开发构建会在 setup 外层包一层
 * useSSRContext()（收集模块用于 SSR），而逻辑测试直接调用 setup() 时没有组件实例，
 * 真实 useSSRContext 会因 inject() 无实例而返回 undefined，导致 ssrContext.modules 抛错。
 * 这里仅把 useSSRContext 替换为返回空对象，其它 API 全部透传 @vue/runtime-core。
 */
// 这里必须直接引 runtime-core：import 'vue' 会递归回本 mock 自身（循环依赖）。
// eslint-disable-next-line vue/prefer-import-from-vue
export * from '@vue/runtime-core'

export function useSSRContext() {
  return {}
}
