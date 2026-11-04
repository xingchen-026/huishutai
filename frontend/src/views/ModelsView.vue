<script setup lang="ts">
import { computed, onMounted, reactive, ref, watchEffect } from 'vue'
import { useEventListener, useScrollLock } from '@vueuse/core'
import AppIcon from '@/components/ui/AppIcon.vue'
import { useToastStore } from '@/stores/toast'
import {
  addManualModel,
  createProvider,
  deleteModel,
  deleteProvider,
  getProviderTemplates,
  listProviderModels,
  listProviders,
  refreshProviderModels,
  updateModel,
  updateProvider,
  type LLMModel,
  type LLMProvider,
  type ModelCategory,
  type ParamSpecItem,
  type ProviderTemplate,
} from '@/api/llm'
import { getErrorMessage } from '@/utils/error'
import type { C } from 'vue-router/dist/index-u4XkZVDG.js'

const CATEGORY_BADGE: Record<string, string> = {
  chat: 'badge-info',
  embedding: 'badge-teal',
  rerank: 'badge-neutral',
  image: 'badge-violet',
  audio: 'badge-warning',
  other: 'badge-neutral',
}

const { success, error, info } = useToastStore()

const templates = ref<ProviderTemplate[]>([])
const categories = ref<{ code: ModelCategory; label: string }[]>([])

const providers = ref<LLMProvider[]>([])
const providersLoading = ref(true)
const pageError = ref('')

const currentProviderId = ref<number | null>(null)
const models = ref<LLMModel[]>([])
const modelsLoading = ref(false)
const syncing = ref(false)

const keyword = ref('')
const categoryFilter = ref<'all' | ModelCategory>('all')

const currentProvider = computed(
  () => providers.value.find((item) => item.id === currentProviderId.value) || null,
)

const filteredModels = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return models.value.filter((model) => {
    const matchCategory = categoryFilter.value === 'all' || model.category === categoryFilter.value
    const matchKeyword =
      !kw ||
      model.display_name.toLowerCase().includes(kw) ||
      model.model_id.toLowerCase().includes(kw)
    return matchCategory && matchKeyword
  })
})

/* ---------------- 加载 ---------------- */

async function loadTemplates() {
  try {
    const res = await getProviderTemplates()
    if (res.code !== 0) throw new Error(res.message)
    templates.value = res.data.templates
    categories.value = res.data.categories
  } catch (err) {
    error('加载供应商模板失败', getErrorMessage(err))
  }
}

async function loadProviders(preferId?: number) {
  providersLoading.value = true
  pageError.value = ''
  try {
    const res = await listProviders()
    if (res.code !== 0) throw new Error(res.message)
    providers.value = res.data.providers
    const targetId =
      preferId ??
      (providers.value.some((item) => item.id === currentProviderId.value)
        ? currentProviderId.value
        : (providers.value[0]?.id ?? null))
    currentProviderId.value = targetId
  } catch (err) {
    pageError.value = getErrorMessage(err, '加载供应商失败')
  } finally {
    providersLoading.value = false
  }
}

async function loadModels() {
  const providerId = currentProviderId.value
  if (!providerId) {
    models.value = []
    return
  }
  modelsLoading.value = true
  try {
    const res = await listProviderModels(providerId)
    if (res.code !== 0) throw new Error(res.message)
    if (currentProviderId.value !== providerId) return
    models.value = res.data.models
  } catch (err) {
    error('加载模型失败', getErrorMessage(err))
  } finally {
    modelsLoading.value = false
  }
}

async function selectProvider(providerId: number) {
  if (currentProviderId.value === providerId) return
  currentProviderId.value = providerId
  keyword.value = ''
  categoryFilter.value = 'all'
  await loadModels()
}

/* ---------------- 删除确认 ---------------- */

const confirmState = reactive({
  open: false,
  title: '',
  message: '',
  action: () => {},
})

function askConfirm(title: string, message: string, action: () => void) {
  confirmState.title = title
  confirmState.message = message
  confirmState.action = action
  confirmState.open = true
}

function closeConfirm() {
  confirmState.open = false
}

function runConfirm() {
  const action = confirmState.action
  confirmState.open = false
  action()
}

/* ---------------- 供应商抽屉 ---------------- */

