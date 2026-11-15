import path from 'node:path'
import { fileURLToPath } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { createServer } from 'vite'

const helpersDir = path.dirname(fileURLToPath(import.meta.url))

/** frontend/tests */
export const testsDir = path.dirname(helpersDir)
/** frontend */
export const frontendRoot = path.dirname(testsDir)
/** 仓库根目录（frontend 的父目录） */
export const repoRoot = path.dirname(frontendRoot)
export const srcDir = path.join(frontendRoot, 'src')
export const mocksDir = path.join(testsDir, 'mocks')

/**
 * 用项目现成的 vite + @vitejs/plugin-vue 程序化创建一个 SSR 加载器。
 * 不加载 vite.config.ts（其中的 vueDevTools 插件在纯 Node 环境不可用）。
 *
 * 模块 mock 通过 resolve.alias 实现：mocks 里的条目必须排在 '@' 别名之前，
 * 否则 Vite 内置 alias 会先把 '@/xxx' 改写成真实文件路径。
 * 注意：SSR 会把 node_modules 依赖外部化（交给 Node 原生 import），
 * 所以被测组件用到的第三方包（vue、vue-router、@vue-flow/*、@vueuse/core）
 * 必须显式 mock，否则会绕过测试替身。
 */
export async function createHarness(options = {}) {
  const { mocks = [] } = options
  const mockAliases = mocks.map((entry) => ({
    find: entry.find,
    replacement: path.join(mocksDir, entry.file),
  }))
  // .vue 的 SSR 开发构建在 setup 外层包了 useSSRContext()，逻辑测试没有组件实例，
  // 统一用 mock 的 vue 覆盖该 API（见 tests/mocks/vue.mjs）。
  const alias = [
    { find: 'vue', replacement: path.join(mocksDir, 'vue.mjs') },
    ...mockAliases,
    { find: '@', replacement: srcDir },
  ]

  const server = await createServer({
    configFile: false,
    root: frontendRoot,
    plugins: [vue()],
    resolve: { alias },
    // ws: false 关闭 Vite 8 默认监听的 HMR WebSocket（否则并行测试文件会抢 24678 端口）
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    appType: 'custom',
    logLevel: 'error',
    optimizeDeps: { noDiscovery: true },
  })

  return {
    server,
    /** 加载 src 下的 TS / Vue 源码（真实执行，组件模板编译为 SSR 渲染函数） */
    load: (url) => server.ssrLoadModule(url),
    close: () => server.close(),
  }
}
