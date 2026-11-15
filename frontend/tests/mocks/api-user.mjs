/** mock `@/api/user`：只实现 AppLayout 用到的 logout。 */
export function logout() {
  const handler = globalThis.__wfTestState.api.logout
  return typeof handler === 'function'
    ? handler()
    : Promise.resolve({ code: 0, message: 'ok', data: {} })
}
