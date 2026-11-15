/** 通用组件桩：用于替代被测视图里重量级子组件（WorkflowNode / VueFlow 相关组件等）。 */
export default {
  name: 'ComponentStub',
  setup: () => () => null,
}
