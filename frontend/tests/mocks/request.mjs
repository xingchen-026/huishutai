/** mock `./request`（axios 实例）：记录调用并把结果委托给测试状态。 */
const state = () => globalThis.__wfTestState

function record(method, args) {
  const call = {
    method,
    url: args[0],
    second: args[1],
    third: args[2],
  }
  state().request.calls.push(call)
  const handler = state().request.handler
  if (handler) return handler(call)
  return Promise.resolve({ code: 0, message: 'ok', data: {} })
}

const request = {
  get: (...args) => record('get', args),
  post: (...args) => record('post', args),
  patch: (...args) => record('patch', args),
  put: (...args) => record('put', args),
  delete: (...args) => record('delete', args),
}

export default request
