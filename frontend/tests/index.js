/**
 * Node 24 的 `node --test tests/` 会把目录参数解析为入口文件（而不是递归目录），
 * 因此这里聚合全部测试文件，保证验收命令 `node --test tests/` 可用。
 * 各测试文件内部仍复用同一套 mock/断言；独立运行单个文件不受影响。
 */
import './workflow-api.test.mjs'
import './workflow-node.test.mjs'
import './workflow-list.test.mjs'
import './workflow-editor.test.mjs'
import './workflow-integration.test.mjs'
