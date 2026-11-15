/** mock theme store：isDark 固定为浅色，避免真实 useDark 依赖 DOM。 */
export function useThemeStore() {
  return {
    isDark: false,
    toggleTheme() {},
  }
}
