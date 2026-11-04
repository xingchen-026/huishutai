<script setup lang="ts">
import AppIcon from '@/components/ui/AppIcon.vue'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

const TOAST_ICONS: Record<string, string> = {
  success: 'circle-check',
  warning: 'alert-triangle',
  danger: 'circle-x',
  info: 'info',
}
</script>

<template>
  <RouterView />

  <div class="toast-stack">
    <div v-for="item in toast.items" :key="item.id" class="toast" :class="`toast-${item.type}`">
      <AppIcon :name="TOAST_ICONS[item.type] || 'info'" />
      <div class="toast-body">
        <div class="toast-title">{{ item.title }}</div>
        <div v-if="item.desc" class="toast-desc">{{ item.desc }}</div>
      </div>
      <button class="toast-close" type="button" aria-label="关闭" @click="toast.remove(item.id)">
        <AppIcon name="x" />
      </button>
    </div>
  </div>
</template>
