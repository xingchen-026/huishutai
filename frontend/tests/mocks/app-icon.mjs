/** mock AppIcon 组件：逻辑测试不渲染，只需要一个可被模板引用的组件对象。 */
export default {
  name: 'AppIcon',
  props: { name: { type: String, default: '' } },
  setup: () => () => null,
}
