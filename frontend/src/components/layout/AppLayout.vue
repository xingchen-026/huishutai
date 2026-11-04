<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { onClickOutside, useEventListener, useStorage, useToggle } from '@vueuse/core'
import AppIcon from '@/components/ui/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useToastStore } from '@/stores/toast'
import { logout } from '@/api/user'

interface NavItem {
  id: string
  label: string
  icon: string
  to: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: '工作区',
    items: [
      { id: 'home', label: '首页', icon: 'home', to: '/home' },
      { id: 'knowledge', label: '知识库', icon: 'book', to: '/knowledge' },
    ],
  },
  {
    label: '服务',
    items: [{ id: 'models', label: '模型服务', icon: 'cpu', to: '/models' }],
  },
]

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const theme = useThemeStore()
const toast = useToastStore()

const pageTitle = computed(() => String(route.meta.title || ''))

/* 侧边栏折叠：持久化 + 复用 body.app-collapsed 样式 */
const collapsed = useStorage('huishutai-sidebar', false)

watchEffect(() => {
  document.body.classList.toggle('app-collapsed', collapsed.value)
})

onBeforeUnmount(() => {
  document.body.classList.remove('app-collapsed')
})

/* 用户菜单 */
const [userMenuOpen, toggleUserMenu] = useToggle(false)
const userMenuRef = ref<HTMLElement | null>(null)

onClickOutside(userMenuRef, () => {
  userMenuOpen.value = false
})

useEventListener(document, 'keydown', (event: KeyboardEvent) => {
  if (event.key === 'Escape') userMenuOpen.value = false
})

async function onLogout() {
  userMenuOpen.value = false
  try {
    await logout()
  } catch {
    // 退出接口失败也继续清本地登录态
  }
  auth.clear()
  toast.info('已退出登录')
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-inner">
        <RouterLink class="brand" to="/home" title="回到首页">
          <span class="brand-mark">
            <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <defs>
                <linearGradient
                  id="hs-brand-g"
                  x1="0"
                  y1="0"
                  x2="32"
                  y2="32"
                  gradientUnits="userSpaceOnUse"
                >
                  <stop stop-color="#5B8CFF" />
                  <stop offset="0.55" stop-color="#3B6CF6" />
                  <stop offset="1" stop-color="#0EB6A6" />
                </linearGradient>
              </defs>
              <rect width="32" height="32" rx="9" fill="url(#hs-brand-g)" />
              <path
                d="M9.5 10.5h6.2a2 2 0 0 1 2 2v9.4a2.6 2.6 0 0 0-2.6-2.6H9.5z"
                fill="#fff"
                opacity=".95"
              />
              <path
                d="M22.5 10.5h-6.2a2 2 0 0 0-2 2v9.4a2.6 2.6 0 0 1 2.6-2.6h5.6z"
                fill="#fff"
                opacity=".68"
              />
              <circle cx="22.6" cy="9.4" r="1.5" fill="#8FF7E8" />
            </svg>
          </span>
          <span class="brand-text">
            <strong>汇书台</strong>
            <span class="brand-sub">AI Workspace</span>
          </span>
        </RouterLink>

        <nav class="nav">
          <div v-for="group in NAV_GROUPS" :key="group.label" class="nav-group">
            <div class="nav-group-label">
              <span>{{ group.label }}</span>
            </div>
            <div class="nav-group-items">
              <RouterLink
                v-for="item in group.items"
                :key="item.id"
                :to="item.to"
                class="nav-item"
                :class="{ 'is-active': route.name === item.id }"
              >
                <AppIcon :name="item.icon" class="nav-icon" />
                <span class="nav-label">{{ item.label }}</span>
              </RouterLink>
            </div>
          </div>
        </nav>

        <div class="sidebar-foot">
          <RouterLink class="user-card" to="/profile">
            <span class="avatar">{{ auth.avatarText }}</span>
            <span class="user-meta">
              <strong>{{ auth.username || '未登录' }}</strong>
              <span>个人中心</span>
            </span>
          </RouterLink>
        </div>
      </div>
    </aside>

    <div class="shell-main">
      <header class="topbar">
        <button
          class="icon-btn"
          type="button"
          title="收起 / 展开侧边栏"
          aria-label="切换侧边栏"
          @click="collapsed = !collapsed"
        >
          <AppIcon name="panel-left" />
        </button>

        <nav class="crumb">
          <template v-if="route.name === 'home'">
            <span class="crumb-current">首页</span>
          </template>
          <template v-else>
            <RouterLink to="/home">首页</RouterLink>
            <span class="crumb-sep">/</span>
            <span class="crumb-current">{{ pageTitle }}</span>
          </template>
        </nav>

        <div class="topbar-right">
          <button
            class="icon-btn"
            type="button"
            :title="theme.isDark ? '切换为白天模式' : '切换为夜晚模式'"
            :aria-label="theme.isDark ? '切换为白天模式' : '切换为夜晚模式'"
            @click="theme.toggleTheme"
          >
            <AppIcon :name="theme.isDark ? 'sun' : 'moon'" />
          </button>

          <div ref="userMenuRef" class="dropdown" :class="{ 'is-open': userMenuOpen }">
            <button
              class="user-trigger"
              type="button"
              aria-haspopup="menu"
              @click.stop="toggleUserMenu()"
            >
              <span class="avatar">{{ auth.avatarText }}</span>
              <span class="fs-sm">{{ auth.username || '未登录' }}</span>
              <AppIcon name="chevron-down" class="chev" style="width: 14px; height: 14px" />
            </button>
            <div v-if="userMenuOpen" class="menu menu-right" role="menu">
              <div class="menu-label">{{ auth.username }}</div>
              <RouterLink class="menu-item" to="/profile">
                <AppIcon name="user" />个人中心
              </RouterLink>
              <div class="menu-divider"></div>
              <button class="menu-item is-danger" type="button" @click="onLogout">
                <AppIcon name="log-out" />退出登录
              </button>
            </div>
          </div>
        </div>
      </header>

      <main class="page">
        <RouterView />
      </main>
    </div>
  </div>
</template>
