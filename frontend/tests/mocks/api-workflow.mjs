/**
 * mock `@/api/workflow`：把调用委托给测试状态里的 `api` 处理器，
 * 测试可按需配置返回成功 / 业务错误 / 网络异常。
 */
const api = () => globalThis.__wfTestState.api

function call(name) {
  return (...args) => {
    const handler = api()[name]
    if (typeof handler !== 'function') {
      throw new Error(`测试未配置 mock api：${name}`)
    }
    return handler(...args)
  }
}

export const listWorkflows = call('listWorkflows')
export const createWorkflow = call('createWorkflow')
export const getWorkflow = call('getWorkflow')
export const updateWorkflow = call('updateWorkflow')
export const deleteWorkflow = call('deleteWorkflow')
export const listWorkflowEvents = call('listWorkflowEvents')
export const addWorkflowNode = call('addWorkflowNode')
export const updateWorkflowNode = call('updateWorkflowNode')
export const deleteWorkflowNode = call('deleteWorkflowNode')
export const addWorkflowRelation = call('addWorkflowRelation')
export const deleteWorkflowRelation = call('deleteWorkflowRelation')
export const importWorkflow = call('importWorkflow')
export const exportWorkflow = call('exportWorkflow')
export const runWorkflow = call('runWorkflow')
export const listWorkflowMembers = call('listWorkflowMembers')
export const addWorkflowMember = call('addWorkflowMember')
export const removeWorkflowMember = call('removeWorkflowMember')
export const listNodeTypes = call('listNodeTypes')
export const getNodeTypeMeta = call('getNodeTypeMeta')