const providerDrawer = ref(false)
const providerMode = ref<'create' | 'edit'>('create')
const providerSaving = ref(false)
const providerError = ref('')
const providerForm = reactive({
  template_code: 'deepseek',
  name: '',
  base_url: '',
  api_key: '',
  enabled: true,
})

const selectedTemplate = computed(
  () => templates.value.find((item) => item.code === providerForm.template_code) || null,
)

function openCreateProvider() {
  providerMode.value = 'create'
  providerError.value = ''
  const template = templates.value[0]
  providerForm.template_code = template?.code || 'deepseek'
  providerForm.name = template?.name || ''
  providerForm.base_url = template?.default_base_url || ''
  providerForm.api_key = ''
  providerForm.enabled = true
  providerDrawer.value = true
}

function openEditProvider() {
  const provider = currentProvider.value
  if (!provider) return
  providerMode.value = 'edit'
  providerError.value = ''
  providerForm.template_code = provider.template_code
  providerForm.name = provider.name
  providerForm.base_url = provider.base_url
  providerForm.api_key = ''
  providerForm.enabled = provider.enabled
  providerDrawer.value = true
}

function onTemplateChange() {
  const template = selectedTemplate.value
  if (!template) return
  if (providerMode.value === 'create') {
    providerForm.name = template.name
    providerForm.base_url = template.default_base_url
  }
}

async function submitProvider() {
  providerError.value = ''
  const name = providerForm.name.trim()
  if (!name) {
    providerError.value = '请输入配置名称'
    return
  }
  if (providerMode.value === 'create') {
    if (selectedTemplate.value?.requires_api_key && !providerForm.api_key.trim()) {
      providerError.value = '请填写该供应商的 API Key'
      return
    }
  }

  providerSaving.value = true
  try {
    if (providerMode.value === 'create') {
      const res = await createProvider({
        template_code: providerForm.template_code,
        name,
        base_url: providerForm.base_url.trim() || undefined,
        api_key: providerForm.api_key.trim() || undefined,
      })
      if (res.code !== 0) throw new Error(res.message)
      providerDrawer.value = false
      success('供应商配置已保存', res.message)
      await loadProviders(res.data.provider.id)
      await loadModels()
    } else {
      const providerId = currentProviderId.value
      if (!providerId) return
      const payload: { name: string; enabled: boolean; base_url: string; api_key?: string } = {
        name,
        enabled: providerForm.enabled,
        base_url: providerForm.base_url.trim() || currentProvider.value?.base_url || '',
      }
      if (providerForm.api_key.trim()) payload.api_key = providerForm.api_key.trim()
      const res = await updateProvider(providerId, payload)
      if (res.code !== 0) throw new Error(res.message)
      providerDrawer.value = false
      success('供应商配置已更新', res.message)
      await loadProviders(providerId)
      await loadModels()
    }
  } catch (err) {
    providerError.value = getErrorMessage(err, '保存失败，请稍后再试')
  } finally {
    providerSaving.value = false
  }
}

function removeProvider() {
  const provider = currentProvider.value
  if (!provider) return
  askConfirm('删除供应商', `确定删除「${provider.name}」及其下所有模型吗？`, async () => {
    try {
      const res = await deleteProvider(provider.id)
      if (res.code !== 0) throw new Error(res.message)
      success('供应商已删除')
      currentProviderId.value = null
      models.value = []
      await loadProviders()
      await loadModels()
    } catch (err) {
      error('删除失败', getErrorMessage(err))
    }
  })
}

async function syncProvider() {
  const provider = currentProvider.value
  if (!provider || syncing.value) return
  syncing.value = true
  try {
    const res = await refreshProviderModels(provider.id)
    if (res.code !== 0) throw new Error(res.message)
    success('模型同步完成', res.message)
    await loadProviders(provider.id)
    await loadModels()
  } catch (err) {
    error('模型同步失败', getErrorMessage(err))
  } finally {
    syncing.value = false
  }
}

/* ---------------- 模型操作 ---------------- */

const specModel = ref<LLMModel | null>(null)

const specRows = computed(() => {
  const spec = specModel.value?.param_spec ?? []
  return spec.map((item) => ({
    name: item.name,
    type: item.type,
    required: item.required ? '必填' : '可选',
    range: formatParamRange(item),
    default: item.default === undefined ? '—' : String(item.default),
    description: item.description,
  }))
})

