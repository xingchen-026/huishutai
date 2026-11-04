import request from './request'
import type { ApiResult } from './user'

export type ModelCategory = 'chat' | 'embedding' | 'rerank' | 'image' | 'audio' | 'other'

export interface ProviderTemplate {
  code: string
  name: string
  protocol: 'openai' | 'anthropic' | 'gemini'
  default_base_url: string
  docs_url: string
  requires_api_key: boolean
  description: string
}

export interface ProviderTemplateData {
  templates: ProviderTemplate[]
  categories: { code: ModelCategory; label: string }[]
}

export interface LLMProvider {
  id: number
  name: string
  template_code: string
  template_name: string
  protocol: string
  base_url: string
  api_key_masked: string
  enabled: boolean
  model_count: number
  last_synced_at: string | null
  last_sync_error: string
  created_at: string
}

export interface ParamSpecItem {
  name: string
  type: string
  required: boolean
  description: string
  default?: unknown
  minimum?: number
  maximum?: number
  enum?: string[]
}

export interface LLMModel {
  id: number
  provider_id: number
  provider_name: string
  template_code: string
  protocol: string
  model_id: string
  display_name: string
  category: ModelCategory
  category_label: string
  param_spec: ParamSpecItem[]
  source: 'auto' | 'manual'
  enabled: boolean
  synced_at: string | null
  created_at: string
}

export interface ModelSyncResult {
  status: string
  count: number
  message: string
}

/* ---------------- 供应商 ---------------- */

export function getProviderTemplates() {
  return request.get<any, ApiResult<ProviderTemplateData>>('/llm/provider-templates/')
}

export function listProviders() {
  return request.get<any, ApiResult<{ total: number; providers: LLMProvider[] }>>('/llm/providers/')
}

export function createProvider(payload: {
  template_code: string
  name?: string
  base_url?: string
  api_key?: string
}) {
  return request.post<any, ApiResult<{ provider: LLMProvider; model_sync: ModelSyncResult }>>(
    '/llm/providers/',
    payload,
  )
}

export function updateProvider(
  providerId: number,
  payload: { name?: string; enabled?: boolean; base_url?: string; api_key?: string },
) {
  return request.patch<any, ApiResult<{ provider: LLMProvider; model_sync?: ModelSyncResult }>>(
    `/llm/providers/${providerId}/`,
    payload,
  )
}

export function deleteProvider(providerId: number) {
  return request.delete<any, ApiResult<{ id: number }>>(`/llm/providers/${providerId}/`)
}

export function refreshProviderModels(providerId: number) {
  return request.post<any, ApiResult<{ count?: number }>>(
    `/llm/providers/${providerId}/refresh-models/`,
  )
}

/* ---------------- 模型 ---------------- */

export function listProviderModels(providerId: number) {
  return request.get<any, ApiResult<{ total: number; models: LLMModel[] }>>(
    `/llm/providers/${providerId}/models/`,
  )
}

export function addManualModel(
  providerId: number,
  payload: { model_id: string; display_name?: string; category?: ModelCategory | '' },
) {
  return request.post<any, ApiResult<{ model: LLMModel }>>(
    `/llm/providers/${providerId}/models/`,
    payload,
  )
}

export function updateModel(
  modelPk: number,
  payload: { enabled?: boolean; display_name?: string },
) {
  return request.patch<any, ApiResult<{ model: LLMModel }>>(`/llm/models/${modelPk}/`, payload)
}

export function deleteModel(modelPk: number) {
  return request.delete<any, ApiResult<{ id: number }>>(`/llm/models/${modelPk}/`)
}
