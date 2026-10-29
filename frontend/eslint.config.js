import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import tsParser from '@typescript-eslint/parser'
import eslintConfigPrettier from 'eslint-config-prettier'
import globals from 'globals'

export default [
  {
    ignores: ['dist/**', 'dist-ssr/**', 'coverage/**'],
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.{js,mjs,cjs,ts,mts,tsx,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node },
    },
    rules: {
      // 类型/全局由 vue-tsc 与 Vue 编译器处理，避免误报编译器宏（defineProps 等）
      'no-undef': 'off',
      'no-unused-vars': 'warn',
    },
  },
  {
    files: ['**/*.{ts,mts,tsx}'],
    languageOptions: {
      parser: tsParser,
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tsParser,
        extraFileExtensions: ['.vue'],
      },
    },
  },
  // 关闭与 Prettier 冲突的格式类规则
  eslintConfigPrettier,
  {
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
]