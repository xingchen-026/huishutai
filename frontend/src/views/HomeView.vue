<script setup lang="ts">
import AppIcon from '@/components/ui/AppIcon.vue'

interface AppEntry {
  title: string
  desc: string
  icon: string
  to?: string
}

const apps: AppEntry[] = [
  { title: '知识库', desc: '上传文档，检索与问答', icon: 'book', to: '/knowledge' },
  { title: '模型服务', desc: '配置供应商，管理可用模型', icon: 'cpu', to: '/models' },
  { title: 'Agent 编排', desc: '多步骤任务与工具调用', icon: 'sparkles' },
  { title: '文生图', desc: '文本生成图像', icon: 'image' },
  { title: '文生视频', desc: '文本生成视频', icon: 'film' },
  { title: '更多应用', desc: '按模块逐步接入', icon: 'plus' },
]
</script>

<template>
  <div class="home-head">
    <h1 class="home-title">汇书台</h1>
    <p class="home-sub">选择要使用的应用</p>
  </div>

  <div class="app-grid">
    <template v-for="app in apps" :key="app.title">
      <RouterLink v-if="app.to" class="app-card is-available" :to="app.to">
        <span class="app-card-icon"><AppIcon :name="app.icon" /></span>
        <div>
          <div class="app-card-title">{{ app.title }}</div>
          <div class="app-card-desc">{{ app.desc }}</div>
        </div>
        <div class="app-card-foot">进入 <AppIcon name="arrow-right" class="icon-sm" /></div>
      </RouterLink>

      <div v-else class="app-card is-planned">
        <span class="app-card-icon"><AppIcon :name="app.icon" /></span>
        <div>
          <div class="app-card-title">{{ app.title }}</div>
          <div class="app-card-desc">{{ app.desc }}</div>
        </div>
        <div class="app-card-foot">即将上线</div>
      </div>
    </template>
  </div>

  <p class="notice-line"><AppIcon name="info" class="icon-sm" />汇书台 · AI 应用落地技术整合实践</p>
</template>
