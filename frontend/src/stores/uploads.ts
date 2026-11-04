import { computed } from 'vue'
import { defineStore } from 'pinia'
import { useStorage } from '@vueuse/core'
import { useAuthStore } from './auth'

export interface UploadRecord {
  id: number
  name: string
  size: number
  hash: string
  bucket: string
  objectKey: string
  url: string
  createdAt: string
}

/**
 * 本地上传历史（按用户隔离）：
 * 后端暂无"文件列表"接口，先把上传成功的元数据存 localStorage；
 * 列表接口落地后替换本 store 实现即可，页面无需改动。
 */
export const useUploadsStore = defineStore('uploads', () => {
  const auth = useAuthStore()
  const all = useStorage<Record<string, UploadRecord[]>>('huishutai-uploads-v1', {})

  const records = computed(() => {
    const key = String(auth.userId ?? 'guest')
    return all.value[key] ?? []
  })

  function add(record: UploadRecord) {
    const key = String(auth.userId ?? 'guest')
    all.value = {
      ...all.value,
      [key]: [record, ...(all.value[key] ?? [])].slice(0, 50),
    }
  }

  function remove(id: number) {
    const key = String(auth.userId ?? 'guest')
    all.value = {
      ...all.value,
      [key]: (all.value[key] ?? []).filter((item) => item.id !== id),
    }
  }

  return { records, add, remove }
})
