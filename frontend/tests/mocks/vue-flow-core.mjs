/** mock `@vue-flow/core`：组件逻辑测试不渲染画布，只保留被测源码用到的 API。 */
const state = () => globalThis.__wfTestState

export const ConnectionMode = { Strict: 'strict', Loose: 'loose' }
export const Position = { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' }

export const Handle = { name: 'Handle', setup: () => () => null }
export const VueFlow = { name: 'VueFlow', setup: () => () => null }

export function useVueFlow() {
  return {
    addEdges(edges) {
      state().vueFlow.addEdgesCalls.push(edges)
    },
  }
}
