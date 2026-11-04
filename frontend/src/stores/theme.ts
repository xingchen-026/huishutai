import { defineStore } from 'pinia'
import { useDark } from '@vueuse/core'

/**
 * 双主题：
 * - 通过 <html data-theme="light|dark"> 驱动 tokens.css 两套变量；
 * - 持久化 key 与 index.html 防闪烁脚本一致；
 * - 默认跟随系统，手动切换后以手动值为准。
 */
export const useThemeStore = defineStore('theme', () => {
  const isDark = useDark({
    selector: 'html',
    attribute: 'data-theme',
    valueDark: 'dark',
    valueLight: 'light',
    storageKey: 'huishutai-theme',
    initialValue: 'auto',
    disableTransition: true,
  })

  function toggleTheme() {
    isDark.value = !isDark.value
  }

  return { isDark, toggleTheme }
})
