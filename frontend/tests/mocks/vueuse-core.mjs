/**
 * mock `@vueuse/core`：只实现被测组件用到的组合式函数。
 * 不依赖浏览器：返回的 ref 用 getter/setter 手写，避免额外运行时代价。
 */
const state = () => globalThis.__wfTestState

function makeRef(initialValue) {
  let current = initialValue
  return {
    get value() {
      return current
    },
    set value(next) {
      current = next
    },
  }
}

export function useIntervalFn(callback, interval, options = {}) {
  return {
    resume() {
      state().interval.resumeCalls += 1
    },
    pause() {},
    isActive: makeRef(false),
    callback,
    interval,
    options,
  }
}

export function useEventListener() {}
export function onClickOutside() {}

export function useStorage(key, initialValue) {
  return makeRef(initialValue)
}

export function useToggle(initialValue = false) {
  const value = makeRef(Boolean(initialValue))
  const toggle = (next) => {
    value.value = typeof next === 'boolean' ? next : !value.value
    return value.value
  }
  return [value, toggle]
}
