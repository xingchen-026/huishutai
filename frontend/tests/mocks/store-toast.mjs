/** mock toast store：记录所有提示调用，避免依赖 Pinia / window.setTimeout。 */
const state = () => globalThis.__wfTestState

function record(level) {
  return (...args) => {
    state().toast.calls.push({ level, args })
  }
}

export function useToastStore() {
  return {
    items: [],
    push: record('push'),
    success: record('success'),
    warning: record('warning'),
    error: record('error'),
    info: record('info'),
  }
}