function formatParamRange(item: ParamSpecItem): string {
  if (item.enum?.length) return item.enum.join(' / ')
  if (item.minimum !== undefined && item.maximum !== undefined) {
    return `${item.minimum} – ${item.maximum}`
  }
  if (item.minimum !== undefined) return `≥ ${item.minimum}`
  if (item.maximum !== undefined) return `≤ ${item.maximum}`
  return '—'
}

function openSpec(model: LLMModel) {
  specModel.value = model
}

async function toggleModel(model: LLMModel, event: Event) {
  const target = event.target as HTMLInputElement
  const nextEnabled = target.checked
  try {
    const res = await updateModel(model.id, { enabled: nextEnabled })
    if (res.code !== 0) throw new Error(res.message)
    model.enabled = nextEnabled
    success(`模型「${model.display_name}」已${nextEnabled ? '启用' : '停用'}`)
  } catch (err) {
    target.checked = model.enabled
    error('操作失败', getErrorMessage(err))
  }
}

function removeModel(model: LLMModel) {
  askConfirm('删除模型', `确定删除模型「${model.display_name}」吗？`, async () => {
    try {
      const res = await deleteModel(model.id)
      if (res.code !== 0) throw new Error(res.message)
      success('模型已删除')
      await loadModels()
      await loadProviders(currentProviderId.value ?? undefined)
    } catch (err) {
      error('删除失败', getErrorMessage(err))
    }
  })
}

/* ---------------- 手动登记 ---------------- */

const manualModal = ref(false)
const manualSaving = ref(false)
const manualError = ref('')
const manualForm = reactive<{
  model_id: string
  display_name: string
  category: ModelCategory | ''
}>({
  model_id: '',
  display_name: '',
  category: 'chat',
})

function openManualModal() {
  if (!currentProvider.value) {
    info('请先新建一个供应商')
    return
  }
  manualError.value = ''
  manualForm.model_id = ''
  manualForm.display_name = ''
  manualForm.category = 'chat'
  manualModal.value = true
}

async function submitManualModel() {
  const providerId = currentProviderId.value
  if (!providerId) return
  if (!manualForm.model_id.trim()) {
    manualError.value = '请输入模型 ID'
    return
  }
  manualSaving.value = true
  manualError.value = ''
  try {
    const res = await addManualModel(providerId, {
      model_id: manualForm.model_id.trim(),
      display_name: manualForm.display_name.trim() || undefined,
      category: manualForm.category || undefined,
    })
    if (res.code !== 0) throw new Error(res.message)
    manualModal.value = false
    success('模型已登记', res.message)
    await loadModels()
    await loadProviders(providerId)
  } catch (err) {
    manualError.value = getErrorMessage(err, '登记失败，请稍后再试')
  } finally {
    manualSaving.value = false
  }
}

/* ---------------- 弹层行为 ---------------- */

const anyOverlayOpen = computed(
  () => providerDrawer.value || Boolean(specModel.value) || manualModal.value || confirmState.open,
)

const isBodyScrollLocked = useScrollLock(document.body)
watchEffect(() => {
  isBodyScrollLocked.value = anyOverlayOpen.value
})

useEventListener(document, 'keydown', (event: KeyboardEvent) => {
  if (event.key !== 'Escape') return
  if (confirmState.open) closeConfirm()
  else if (manualModal.value) manualModal.value = false
  else if (specModel.value) specModel.value = null
  else if (providerDrawer.value) providerDrawer.value = false
})

function formatDateTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  await loadTemplates()
  await loadProviders()
  await loadModels()
})
</script>

