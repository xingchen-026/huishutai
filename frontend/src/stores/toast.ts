import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ToastType = 'success' | 'warning' | 'danger' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  title: string
  desc?: string
}

export const useToastStore = defineStore('toast', () => {
  const items = ref<ToastItem[]>([])
  let seed = 0

  function remove(id: number) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  function push(type: ToastType, title: string, desc?: string) {
    const id = ++seed
    items.value.push({ id, type, title, desc })
    window.setTimeout(() => remove(id), 2800)
  }

  const success = (title: string, desc?: string) => push('success', title, desc)
  const warning = (title: string, desc?: string) => push('warning', title, desc)
  const error = (title: string, desc?: string) => push('danger', title, desc)
  const info = (title: string, desc?: string) => push('info', title, desc)

  return { items, remove, push, success, warning, error, info }
})
