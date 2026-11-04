/* ==========================================================================
   汇书台 · 原型外壳（Shell）
   职责：
   1. 统一渲染侧边栏 / 顶栏 / 面包屑 / 用户菜单；
   2. 提供可扩展的导航注册表、命令面板、页面动作溢出机制；
   3. 提供弹层、抽屉、Toast、Tabs、复制、下拉等通用交互；
   4. 暴露 window.AppShell / window.AppUI / window.AppMock 三个扩展入口。

   扩展方式（新页面无需改本文件）：
   - 新增导航：AppShell.addNavItem(groupId, item) / addNavGroup(group)
   - 新增命令：AppShell.addCommand({id, title, group, icon, hint, run})
   - 新增页面动作：AppShell.addPageAction({label, icon, variant, onClick})
   - 事件总线：AppShell.on(name, fn) / AppShell.emit(name, detail)
   ========================================================================== */

;(function () {
  'use strict'

  /* ==========================================================================
     图标库（内联 SVG，离线可用）
     ========================================================================== */

  var ICONS = {
    home: '<path d="M4 11.5 12 4l8 7.5"/><path d="M6 10.5V20h12v-9.5"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/>',
    folder:
      '<path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H10l2 2.5h6.5A2.5 2.5 0 0 1 21 10v7a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17z"/>',
    upload:
      '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 16v2.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V16"/>',
    download: '<path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M5 20h14"/>',
    database:
      '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6"/><path d="M4 11.5v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
    sparkles:
      '<path d="M12 4l1.9 5.1L19 11l-5.1 1.9L12 18l-1.9-5.1L5 11l5.1-1.9z"/><path d="M18.5 16.5 19 18l1.5.5-1.5.5-.5 1.5-.5-1.5L16.5 19l1.5-.5z"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    route:
      '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="6" r="2.5"/><path d="M8.5 18H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.5"/>',
    palette:
      '<path d="M12 3a9 9 0 1 0 0 18c1.4 0 2-.9 2-1.8 0-.7-.4-1.2-.4-1.9 0-.8.7-1.3 1.6-1.3H17a4 4 0 0 0 4-4c0-5-4-9-9-9z"/><circle cx="7.5" cy="11" r="1" fill="currentColor" stroke="none"/><circle cx="10" cy="7.5" r="1" fill="currentColor" stroke="none"/><circle cx="14.5" cy="7.5" r="1" fill="currentColor" stroke="none"/><circle cx="17" cy="11" r="1" fill="currentColor" stroke="none"/>',
    sliders:
      '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h10M18 18h2"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="16" cy="18" r="2"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    users:
      '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 5.2a3.5 3.5 0 0 1 0 6.6"/><path d="M17.5 14.2A6.5 6.5 0 0 1 21.5 20"/>',
    bell: '<path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6"/><path d="M10 19a2.2 2.2 0 0 0 4 0"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-3.6-3.6"/>',
    'chevron-down': '<path d="m6 9 6 6 6-6"/>',
    'chevron-right': '<path d="m9 6 6 6-6 6"/>',
    'chevron-left': '<path d="m15 6-6 6 6 6"/>',
    'chevron-up': '<path d="m6 15 6-6 6 6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    minus: '<path d="M5 12h14"/>',
    more: '<circle cx="6" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="18" cy="12" r="1.5" fill="currentColor" stroke="none"/>',
    refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/>',
    trash:
      '<path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12"/><path d="M10 11v6M14 11v6"/>',
    edit: '<path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z"/><path d="m14 8 2 2"/>',
    copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M15 9V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3"/>',
    check: '<path d="m5 13 4 4L19 7"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    'external-link':
      '<path d="M14 4h6v6"/><path d="M20 4 11 13"/><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>',
    link: '<path d="M10 13a4 4 0 0 0 5.7 0l3-3A4 4 0 0 0 13 4.3l-1.7 1.7"/><path d="M14 11a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 19.7l1.7-1.7"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9"/><path d="m17 6 2 2"/><path d="m14.5 8.5 2 2"/>',
    lock: '<rect x="4.5" y="10" width="15" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    'alert-circle':
      '<circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><circle cx="12" cy="16.5" r="0.9" fill="currentColor" stroke="none"/>',
    'alert-triangle':
      '<path d="M12 4.5 21 20H3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="8" r="0.9" fill="currentColor" stroke="none"/>',
    book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20"/>',
    terminal:
      '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3"/><path d="M13 15h4"/>',
    'log-out':
      '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="m9 8-4 4 4 4"/><path d="M5 12h10"/>',
    filter: '<path d="M4 5h16l-6.5 8v5l-3 2v-7z"/>',
    'arrow-right': '<path d="M4 12h15"/><path d="m13 6 6 6-6 6"/>',
    'arrow-up-right': '<path d="M7 17 17 7"/><path d="M8 7h9v9"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    shield: '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z"/><path d="m9 12 2 2 4-4"/>',
    play: '<path d="M8 5.5v13l11-6.5z"/>',
    message:
      '<path d="M21 12a8 8 0 0 1-8 8H4l3-3.5A8 8 0 1 1 21 12z"/><path d="M8.5 11h7M8.5 14.5h4"/>',
    file: '<path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13 3v6h6"/>',
    'file-text':
      '<path d="M13 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13 3v6h6"/><path d="M9 13h6M9 17h4"/>',
    image:
      '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m4 18 5-5 4 4 3-3 4 4"/>',
    film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M17 9h4M3 15h4M17 15h4"/>',
    music:
      '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    command: '<path d="M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3z"/>',
    'panel-left': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    'eye-off':
      '<path d="M3 3l18 18"/><path d="M10.6 5.8A9.8 9.8 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.7 3.6"/><path d="M6.3 7.7A17 17 0 0 0 2.5 12S6 18.5 12 18.5c1.2 0 2.3-.2 3.3-.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    hash: '<path d="M9 4 7 20M17 4l-2 16M4 9h16M3 15h16"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    server:
      '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/>',
    activity: '<path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>',
    'circle-check': '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
    'circle-x': '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    loader:
      '<path d="M12 3v4M12 17v4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M3 12h4M17 12h4M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/>',
    send: '<path d="m21 3-9 18-2.5-7.5L2 11z"/><path d="M21 3 9.5 13.5"/>',
    box: '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
    phone:
      '<path d="M5 4h3.5l1.5 4-2 1.5a12 12 0 0 0 6.5 6.5L16 14l4 1.5V19a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    zap: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    code: '<path d="m8 7-5 5 5 5M16 7l5 5-5 5"/>',
    table: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
    dot: '<circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none"/>',
    spark:
      '<path d="M12 2v4M12 18v4M2 12h4M18 12h4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M19.1 4.9l-2.8 2.8M7.7 16.3l-2.8 2.8"/>',
    rocket:
      '<path d="M12 3c3 2 5 5.5 5 9l-3 2h-4l-3-2c0-3.5 2-7 5-9z"/><path d="M9 14l-2 5 4-2M15 14l2 5-4-2"/>',
    history: '<path d="M4 12a8 8 0 1 0 2.3-5.7"/><path d="M4 4v5h5"/><path d="M12 8v4l3 2"/>',
    shield_check:
      '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z"/><path d="m9 12 2 2 4-4"/>',
    gauge:
      '<path d="M4 18a8 8 0 1 1 16 0"/><path d="m12 14 3.5-4.5"/><circle cx="12" cy="16" r="1.6"/>',
    branch:
      '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 7v10M18 10a6 6 0 0 1-6 6H8"/>',
  }

  function iconSvg(name) {
    var body = ICONS[name] || ICONS.dot
    return (
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      body +
      '</svg>'
    )
  }

  function iconHTML(name, extraClass) {
    return '<span class="icon ' + (extraClass || '') + '">' + iconSvg(name) + '</span>'
  }

  /* ==========================================================================
     导航注册表（唯一数据源：侧边栏 / 命令面板 / 面包屑都读它）
     ========================================================================== */

  var NAV_GROUPS = [
    {
      id: 'workspace',
      label: '工作区',
      items: [
        { id: 'home', label: '首页', icon: 'home', href: 'home.html' },
        { id: 'knowledge', label: '知识库', icon: 'book', href: 'knowledge.html' },
      ],
    },
    {
      id: 'service',
      label: '服务',
      items: [{ id: 'llm', label: '模型服务', icon: 'cpu', href: 'llm.html' }],
    },
  ]

  /* 命令注册表：自定义动作（页面跳转之外的全局动作放这里） */
  var COMMANDS = [
    {
      id: 'go-upload',
      group: '快捷操作',
      title: '上传文档',
      hint: '知识库',
      icon: 'upload',
      keywords: 'upload file 上传 文档 知识库',
      run: function () {
        location.href = 'knowledge.html?action=upload'
      },
    },
    {
      id: 'go-new-provider',
      group: '快捷操作',
      title: '新增供应商配置',
      hint: '模型服务',
      icon: 'plus',
      keywords: 'provider 新增 配置 供应商',
      run: function () {
        location.href = 'llm.html?action=new'
      },
    },
    {
      id: 'toggle-sidebar',
      group: '界面',
      title: '收起 / 展开侧边栏',
      hint: '界面布局',
      icon: 'panel-left',
      keywords: 'sidebar 侧边栏',
      run: function () {
        toggleSidebar()
      },
    },
    {
      id: 'open-design',
      group: '界面',
      title: '打开设计规范',
      hint: '设计规范',
      icon: 'palette',
      keywords: 'design ui 规范',
      run: function () {
        location.href = 'design-system.html'
      },
    },
    {
      id: 'go-home',
      group: '页面',
      title: '回到首页',
      hint: 'home.html',
      icon: 'home',
      keywords: 'home 首页 应用',
      run: function () {
        location.href = 'home.html'
      },
    },
    {
      id: 'go-showcase',
      group: '界面',
      title: '回到原型总览',
      hint: 'index.html',
      icon: 'grid',
      keywords: 'index 总览 原型',
      run: function () {
        location.href = 'index.html'
      },
    },
    {
      id: 'logout',
      group: '账号',
      title: '退出登录',
      hint: '演示动作',
      icon: 'log-out',
      keywords: 'logout 退出',
      run: function () {
        location.href = 'login.html?logout=1'
      },
    },
  ]

  /* ==========================================================================
     演示数据（页面可自由覆盖，仅做概念展示）
     ========================================================================== */

  var MOCK = {
    user: {
      id: 1,
      username: 'xingchen',
      displayName: '陈星',
      email: 'xingchen@example.com',
      phone: '13800138000',
      gender: 'male',
      role: '项目所有者',
      joinedAt: '2026-10-21',
    },
    providers: [
      {
        id: 1,
        name: '我的 DeepSeek',
        template: 'deepseek',
        templateName: 'DeepSeek',
        protocol: 'openai',
        baseUrl: 'https://api.deepseek.com/v1',
        key: 'sk-****7f2a',
        modelCount: 8,
        enabled: true,
        lastSync: '5 分钟前',
        status: 'ok',
      },
      {
        id: 2,
        name: '通义千问 · 百炼',
        template: 'dashscope',
        templateName: '阿里云百炼',
        protocol: 'openai',
        baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        key: 'sk-****9c13',
        modelCount: 12,
        enabled: true,
        lastSync: '今天 09:12',
        status: 'ok',
      },
      {
        id: 3,
        name: '本地 Ollama',
        template: 'ollama',
        templateName: 'Ollama',
        protocol: 'openai',
        baseUrl: 'http://127.0.0.1:11434/v1',
        key: '无需 Key',
        modelCount: 4,
        enabled: false,
        lastSync: '昨天 21:40',
        status: 'warn',
      },
    ],
    models: [
      {
        id: 12,
        modelId: 'deepseek-chat',
        displayName: 'DeepSeek Chat',
        provider: '我的 DeepSeek',
        category: 'chat',
        source: 'auto',
        enabled: true,
        params: ['temperature', 'max_tokens', 'top_p', 'stream'],
        updated: '今天 09:12',
      },
      {
        id: 13,
        modelId: 'deepseek-reasoner',
        displayName: 'DeepSeek Reasoner',
        provider: '我的 DeepSeek',
        category: 'chat',
        source: 'auto',
        enabled: true,
        params: ['temperature', 'max_tokens', 'reasoning_effort'],
        updated: '今天 09:12',
      },
      {
        id: 21,
        modelId: 'text-embedding-v4',
        displayName: 'Text Embedding v4',
        provider: '通义千问 · 百炼',
        category: 'embedding',
        source: 'auto',
        enabled: true,
        params: ['dimensions', 'encoding_format'],
        updated: '今天 09:12',
      },
      {
        id: 22,
        modelId: 'qwen-max',
        displayName: 'Qwen Max',
        provider: '通义千问 · 百炼',
        category: 'chat',
        source: 'auto',
        enabled: true,
        params: ['temperature', 'max_tokens', 'top_p'],
        updated: '今天 09:12',
      },
      {
        id: 23,
        modelId: 'bge-reranker-v2-m3',
        displayName: 'BGE Reranker v2',
        provider: '通义千问 · 百炼',
        category: 'embedding',
        source: 'manual',
        enabled: false,
        params: ['top_n', 'return_documents'],
        updated: '10-28 21:40',
      },
    ],
    files: [
      {
        id: 1,
        name: '产品需求文档-v2.pdf',
        type: 'pdf',
        size: 2483921,
        hash: '9f2c8a41d9b7e3f0a6c5...',
        time: '今天 10:24',
        url: 'http://127.0.0.1:9004/huishutai-files/...',
      },
      {
        id: 2,
        name: '知识库-用户手册.md',
        type: 'md',
        size: 86542,
        hash: '3ac9e1b77d02f4a8c1e6...',
        time: '昨天 22:15',
        url: 'http://127.0.0.1:9004/huishutai-files/...',
      },
      {
        id: 3,
        name: 'RAG-评测集.xlsx',
        type: 'xlsx',
        size: 512064,
        hash: 'b71d0c2e9f4a5d8b3c60...',
        time: '10-28 16:02',
        url: 'http://127.0.0.1:9004/huishutai-files/...',
      },
    ],
    routes: [
      {
        path: '/user/register/',
        name: 'user-register',
        view: 'user.views.user_register',
        methods: ['POST'],
        auth: '公开',
        module: 'user',
      },
      {
        path: '/user/login/',
        name: 'user-login',
        view: 'user.views.user_login',
        methods: ['POST'],
        auth: '公开',
        module: 'user',
      },
      {
        path: '/user/logout/',
        name: 'user-logout',
        view: 'user.views.user_logout',
        methods: ['POST'],
        auth: '公开',
        module: 'user',
      },
      {
        path: '/user/check-username/',
        name: 'user-check-username',
        view: 'user.views.username_available',
        methods: ['GET'],
        auth: '公开',
        module: 'user',
      },
      {
        path: '/user/info/',
        name: 'user-info',
        view: 'user.views.user_info',
        methods: ['GET', 'PATCH'],
        auth: '需登录',
        module: 'user',
      },
      {
        path: '/user/password/',
        name: 'user-password',
        view: 'user.views.user_change_password',
        methods: ['POST'],
        auth: '需登录',
        module: 'user',
      },
      {
        path: '/files/upload/',
        name: 'file-upload',
        view: 'files.views.file_upload',
        methods: ['POST'],
        auth: '需登录',
        module: 'files',
      },
      {
        path: '/routes/',
        name: 'route-list',
        view: 'api.views.route_list',
        methods: ['GET'],
        auth: '需登录',
        module: 'api',
      },
      {
        path: '/llm/provider-templates/',
        name: 'llm-provider-templates',
        view: 'LLMapi.views.provider_templates',
        methods: ['GET'],
        auth: '需登录',
        module: 'llm',
      },
      {
        path: '/llm/providers/',
        name: 'llm-providers',
        view: 'LLMapi.views.providers',
        methods: ['GET', 'POST'],
        auth: '需登录',
        module: 'llm',
      },
      {
        path: '/llm/providers/<int:provider_id>/',
        name: 'llm-provider-detail',
        view: 'LLMapi.views.provider_detail',
        methods: ['GET', 'PATCH', 'DELETE'],
        auth: '需登录',
        module: 'llm',
      },
      {
        path: '/llm/providers/<int:provider_id>/refresh-models/',
        name: 'llm-provider-refresh-models',
        view: 'LLMapi.views.provider_refresh_models',
        methods: ['POST'],
        auth: '需登录',
        module: 'llm',
      },
      {
        path: '/llm/models/',
        name: 'llm-models',
        view: 'LLMapi.views.models',
        methods: ['GET'],
        auth: '需登录',
        module: 'llm',
      },
      {
        path: '/llm/models/<int:model_pk>/',
        name: 'llm-model-detail',
        view: 'LLMapi.views.model_detail',
        methods: ['PATCH', 'DELETE'],
        auth: '需登录',
        module: 'llm',
      },
      {
        path: '/llm/chat/',
        name: 'llm-chat',
        view: 'LLMapi.views.chat',
        methods: ['POST'],
        auth: '需登录',
        module: 'llm',
      },
      {
        path: '/llm/embeddings/',
        name: 'llm-embeddings',
        view: 'LLMapi.views.embeddings',
        methods: ['POST'],
        auth: '需登录',
        module: 'llm',
      },
    ],
  }

  /* ==========================================================================
     工具方法
     ========================================================================== */

  var UI = {
    toast: function (title, type, desc) {
      var stack = document.querySelector('.toast-stack')
      if (!stack) {
        stack = document.createElement('div')
        stack.className = 'toast-stack'
        document.body.appendChild(stack)
      }
      var iconName =
        type === 'success'
          ? 'circle-check'
          : type === 'warning'
            ? 'alert-triangle'
            : type === 'danger'
              ? 'circle-x'
              : 'info'
      var el = document.createElement('div')
      el.className = 'toast' + (type ? ' toast-' + type : '')
      el.innerHTML =
        '<span class="toast-icon icon">' +
        iconSvg(iconName) +
        '</span>' +
        '<div class="toast-body"><div class="toast-title"></div>' +
        (desc ? '<div class="toast-desc"></div>' : '') +
        '</div>' +
        '<button class="toast-close" aria-label="关闭">' +
        iconHTML('x') +
        '</button>'
      el.querySelector('.toast-title').textContent = title
      if (desc) el.querySelector('.toast-desc').textContent = desc
      stack.appendChild(el)
      var timer = setTimeout(function () {
        remove()
      }, 2800)
      function remove() {
        clearTimeout(timer)
        el.classList.add('is-leaving')
        setTimeout(function () {
          el.remove()
        }, 200)
      }
      el.querySelector('.toast-close').addEventListener('click', remove)
    },

    copy: function (text) {
      function fallback() {
        var ta = document.createElement('textarea')
        ta.value = text
        ta.style.position = 'fixed'
        ta.style.opacity = '0'
        document.body.appendChild(ta)
        ta.select()
        try {
          document.execCommand('copy')
          UI.toast('已复制到剪贴板', 'success')
        } catch (e) {
          UI.toast('复制失败，请手动选择文本', 'warning')
        }
        ta.remove()
      }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function () {
          UI.toast('已复制到剪贴板', 'success')
        }, fallback)
      } else {
        fallback()
      }
    },

    open: function (id) {
      var el = document.getElementById(id)
      if (!el) return
      el.hidden = false
      el.classList.add('is-open')
      document.body.classList.add('has-overlay')
      var focusable = el.querySelector('input, textarea, select, button:not([data-close])')
      if (focusable)
        setTimeout(function () {
          focusable.focus()
        }, 40)
    },

    close: function (id) {
      var el = typeof id === 'string' ? document.getElementById(id) : id
      if (!el) return
      el.hidden = true
      el.classList.remove('is-open')
      if (
        !document.querySelector(
          '.modal.is-open:not([hidden]), .drawer.is-open:not([hidden]), .command-layer:not([hidden])',
        )
      ) {
        document.body.classList.remove('has-overlay')
      }
    },

    closeAll: function () {
      document.querySelectorAll('.modal.is-open, .drawer.is-open').forEach(function (el) {
        el.hidden = true
        el.classList.remove('is-open')
      })
      var cmd = document.getElementById('app-command')
      if (cmd) cmd.hidden = true
      document.body.classList.remove('has-overlay')
    },

    icon: iconHTML,

    bytes: function (n) {
      if (n === null || n === undefined || isNaN(n)) return '—'
      if (n < 1024) return n + ' B'
      var units = ['KB', 'MB', 'GB', 'TB']
      var i = -1
      do {
        n = n / 1024
        i++
      } while (n >= 1024 && i < units.length - 1)
      return n.toFixed(n >= 100 ? 0 : 1) + ' ' + units[i]
    },

    maskKey: function (key) {
      if (!key) return ''
      if (key.length <= 8) return '****'
      return key.slice(0, 4) + '****' + key.slice(-4)
    },

    now: function () {
      return new Date().toLocaleString('zh-CN', { hour12: false })
    },

    escape: function (str) {
      return String(str).replace(/[&<>"']/g, function (s) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[s]
      })
    },
  }

  /* ==========================================================================
     状态（侧边栏折叠 / 导航分组折叠，写入 localStorage）
     ========================================================================== */

  var STORAGE_KEY = 'huishutai-proto-shell-v1'
  var state = readState()

  function readState() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    } catch (e) {
      return {}
    }
  }

  function saveState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch (e) {
      /* file:// 下可能禁用 localStorage，忽略即可 */
    }
  }

  /* ==========================================================================
     事件总线
     ========================================================================== */

  var listeners = {}

  function on(name, fn) {
    ;(listeners[name] = listeners[name] || []).push(fn)
    return function () {
      listeners[name] = listeners[name].filter(function (f) {
        return f !== fn
      })
    }
  }

  function emit(name, detail) {
    ;(listeners[name] || []).forEach(function (fn) {
      try {
        fn(detail)
      } catch (e) {
        if (window.console) console.error('[AppShell] listener error on "' + name + '"', e)
      }
    })
  }

  /* ==========================================================================
     侧边栏 / 顶栏渲染
     ========================================================================== */

  function currentPage() {
    return document.body.getAttribute('data-page') || ''
  }

  function findNav(page) {
    var found = null
    NAV_GROUPS.some(function (g) {
      return g.items.some(function (item) {
        if (item.id === page) {
          found = { group: g, item: item }
          return true
        }
        return false
      })
    })
    return found
  }

  function brandMarkSVG() {
    return (
      '<svg viewBox="0 0 32 32" fill="none" aria-hidden="true">' +
      '<defs><linearGradient id="hs-brand-g" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">' +
      '<stop stop-color="#5B8CFF"/><stop offset="0.55" stop-color="#3B6CF6"/><stop offset="1" stop-color="#0EB6A6"/>' +
      '</linearGradient></defs>' +
      '<rect width="32" height="32" rx="9" fill="url(#hs-brand-g)"/>' +
      '<path d="M9.5 10.5h6.2a2 2 0 0 1 2 2v9.4a2.6 2.6 0 0 0-2.6-2.6H9.5z" fill="#fff" opacity=".95"/>' +
      '<path d="M22.5 10.5h-6.2a2 2 0 0 0-2 2v9.4a2.6 2.6 0 0 1 2.6-2.6h5.6z" fill="#fff" opacity=".68"/>' +
      '<circle cx="22.6" cy="9.4" r="1.5" fill="#8FF7E8"/>' +
      '</svg>'
    )
  }

  function renderSidebar() {
    var aside = document.getElementById('app-sidebar')
    if (!aside) return

    var active = currentPage()
    var groupsHTML = NAV_GROUPS.map(function (g) {
      var collapsed = !!(state.navCollapsed && state.navCollapsed[g.id])
      var itemsHTML = g.items
        .map(function (item) {
          var isActive = item.id === active
          var badge = item.badge
            ? '<span class="nav-badge' +
              (item.badgeAccent ? ' is-accent' : '') +
              '">' +
              UI.escape(item.badge) +
              '</span>'
            : ''
          return (
            '<a class="nav-item' +
            (isActive ? ' is-active' : '') +
            '" href="' +
            item.href +
            '" data-nav-id="' +
            item.id +
            '">' +
            '<span class="icon nav-icon">' +
            iconSvg(item.icon) +
            '</span>' +
            '<span class="nav-label">' +
            UI.escape(item.label) +
            '</span>' +
            badge +
            '</a>'
          )
        })
        .join('')
      return (
        '<div class="nav-group' +
        (collapsed ? ' is-collapsed' : '') +
        '" data-nav-group="' +
        g.id +
        '">' +
        '<div class="nav-group-label" data-nav-group-toggle="' +
        g.id +
        '">' +
        '<span>' +
        UI.escape(g.label) +
        '</span>' +
        '<span class="icon chev">' +
        iconSvg('chevron-down') +
        '</span>' +
        '</div>' +
        '<div class="nav-group-items">' +
        itemsHTML +
        '</div>' +
        '</div>'
      )
    }).join('')

    aside.innerHTML =
      '<div class="sidebar-inner">' +
      '<a class="brand" href="home.html" title="回到首页">' +
      '<span class="brand-mark">' +
      brandMarkSVG() +
      '</span>' +
      '<span class="brand-text"><strong>汇书台</strong><span class="brand-sub">AI Workspace</span></span>' +
      '<span class="brand-badge">原型</span>' +
      '</a>' +
      '<nav class="nav">' +
      groupsHTML +
      '</nav>' +
      '<div class="sidebar-foot">' +
      '<a class="user-card" href="profile.html">' +
      '<span class="avatar">' +
      UI.escape((MOCK.user.displayName || MOCK.user.username).slice(0, 1)) +
      '</span>' +
      '<span class="user-meta"><strong>' +
      UI.escape(MOCK.user.displayName) +
      '</strong><span>个人中心</span></span>' +
      '</a>' +
      '</div>' +
      '</div>'

    aside.querySelectorAll('[data-nav-group-toggle]').forEach(function (label) {
      label.addEventListener('click', function () {
        var id = label.getAttribute('data-nav-group-toggle')
        var group = aside.querySelector('[data-nav-group="' + id + '"]')
        var collapsed = group.classList.toggle('is-collapsed')
        state.navCollapsed = state.navCollapsed || {}
        state.navCollapsed[id] = collapsed
        saveState()
      })
    })
  }

  function renderTopbar() {
    var header = document.getElementById('app-topbar')
    if (!header) return

    var page = currentPage()
    var nav = findNav(page)
    var title = document.body.getAttribute('data-title') || (nav && nav.item.label) || '首页'
    var crumbHTML =
      page === 'home'
        ? '<span class="crumb-current">首页</span>'
        : '<a href="home.html">首页</a><span class="crumb-sep">/</span>' +
          '<span class="crumb-current">' +
          UI.escape(title) +
          '</span>'

    header.innerHTML =
      '<button class="icon-btn" id="sidebar-toggle" data-tip="收起 / 展开侧边栏" aria-label="切换侧边栏">' +
      iconHTML('panel-left') +
      '</button>' +
      '<nav class="crumb">' +
      crumbHTML +
      '</nav>' +
      '<div class="topbar-right">' +
      '<button class="search-trigger" id="open-command" type="button">' +
      iconHTML('search') +
      '<span>搜索</span>' +
      '<span class="kbd-group"><span class="kbd">Ctrl</span><span class="kbd">K</span></span>' +
      '</button>' +
      '<div class="dropdown">' +
      '<button class="user-trigger" type="button" data-dropdown-toggle aria-haspopup="menu">' +
      '<span class="avatar">' +
      UI.escape(MOCK.user.displayName.slice(0, 1)) +
      '</span>' +
      '<span class="fs-sm">' +
      UI.escape(MOCK.user.displayName) +
      '</span>' +
      '<span class="icon chev" style="width:14px;height:14px">' +
      iconSvg('chevron-down') +
      '</span>' +
      '</button>' +
      '<div class="menu menu-right" role="menu">' +
      '<div class="menu-label">' +
      UI.escape(MOCK.user.username) +
      ' · ' +
      UI.escape(MOCK.user.role) +
      '</div>' +
      '<a class="menu-item" href="profile.html">' +
      iconHTML('user') +
      '个人中心</a>' +
      '<a class="menu-item" href="design-system.html">' +
      iconHTML('palette') +
      '设计规范</a>' +
      '<a class="menu-item" href="index.html">' +
      iconHTML('grid') +
      '原型总览</a>' +
      '<div class="menu-divider"></div>' +
      '<a class="menu-item is-danger" href="login.html">' +
      iconHTML('log-out') +
      '退出登录</a>' +
      '</div>' +
      '</div>' +
      '</div>'

    header.querySelector('#sidebar-toggle').addEventListener('click', toggleSidebar)
    header.querySelector('#open-command').addEventListener('click', openCommandPalette)
  }

  function toggleSidebar() {
    document.body.classList.toggle('app-collapsed')
    state.collapsed = document.body.classList.contains('app-collapsed')
    saveState()
  }

  /* ==========================================================================
     命令面板
     ========================================================================== */

  var paletteState = { index: 0, items: [] }

  function ensurePalette() {
    var layer = document.getElementById('app-command')
    if (layer) return layer
    layer = document.createElement('div')
    layer.className = 'command-layer'
    layer.id = 'app-command'
    layer.hidden = true
    layer.innerHTML =
      '<div class="command-backdrop" data-command-close></div>' +
      '<div class="command-panel" role="dialog" aria-label="命令面板">' +
      '<div class="command-input-row">' +
      iconHTML('search') +
      '<input id="command-input" type="text" placeholder="搜索页面、操作…" autocomplete="off" spellcheck="false" />' +
      '<span class="kbd">Esc</span>' +
      '</div>' +
      '<div class="command-list" id="command-list"></div>' +
      '<div class="command-foot"><span><span class="kbd">↑</span> <span class="kbd">↓</span> 选择</span><span><span class="kbd">Enter</span> 打开</span><span style="margin-left:auto">共 <b id="command-count">0</b> 项</span></div>' +
      '</div>'
    document.body.appendChild(layer)

    layer.querySelector('[data-command-close]').addEventListener('click', closeCommandPalette)
    var input = layer.querySelector('#command-input')
    input.addEventListener('input', function () {
      renderCommands(input.value)
    })
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        moveActive(1)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        moveActive(-1)
      } else if (e.key === 'Enter') {
        e.preventDefault()
        runActive()
      } else if (e.key === 'Escape') {
        closeCommandPalette()
      }
    })
    return layer
  }

  function commandItems() {
    var navItems = []
    NAV_GROUPS.forEach(function (g) {
      g.items.forEach(function (item) {
        navItems.push({
          id: 'nav-' + item.id,
          group: '页面 · ' + g.label,
          title: item.label,
          hint: item.href,
          icon: item.icon,
          keywords: (item.label + ' ' + item.href + ' ' + item.id).toLowerCase(),
          run: function () {
            location.href = item.href
          },
        })
      })
    })
    return navItems.concat(
      COMMANDS.map(function (c) {
        return {
          id: c.id,
          group: c.group,
          title: c.title,
          hint: c.hint || '',
          icon: c.icon || 'command',
          keywords: (
            (c.title || '') +
            ' ' +
            (c.keywords || '') +
            ' ' +
            (c.hint || '')
          ).toLowerCase(),
          run: c.run,
        }
      }),
    )
  }

  function renderCommands(query) {
    var list = document.getElementById('command-list')
    if (!list) return
    var q = (query || '').trim().toLowerCase()
    var items = commandItems().filter(function (c) {
      return !q || c.keywords.indexOf(q) >= 0 || c.title.toLowerCase().indexOf(q) >= 0
    })
    paletteState.items = items
    paletteState.index = 0

    if (!items.length) {
      list.innerHTML = '<div class="command-empty">没有匹配的页面或操作</div>'
      document.getElementById('command-count').textContent = '0'
      return
    }

    var groups = {}
    var order = []
    items.forEach(function (c) {
      if (!groups[c.group]) {
        groups[c.group] = []
        order.push(c.group)
      }
      groups[c.group].push(c)
    })

    var flatIndex = 0
    var html = order
      .map(function (g) {
        return (
          '<div class="command-group-label">' +
          UI.escape(g) +
          '</div>' +
          groups[g]
            .map(function (c) {
              var idx = flatIndex++
              return (
                '<button class="command-item' +
                (idx === 0 ? ' is-active' : '') +
                '" data-command-index="' +
                idx +
                '" type="button">' +
                iconHTML(c.icon) +
                '<span>' +
                UI.escape(c.title) +
                '</span>' +
                (c.hint ? '<span class="command-hint">' + UI.escape(c.hint) + '</span>' : '') +
                '</button>'
              )
            })
            .join('')
        )
      })
      .join('')

    list.innerHTML = html
    document.getElementById('command-count').textContent = String(items.length)

    list.querySelectorAll('[data-command-index]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        runCommand(items[parseInt(btn.getAttribute('data-command-index'), 10)])
      })
    })
  }

  function moveActive(delta) {
    var items = paletteState.items
    if (!items.length) return
    paletteState.index = (paletteState.index + delta + items.length) % items.length
    document.querySelectorAll('.command-item').forEach(function (el, i) {
      el.classList.toggle('is-active', i === paletteState.index)
      if (i === paletteState.index) {
        var list = document.getElementById('command-list')
        var top = el.offsetTop - 60
        if (
          el.offsetTop < list.scrollTop ||
          el.offsetTop + el.offsetHeight > list.scrollTop + list.clientHeight
        ) {
          list.scrollTop = Math.max(0, top)
        }
      }
    })
  }

  function runActive() {
    var item = paletteState.items[paletteState.index]
    if (item) runCommand(item)
  }

  function runCommand(item) {
    closeCommandPalette()
    if (typeof item.run === 'function') item.run()
  }

  function openCommandPalette() {
    var layer = ensurePalette()
    layer.hidden = false
    document.body.classList.add('has-overlay')
    var input = document.getElementById('command-input')
    input.value = ''
    renderCommands('')
    setTimeout(function () {
      input.focus()
    }, 30)
  }

  function closeCommandPalette() {
    var layer = document.getElementById('app-command')
    if (!layer) return
    layer.hidden = true
    if (!document.querySelector('.modal.is-open:not([hidden]), .drawer.is-open:not([hidden])')) {
      document.body.classList.remove('has-overlay')
    }
  }

  /* ==========================================================================
     页面动作栏：常驻操作 ≤ 3，超出自动收入「更多」
     ========================================================================== */

  var PAGE_ACTION_LIMIT = 3

  function overflowPageActions() {
    var bar = document.getElementById('page-actions')
    if (!bar) return
    var items = Array.prototype.slice.call(bar.children).filter(function (el) {
      return (
        !el.classList.contains('dropdown') || el.getAttribute('data-overflow-generated') !== 'true'
      )
    })
    var generated = bar.querySelector('[data-overflow-generated="true"]')
    if (generated) generated.remove()

    if (items.length <= PAGE_ACTION_LIMIT) return

    // 保证主操作（.btn-primary）常驻，其余按原始顺序补足到上限，多余的收入「更多」
    var primary = items.filter(function (el) {
      return el.classList.contains('btn-primary')
    })[0]
    var visible = primary ? [primary] : []
    items.some(function (el) {
      if (el === primary) return false
      if (visible.length >= PAGE_ACTION_LIMIT) return true
      visible.push(el)
      return false
    })
    var rest = items.filter(function (el) {
      return visible.indexOf(el) < 0
    })

    bar.innerHTML = ''
    items.forEach(function (el) {
      if (visible.indexOf(el) >= 0) bar.appendChild(el)
    })

    var dropdown = document.createElement('div')
    dropdown.className = 'dropdown'
    dropdown.setAttribute('data-overflow-generated', 'true')

    var btn = document.createElement('button')
    btn.type = 'button'
    btn.className = 'btn btn-secondary'
    btn.setAttribute('data-dropdown-toggle', '')
    btn.innerHTML = iconHTML('more') + '更多'
    dropdown.appendChild(btn)

    var menu = document.createElement('div')
    menu.className = 'menu menu-right'
    menu.setAttribute('role', 'menu')
    rest.forEach(function (el) {
      var item = document.createElement('button')
      item.type = 'button'
      item.className = 'menu-item'
      item.innerHTML = el.innerHTML
      if (el.classList.contains('btn-danger') || el.classList.contains('btn-danger-soft')) {
        item.classList.add('is-danger')
      }
      item.addEventListener('click', function () {
        if (el.tagName === 'A') {
          location.href = el.getAttribute('href')
        } else {
          el.click()
        }
      })
      menu.appendChild(item)
    })
    dropdown.appendChild(menu)
    bar.appendChild(dropdown)
  }

  function addPageAction(action) {
    var bar = document.getElementById('page-actions')
    if (!bar) return
    var el = document.createElement(action.href ? 'a' : 'button')
    if (action.href) el.href = action.href
    else el.type = 'button'
    el.className = 'btn btn-' + (action.variant || 'secondary') + (action.small ? ' btn-sm' : '')
    el.innerHTML = (action.icon ? iconHTML(action.icon) : '') + UI.escape(action.label || '操作')
    if (action.onClick) el.addEventListener('click', action.onClick)
    bar.appendChild(el)
    overflowPageActions()
  }

  /* ==========================================================================
     通用交互绑定
     ========================================================================== */

  function bindOverlays() {
    document.addEventListener('click', function (e) {
      var opener = e.target.closest('[data-open], [data-modal]')
      if (opener) {
        e.preventDefault()
        var id = opener.getAttribute('data-open') || opener.getAttribute('data-modal')
        UI.open(id)
        return
      }
      var closer = e.target.closest('[data-close]')
      if (closer) {
        e.preventDefault()
        var closeId = closer.getAttribute('data-close')
        if (closeId) UI.close(closeId)
        else {
          var layer = closer.closest('.modal, .drawer')
          if (layer) UI.close(layer)
        }
        return
      }
      var dropdownToggle = e.target.closest('[data-dropdown-toggle]')
      if (dropdownToggle) {
        var dd = dropdownToggle.closest('.dropdown')
        if (dd) {
          e.preventDefault()
          var wasOpen = dd.classList.contains('is-open')
          document.querySelectorAll('.dropdown.is-open').forEach(function (d) {
            d.classList.remove('is-open')
          })
          if (!wasOpen) dd.classList.add('is-open')
        }
        return
      }
      if (!e.target.closest('.menu')) {
        document.querySelectorAll('.dropdown.is-open').forEach(function (d) {
          d.classList.remove('is-open')
        })
      }
      var copyEl = e.target.closest('[data-copy]')
      if (copyEl) {
        e.preventDefault()
        UI.copy(copyEl.getAttribute('data-copy'))
      }
      var alertClose = e.target.closest('[data-alert-close]')
      if (alertClose) {
        var alert = alertClose.closest('.alert')
        if (alert) alert.remove()
      }
    })

    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault()
        if (!document.getElementById('app-topbar')) return
        if (
          document.getElementById('app-command') &&
          !document.getElementById('app-command').hidden
        )
          closeCommandPalette()
        else openCommandPalette()
      } else if (e.key === 'Escape') {
        var cmd = document.getElementById('app-command')
        if (cmd && !cmd.hidden) {
          closeCommandPalette()
          return
        }
        var openLayer = document.querySelector(
          '.modal.is-open:not([hidden]), .drawer.is-open:not([hidden])',
        )
        if (openLayer) {
          UI.close(openLayer)
          return
        }
        document.querySelectorAll('.dropdown.is-open').forEach(function (d) {
          d.classList.remove('is-open')
        })
      }
    })
  }

  function bindTabs() {
    document.querySelectorAll('[data-tabs]').forEach(function (group) {
      var name = group.getAttribute('data-tabs')
      var buttons = Array.prototype.slice.call(group.querySelectorAll('[data-tab]'))
      if (!buttons.length) return
      function activate(key) {
        buttons.forEach(function (btn) {
          btn.classList.toggle('is-active', btn.getAttribute('data-tab') === key)
        })
        document.querySelectorAll('[data-panel-group="' + name + '"]').forEach(function (panel) {
          var show = panel.getAttribute('data-panel') === key
          panel.hidden = !show
          panel.classList.toggle('is-hidden', !show)
        })
        emit('tab:change', { name: name, key: key })
      }
      buttons.forEach(function (btn) {
        btn.addEventListener('click', function () {
          activate(btn.getAttribute('data-tab'))
        })
      })
      var active = buttons.filter(function (b) {
        return b.classList.contains('is-active')
      })[0]
      activate((active || buttons[0]).getAttribute('data-tab'))
    })
  }

  function injectIcons(root) {
    ;(root || document).querySelectorAll('[data-icon]').forEach(function (el) {
      var name = el.getAttribute('data-icon')
      var svg = iconSvg(name)
      if (el.tagName === 'I' || el.classList.contains('icon')) {
        el.classList.add('icon')
        el.innerHTML = svg
        el.removeAttribute('data-icon')
      } else {
        var span = document.createElement('span')
        span.className = 'icon'
        span.innerHTML = svg
        el.insertBefore(span, el.firstChild)
        el.removeAttribute('data-icon')
      }
    })
  }

  /* ==========================================================================
     初始化
     ========================================================================== */

  function isAppLayout() {
    return (
      document.body.getAttribute('data-layout') !== 'auth' &&
      document.body.getAttribute('data-layout') !== 'showcase'
    )
  }

  function init() {
    if (document.body.classList.contains('app-collapsed') || state.collapsed) {
      document.body.classList.add('app-collapsed')
    }

    if (isAppLayout()) {
      renderSidebar()
      renderTopbar()
    }

    injectIcons(document)
    bindOverlays()
    bindTabs()
    overflowPageActions()

    if (isAppLayout()) {
      emit('page:ready', { page: currentPage() })
    }
  }

  /* ==========================================================================
     对外扩展入口
     ========================================================================== */

  window.AppUI = UI
  window.AppMock = MOCK

  window.AppShell = {
    version: '1.0.0',
    icons: ICONS,
    icon: iconHTML,
    nav: {
      groups: NAV_GROUPS,
      addGroup: function (group) {
        NAV_GROUPS.push(group)
        if (isAppLayout()) {
          renderSidebar()
          injectIcons(document)
        }
      },
      addItem: function (groupId, item) {
        var group = NAV_GROUPS.filter(function (g) {
          return g.id === groupId
        })[0]
        if (!group) return
        group.items.push(item)
        if (isAppLayout()) {
          renderSidebar()
          injectIcons(document)
        }
      },
    },
    commands: {
      list: COMMANDS,
      add: function (command) {
        COMMANDS.push(command)
      },
    },
    page: {
      addAction: addPageAction,
      overflow: overflowPageActions,
    },
    on: on,
    emit: emit,
    toast: UI.toast,
    openCommandPalette: openCommandPalette,
    toggleSidebar: toggleSidebar,
    go: function (href) {
      location.href = href
    },
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init)
  } else {
    init()
  }
})()
