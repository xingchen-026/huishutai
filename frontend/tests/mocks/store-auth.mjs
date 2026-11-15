/** mock auth store：只暴露被测组件读取的字段。 */
const state = () => globalThis.__wfTestState

export function useAuthStore() {
  return {
    get userId() {
      return state().auth.userId
    },
    get username() {
      return state().auth.username
    },
    avatarText: 'T',
    isLoggedIn: true,
    clear() {
      state().auth.cleared = true
    },
  }
}