<template>
  <div class="page-head">
    <div class="page-head-main">
      <h1 class="page-title">模型服务</h1>
      <p class="page-desc">管理供应商与可用模型。</p>
    </div>
    <div class="page-actions">
      <button
        class="btn btn-secondary"
        type="button"
        :disabled="!currentProvider || syncing"
        @click="syncProvider"
      >
        <AppIcon name="refresh" />{{ syncing ? '同步中…' : '同步模型' }}
      </button>
      <button class="btn btn-primary" type="button" @click="openCreateProvider">
        <AppIcon name="plus" />新增供应商
      </button>
    </div>
  </div>

  <p v-if="pageError" class="field-error mb-3">{{ pageError }}</p>

  <div class="ms-layout">
    <!-- 供应商列表 -->
    <section class="card">
      <div class="card-head">
        <div class="card-head-main"><h3 class="card-title">供应商</h3></div>
        <div class="card-extra">
          <span class="fs-xs subtle"
            >{{ providers.filter((item) => item.enabled).length }} 启用</span
          >
        </div>
      </div>

      <div class="provider-list">
        <button
          v-for="provider in providers"
          :key="provider.id"
          class="provider-item"
          :class="{ 'is-active': provider.id === currentProviderId }"
          type="button"
          @click="selectProvider(provider.id)"
        >
          <span class="p-main">
            <div class="p-name">{{ provider.name }}</div>
            <div class="p-meta">
              {{ provider.template_name }} · {{ provider.model_count }} 个模型
            </div>
          </span>
          <span class="p-side">
            <span class="status-dot" :class="provider.enabled ? 'is-ok' : 'is-idle'" />
          </span>
        </button>

        <p v-if="providersLoading" class="muted fs-sm" style="padding: 20px">加载中…</p>
        <p v-else-if="!providers.length" class="muted fs-sm" style="padding: 20px">
          还没有供应商，先新增一个。
        </p>
      </div>

      <div class="card-foot">
        <button class="btn btn-ghost btn-sm btn-block" type="button" @click="openCreateProvider">
          <AppIcon name="plus" />新增供应商
        </button>
      </div>
    </section>

    <!-- 供应商详情 + 模型 -->
    <section class="card">
      <template v-if="currentProvider">
        <div class="ms-detail-head">
          <div>
            <div class="ms-detail-title">{{ currentProvider.name }}</div>
            <div class="ms-detail-meta">
              {{ currentProvider.protocol }} · {{ currentProvider.base_url }} ·
              {{ currentProvider.api_key_masked || '无需 Key' }} · 同步于
              {{ formatDateTime(currentProvider.last_synced_at) }}
            </div>
          </div>
          <div class="ms-detail-actions">
            <button class="btn btn-secondary btn-sm" type="button" @click="openEditProvider">
              编辑
            </button>
          </div>
        </div>

        <div v-if="currentProvider.last_sync_error" class="alert alert-warning m-4">
          <AppIcon name="alert-triangle" />
          <div>{{ currentProvider.last_sync_error }}</div>
        </div>

        <div class="toolbar">
          <div class="toolbar-left">
            <div class="input-icon search-input">
              <AppIcon name="search" />
              <input v-model="keyword" class="input" placeholder="搜索模型" />
            </div>
            <div class="select-wrap">
              <select v-model="categoryFilter" class="select" style="width: 150px">
                <option value="all">全部分类</option>
                <option v-for="category in categories" :key="category.code" :value="category.code">
                  {{ category.label }}
                </option>
              </select>
            </div>
          </div>
          <div class="toolbar-right">
            <button class="btn btn-ghost btn-sm" type="button" @click="openManualModal">
              <AppIcon name="plus" />手动登记
            </button>
            <button class="btn btn-ghost btn-sm" type="button" @click="removeProvider">
              <AppIcon name="trash" />删除配置
            </button>
          </div>
        </div>

        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>模型</th>
                <th>分类</th>
                <th>来源</th>
                <th>启用</th>
                <th>同步时间</th>
                <th class="th-actions">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="model in filteredModels" :key="model.id">
                <td>
                  <div class="cell-main">
                    <span class="cell-icon"><AppIcon name="cpu" /></span>
                    <div>
                      <div class="cell-title">{{ model.display_name }}</div>
                      <div class="cell-sub mono">{{ model.model_id }}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span class="badge" :class="CATEGORY_BADGE[model.category] || 'badge-neutral'">
                    {{ model.category_label }}
                  </span>
                </td>
                <td>
                  <span class="fs-sm muted">{{ model.source === 'manual' ? '手动' : '自动' }}</span>
                </td>
                <td>
                  <label class="switch">
                    <input
                      type="checkbox"
                      :checked="model.enabled"
                      @change="toggleModel(model, $event)"
                    />
                    <span class="switch-track" />
                  </label>
                </td>
                <td class="num">{{ formatDateTime(model.synced_at) }}</td>
                <td>
                  <div class="cell-actions">
                    <button
                      class="icon-btn"
                      type="button"
                      title="参数规格"
                      @click="openSpec(model)"
                    >
                      <AppIcon name="sliders" />
                    </button>
                    <button class="icon-btn" type="button" title="删除" @click="removeModel(model)">
                      <AppIcon name="trash" />
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="modelsLoading">
                <td colspan="6">
                  <div class="empty" style="padding: 28px"><p>加载中…</p></div>
                </td>
              </tr>
              <tr v-else-if="!filteredModels.length">
                <td colspan="6">
                  <div class="empty" style="padding: 40px 24px">
                    <span class="empty-icon"><AppIcon name="cpu" /></span>
                    <h3>没有匹配的模型</h3>
                    <p>可以重新同步供应商模型，或手动登记模型。</p>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="table-foot">
          <span>共 {{ filteredModels.length }} 个模型</span>
          <span class="spacer" />
          <span class="fs-xs subtle">模型列表在线同步后自动分类</span>
        </div>
      </template>

      <div v-else class="empty" style="padding: 64px 24px">
        <span class="empty-icon"><AppIcon name="box" /></span>
        <h3>还没有供应商</h3>
        <p>新增一个供应商后，即可同步并管理可用模型。</p>
        <button class="btn btn-primary btn-sm" type="button" @click="openCreateProvider">
          新增供应商
        </button>
      </div>
    </section>
  </div>

  <p class="quiet-note">API Key 加密存储，页面只展示掩码；统一模型调用网关在后台运行。</p>

  <!-- 新增 / 编辑供应商 -->
  <Teleport to="body">
    <div v-if="providerDrawer" class="drawer">
      <div class="drawer-backdrop" @click="providerDrawer = false" />
      <div class="drawer-panel">
        <div class="drawer-head">
          <div>
            <h3 class="modal-title">
              {{ providerMode === 'create' ? '新增供应商' : '编辑供应商' }}
            </h3>
            <p class="modal-sub">保存后自动尝试同步模型列表</p>
          </div>
          <button class="icon-btn" type="button" aria-label="关闭" @click="providerDrawer = false">
            <AppIcon name="x" />
          </button>
        </div>

        <div class="drawer-body">
          <div class="field">
            <label class="field-label" for="provider-template">供应商模板</label>
            <div class="select-wrap">
              <select
                id="provider-template"
                v-model="providerForm.template_code"
                class="select"
                :disabled="providerMode === 'edit'"
                @change="onTemplateChange"
              >
                <option v-for="template in templates" :key="template.code" :value="template.code">
                  {{ template.name }}（{{ template.protocol }}）
                </option>
              </select>
            </div>
            <p v-if="selectedTemplate" class="field-help">{{ selectedTemplate.description }}</p>
          </div>

          <div class="field mt-4">
            <label class="field-label" for="provider-name">配置名称</label>
            <input
              id="provider-name"
              v-model="providerForm.name"
              class="input"
              placeholder="例如：我的 DeepSeek"
            />
          </div>

          <div class="field mt-4">
            <label class="field-label" for="provider-base-url">接口地址</label>
            <input
              id="provider-base-url"
              v-model="providerForm.base_url"
              class="input"
              placeholder="https://api.deepseek.com/v1"
            />
          </div>

          <div class="field mt-4">
            <label class="field-label" for="provider-api-key">API Key</label>
            <input
              id="provider-api-key"
              v-model="providerForm.api_key"
              class="input"
              type="password"
              :placeholder="providerMode === 'edit' ? '留空表示不修改' : '输入供应商 API Key'"
              autocomplete="off"
            />
            <p class="field-help">加密保存，接口只返回掩码。</p>
          </div>

          <div v-if="providerMode === 'edit'" class="field mt-4">
            <label class="field-label">启用状态</label>
            <label class="switch">
              <input v-model="providerForm.enabled" type="checkbox" />
              <span class="switch-track" />
            </label>
          </div>

          <p v-if="providerError" class="field-error mt-4">{{ providerError }}</p>
        </div>

        <div class="drawer-foot">
          <button class="btn btn-secondary" type="button" @click="providerDrawer = false">
            取消
          </button>
          <button class="btn" type="button" :disabled="providerSaving" @click="submitProvider">
            {{ providerSaving ? '保存中…' : '保存并同步' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 参数规格 -->
  <Teleport to="body">
    <div v-if="specModel" class="drawer">
      <div class="drawer-backdrop" @click="specModel = null" />
      <div class="drawer-panel">
        <div class="drawer-head">
          <div>
            <h3 class="modal-title">{{ specModel.display_name }}</h3>
            <p class="modal-sub mono">{{ specModel.model_id }}</p>
          </div>
          <button class="icon-btn" type="button" aria-label="关闭" @click="specModel = null">
            <AppIcon name="x" />
          </button>
        </div>
        <div class="drawer-body">
          <table class="table param-spec-table">
            <thead>
              <tr>
                <th>参数</th>
                <th>类型</th>
                <th>范围</th>
                <th>默认值</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in specRows" :key="row.name">
                <td class="mono">{{ row.name }}</td>
                <td>
                  {{ row.type
                  }}<span v-if="row.required === '必填'" class="param-required">必填</span>
                </td>
                <td>{{ row.range }}</td>
                <td class="mono">{{ row.default }}</td>
                <td class="fs-sm muted">{{ row.description }}</td>
              </tr>
              <tr v-if="!specRows.length">
                <td colspan="5">
                  <div class="empty" style="padding: 24px"><p>该模型没有可配置参数</p></div>
                </td>
              </tr>
            </tbody>
          </table>
          <p class="quiet-note">
            调用时按参数白名单校验，非法参数整单拒绝；model / messages 由系统控制。
          </p>
        </div>
        <div class="drawer-foot">
          <button class="btn btn-secondary btn-block" type="button" @click="specModel = null">
            关闭
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 手动登记模型 -->
  <Teleport to="body">
    <div v-if="manualModal" class="modal">
      <div class="modal-backdrop" @click="manualModal = false" />
      <div class="modal-card modal-sm">
        <div class="modal-head">
          <div>
            <h3 class="modal-title">手动登记模型</h3>
            <p class="modal-sub">供应商未返回模型列表时使用</p>
          </div>
          <button class="icon-btn" type="button" aria-label="关闭" @click="manualModal = false">
            <AppIcon name="x" />
          </button>
        </div>
        <div class="modal-body">
          <div class="field">
            <label class="field-label" for="manual-model-id">模型 ID</label>
            <input
              id="manual-model-id"
              v-model="manualForm.model_id"
              class="input"
              placeholder="例如 fast-chat-1"
            />
          </div>
          <div class="field mt-4">
            <label class="field-label" for="manual-model-name">显示名称</label>
            <input
              id="manual-model-name"
              v-model="manualForm.display_name"
              class="input"
              placeholder="默认使用模型 ID"
            />
          </div>
          <div class="field mt-4">
            <label class="field-label" for="manual-model-category">分类</label>
            <div class="select-wrap">
              <select id="manual-model-category" v-model="manualForm.category" class="select">
                <option value="">自动识别</option>
                <option v-for="category in categories" :key="category.code" :value="category.code">
                  {{ category.label }}
                </option>
              </select>
            </div>
          </div>
          <p v-if="manualError" class="field-error mt-4">{{ manualError }}</p>
        </div>
        <div class="modal-foot">
          <button class="btn btn-secondary" type="button" @click="manualModal = false">取消</button>
          <button class="btn" type="button" :disabled="manualSaving" @click="submitManualModel">
            {{ manualSaving ? '登记中…' : '登记' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 删除确认 -->
  <Teleport to="body">
    <div v-if="confirmState.open" class="modal">
      <div class="modal-backdrop" @click="closeConfirm" />
      <div class="modal-card modal-sm">
        <div class="modal-head">
          <div>
            <h3 class="modal-title">{{ confirmState.title }}</h3>
            <p class="modal-sub">{{ confirmState.message }}</p>
          </div>
          <button class="icon-btn" type="button" aria-label="关闭" @click="closeConfirm">
            <AppIcon name="x" />
          </button>
        </div>
        <div class="modal-foot">
          <button class="btn btn-secondary" type="button" @click="closeConfirm">取消</button>
          <button class="btn btn-danger" type="button" @click="runConfirm">确认删除</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
