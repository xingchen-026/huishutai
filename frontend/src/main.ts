import './assets/main.css'

import { createApp } from 'vue'
// @ts-ignore Vue SFC typing may not be configured in this project.
import App from './App.vue'
import router from './router'

// 创建应用实例，挂载路由后渲染到 #app 节点
createApp(App).use(router).mount('#app')
