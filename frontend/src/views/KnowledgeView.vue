<script setup lang="ts">
import { ref } from 'vue'
import { useClipboard, useDropZone, useFileDialog } from '@vueuse/core'
import AppIcon from '@/components/ui/AppIcon.vue'
import { useUploadsStore, type UploadRecord } from '@/stores/uploads'
import { useToastStore } from '@/stores/toast'
import { uploadFile } from '@/api/files'
import { getErrorMessage } from '@/utils/error'

/** 与后端 config/settings.py 保持一致；后端调整时同步修改这里 */
const MAX_SIZE = 50 * 1024 * 1024
const ALLOWED_EXTENSIONS = [
  '.pdf',
  '.txt',
  '.md',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.ppt',
  '.pptx',
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.zip',
]

const toast = useToastStore()
const uploads = useUploadsStore()

const pendingFile = ref<File | null>(null)
const uploading = ref(false)
const progress = ref(0)
const pageError = ref('')
const uploadZone = ref<HTMLElement | null>(null)

const { open: openFilePicker, onChange } = useFileDialog({
  accept: ALLOWED_EXTENSIONS.join(','),
  multiple: false,
})

onChange((files) => {
  const file = files?.[0]
  if (file) selectFile(file)
})

const { isOverDropZone } = useDropZone(uploadZone, {
  onDrop: (files) => {
    const file = files?.[0]
    if (file) selectFile(file)
  },
})

const { copy, isSupported: clipboardSupported } = useClipboard({ legacy: true })

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString('zh-CN', { hour12: false })
}

function validateFile(file: File): string | null {
  if (file.size <= 0) return '不能上传空文件'
  if (file.size > MAX_SIZE) return `文件大小超过限制（最大 ${MAX_SIZE / 1024 / 1024}MB）`
  const lower = file.name.toLowerCase()
  const allowed = ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))
  return allowed ? null : '不支持的文件类型'
}

function selectFile(file: File) {
  pageError.value = ''
  const message = validateFile(file)
  if (message) {
    pageError.value = message
    toast.error('文件校验未通过', message)
    return
  }
  pendingFile.value = file
}

async function startUpload() {
  if (!pendingFile.value || uploading.value) return
  uploading.value = true
  progress.value = 0
  try {
    const res = await uploadFile(pendingFile.value, (percent) => {
      progress.value = percent
    })
    if (res.code !== 0) {
      toast.error('上传失败', res.message)
      return
    }
    const data = res.data
    const record: UploadRecord = {
      id: data.id,
      name: data.original_name,
      size: data.file_size,
      hash: data.file_hash,
      bucket: data.bucket,
      objectKey: data.object_key,
      url: data.url,
      createdAt: data.created_at,
    }
    uploads.add(record)
    pendingFile.value = null
    toast.success('上传成功', '已生成 1 小时有效的临时访问链接')
  } catch (err) {
    toast.error('上传失败', getErrorMessage(err))
  } finally {
    uploading.value = false
    progress.value = 0
  }
}

async function copyUrl(url: string) {
  if (!clipboardSupported.value) {
    toast.error('复制失败', '当前浏览器不支持剪贴板')
    return
  }
  await copy(url)
  toast.success('链接已复制')
}

function openUrl(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

function removeRecord(record: UploadRecord) {
  uploads.remove(record.id)
  toast.info('已从本地列表移除', '后端文件删除接口尚未提供，仅移除本地记录')
}
</script>

<template>
  <div class="page-head">
    <div class="page-head-main">
      <h1 class="page-title">知识库</h1>
      <p class="page-desc">上传文档，构建可检索的知识库。</p>
    </div>
    <div class="page-actions">
      <button class="btn btn-primary" type="button" @click="openFilePicker()">
        <AppIcon name="upload" />上传文档
      </button>
    </div>
  </div>

  <section class="card">
    <div class="card-head">
      <div class="card-head-main"><h3 class="card-title">文档</h3></div>
      <div class="card-extra">
        <span class="fs-sm subtle">共 {{ uploads.records.length }} 个</span>
      </div>
    </div>

    <div class="card-body">
      <div
        ref="uploadZone"
        class="upload-inline"
        :class="{ 'is-drag': isOverDropZone }"
        role="button"
        tabindex="0"
        @click="openFilePicker()"
        @keydown.enter.prevent="openFilePicker()"
      >
        <span class="upload-inline-icon"><AppIcon name="upload" /></span>
        <div class="upload-inline-main">
          <div class="upload-inline-title">拖拽或点击上传文档</div>
          <div class="upload-inline-hint">PDF / Word / Markdown · 单文件 ≤ 50MB</div>
        </div>
        <div v-if="pendingFile" class="upload-inline-actions" @click.stop>
          <span class="upload-file">
            <AppIcon name="file-text" />
            <span>{{ pendingFile.name }}</span>
          </span>
          <button class="btn btn-sm" type="button" :disabled="uploading" @click="startUpload">
            {{ uploading ? `${progress}%` : '上传' }}
          </button>
          <button
            class="icon-btn"
            type="button"
            title="取消"
            :disabled="uploading"
            @click="pendingFile = null"
          >
            <AppIcon name="x" />
          </button>
        </div>
      </div>

      <div v-if="uploading" class="progress mt-3">
        <div class="progress-bar" :style="{ width: `${progress}%` }" />
      </div>
      <p v-if="pageError" class="field-error mt-3">{{ pageError }}</p>
    </div>

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>文档</th>
            <th>大小</th>
            <th>状态</th>
            <th>上传时间</th>
            <th class="th-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in uploads.records" :key="record.id">
            <td>
              <div class="doc-name">
                <AppIcon name="file-text" />
                <span class="truncate">{{ record.name }}</span>
              </div>
            </td>
            <td class="num">{{ formatBytes(record.size) }}</td>
            <td>
              <span class="doc-status"><span class="status-dot is-ok" />已上传</span>
            </td>
            <td class="num">{{ formatTime(record.createdAt) }}</td>
            <td>
              <div class="cell-actions">
                <button
                  class="icon-btn"
                  type="button"
                  title="打开临时链接"
                  @click="openUrl(record.url)"
                >
                  <AppIcon name="external-link" />
                </button>
                <button
                  class="icon-btn"
                  type="button"
                  title="复制链接"
                  @click="copyUrl(record.url)"
                >
                  <AppIcon name="copy" />
                </button>
                <button
                  class="icon-btn"
                  type="button"
                  title="移除本地记录"
                  @click="removeRecord(record)"
                >
                  <AppIcon name="trash" />
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!uploads.records.length">
            <td colspan="5">
              <div class="empty" style="padding: 40px 24px">
                <span class="empty-icon"><AppIcon name="folder" /></span>
                <h3>还没有上传过文档</h3>
                <p>
                  上传后的文件会显示在这里；后端文件列表接口尚未提供，当前展示本次在浏览器上传的历史。
                </p>
                <button class="btn btn-secondary btn-sm" type="button" @click="openFilePicker()">
                  上传第一个文档
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="card mt-4">
    <div class="card-head">
      <div class="card-head-main"><h3 class="card-title">知识库问答</h3></div>
      <div class="card-extra"><span class="badge badge-dashed">即将上线</span></div>
    </div>
    <div class="card-body">
      <div class="qa-bar">
        <AppIcon name="search" />
        <input class="input" placeholder="基于知识库提问" disabled />
        <button class="btn btn-secondary" type="button" disabled>提问</button>
      </div>
    </div>
  </section>

  <p class="quiet-note">
    文档解析、向量化与问答能力正在接入；当前已支持上传、临时链接与本地历史记录。
  </p>
</template>
