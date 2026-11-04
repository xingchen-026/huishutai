import request from './request'
import type { ApiResult } from './user'

export interface UploadedFileData {
  id: number
  user_id: number
  original_name: string
  bucket: string
  object_key: string
  file_hash: string
  file_size: number
  content_type: string
  created_at: string
  url: string
  url_expires_in: number
}

/** 上传文件：POST /files/upload/（multipart 字段 file） */
// eslint-disable-next-line no-unused-vars -- 回调类型参数仅用于文档说明，核心规则会误报
export function uploadFile(file: File, onProgress?: (percent: number) => void) {
  const form = new FormData()
  form.append('file', file)

  return request.post<any, ApiResult<UploadedFileData>>('/files/upload/', form, {
    timeout: 120_000,
    onUploadProgress: (event) => {
      if (!event.total) return
      onProgress?.(Math.min(100, Math.round((event.loaded / event.total) * 100)))
    },
  })
}
