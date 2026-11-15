<script setup lang="ts">
import { computed, markRaw, onBeforeUnmount, reactive, ref, shallowRef, type Component } from 'vue'
import type { Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ConnectionMode,
  VueFlow,
  useVueFlow,
  type Connection,
  type Edge,
  type Node,
} from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { useEventListener, useIntervalFn } from '@vueuse/core'
import AppIcon from '@/components/ui/AppIcon.vue'
import WorkflowNode from '@/components/workflow/WorkflowNode.vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useToastStore } from '@/stores/toast'
import {
  addWorkflowMember,
  addWorkflowNode,
  addWorkflowRelation,
  deleteWorkflowNode,
  deleteWorkflowRelation,
  exportWorkflow,
  getNodeTypeMeta,
  getWorkflow,
  importWorkflow,
  listWorkflowEvents,
  removeWorkflowMember,
  runWorkflow,
  updateWorkflowNode,
  type NodeMeta,
  type NodeParamSpec,
  type RunResult,
  type WorkflowDocument,
  type WorkflowMember,
  type WorkflowNodeState,
  type WorkflowRelation,
  type WorkflowState,
} from '@/api/workflow'
import { getErrorMessage } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const theme = useThemeStore()
const toast = useToastStore()

const workflowId = computed(() => Number(route.params.id))

const workflow = ref<WorkflowState['workflow'] | null>(null)
const members = ref<WorkflowMember[]>([])
const nodes = ref([]) as Ref<Node[]>
const edges = ref([]) as Ref<Edge[]>
const nodeTypes = shallowRef<Record<string, Component>>({})
const nodeCatalog = ref<string[]>([])
const nodeMetas = reactive<Record<string, NodeMeta>>({})
const metaLoading = reactive<Record<string, boolean>>({})
const lastEventSeq = ref(0)
const loading = ref(true)
const pageError = ref('')
const syncing = ref(false)

const selectedNodeId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)
const selectedRelationId = ref<number | null>(null)

const paletteOpen = ref(false)
const configDrawer = ref(false)
const editingNodeKey = ref<string | null>(null)
const editingVersion = ref(0)
const configForm = reactive<Record<string, unknown>>({})
const nodeNameForm = ref('')
const configError = ref('')
const savingConfig = ref(false)

const membersModal = ref(false)
const memberForm = reactive({ username: '', role: 'editor' as 'editor' | 'viewer' })
const addingMember = ref(false)

const runModal = ref(false)
const running = ref(false)
const runResult = ref<RunResult | null>(null)

const importInput = ref<HTMLInputElement | null>(null)
const importing = ref(false)

const { addEdges } = useVueFlow()

const canEdit = computed(
  () => workflow.value?.role === 'owner' || workflow.value?.role === 'editor',
)
const patternColor = computed(() => (theme.isDark ? '#24314d' : '#dbe3f2'))
const editingMeta = computed<NodeMeta | null>(() => {
  if (!editingNodeKey.value) return null
  return nodeMetas[editingNodeKey.value] ?? null
})

/* ---------------- 数据转换 ---------------- */
function buildNode(state: WorkflowNodeState): Node {
  return {
    id: state.key,
    type: state.node_type,
    position: { x: state.position.x, y: state.position.y },
    data: {
      name: state.name,
      nodeType: state.node_type,
      config: state.config,
      version: state.version,
      meta: nodeMetas[state.node_type],
    },
  }
}

function buildEdge(relation: WorkflowRelation): Edge {
  return {
    id: `e-${relation.id}`,
    type: 'smoothstep',
    source: relation.source_key,
    sourceHandle: relation.source_port,
    target: relation.target_key,
    targetHandle: relation.target_port,
    data: { relationId: relation.id },
  }
}

async function ensureMeta(nodeType: string) {
  if (nodeMetas[nodeType] || metaLoading[nodeType]) return
  metaLoading[nodeType] = true
  try {
    const res = await getNodeTypeMeta(nodeType)
    if (res.code === 0) nodeMetas[nodeType] = res.data.meta
  } catch {
    // 元数据加载失败时节点仍可展示基础信息
  } finally {
    metaLoading[nodeType] = false
  }
}

async function applyState(state: WorkflowState) {
  workflow.value = state.workflow
  members.value = state.members ?? []
  nodeCatalog.value = state.node_types
  lastEventSeq.value = Math.max(lastEventSeq.value, state.last_event_seq || 0)
  nodeTypes.value = Object.fromEntries(
    state.node_types.map((type) => [type, markRaw(WorkflowNode)]),
  ) as Record<string, Component>
  const usedTypes = new Set(state.nodes.map((node) => node.node_type))
  await Promise.all([...usedTypes].map((type) => ensureMeta(type)))
  nodes.value = state.nodes.map(buildNode)
  edges.value = state.relations.map(buildEdge)
  selectedNodeId.value = null
  selectedEdgeId.value = null
  selectedRelationId.value = null
}

async function refresh(silent = false) {
  if (!silent) syncing.value = true
  try {
    const res = await getWorkflow(workflowId.value)
    if (res.code !== 0) throw new Error(res.message)
    await applyState(res.data)
  } catch (err) {
    if (!silent) pageError.value = getErrorMessage(err, '加载工作流失败')
  } finally {
    syncing.value = false
    loading.value = false
  }
}

/* ---------------- 轮询同步 ---------------- */
let polling = false
const { resume: startPolling } = useIntervalFn(pollEvents, 2000, { immediate: false })

async function pollEvents() {
  if (polling || document.hidden || !workflow.value) return
  polling = true
  try {
    const res = await listWorkflowEvents(workflowId.value, lastEventSeq.value)
    if (res.code !== 0) return
    const events = res.data.events
    lastEventSeq.value = Math.max(
      lastEventSeq.value,
      res.data.last_event_seq || 0,
      ...events.map((item) => item.id),
    )
    const remoteEvents = events.filter((item) => item.actor_id !== auth.userId)
    if (remoteEvents.length) {
      await refresh(true)
      toast.info('已同步协作者的修改')
    }
  } catch {
    // 网络抖动时下一轮继续
  } finally {
    polling = false
  }
}

/* ---------------- 节点操作 ---------------- */
function togglePalette() {
  paletteOpen.value = !paletteOpen.value
  if (paletteOpen.value) {
    void Promise.all(nodeCatalog.value.map((type) => ensureMeta(type)))
  }
}

function defaultConfig(meta: NodeMeta): Record<string, unknown> {
  const config: Record<string, unknown> = {}
  for (const param of meta.params) {
    if (param.default !== undefined) {
      if (param.type === 'json') {
        config[param.key] =
          typeof param.default === 'string' ? param.default : JSON.stringify(param.default)
      } else {
        config[param.key] = param.default
      }
    } else if (param.type === 'json') {
      config[param.key] = '{}'
    } else if (param.type === 'boolean') {
      config[param.key] = false
    } else {
      config[param.key] = ''
    }
  }
  return config
}

async function addNode(nodeType: string) {
  if (!canEdit.value) return
  try {
    await ensureMeta(nodeType)
    const meta = nodeMetas[nodeType]
    const index = nodes.value.length
    const res = await addWorkflowNode(workflowId.value, {
      node_type: nodeType,
      name: meta?.name || nodeType,
      position: { x: 80 + (index % 3) * 280, y: 80 + Math.floor(index / 3) * 180 },
      config: meta ? defaultConfig(meta) : {},
    })
    if (res.code !== 0) throw new Error(res.message)
    await ensureMeta(nodeType)
    nodes.value.push(buildNode(res.data.node))
    paletteOpen.value = false
    toast.success(`已添加节点：${res.data.node.name || nodeType}`)
  } catch (err) {
    toast.error('添加节点失败', getErrorMessage(err))
  }
}

function onNodeDragStop(payload: any) {
  const node: Node | undefined = payload?.node
  if (!node || !canEdit.value) return
  void savePosition(node)
}

async function savePosition(node: Node) {
  try {
    const res = await updateWorkflowNode(workflowId.value, node.id, {
      base_version: Number(node.data?.version || 1),
      position: { x: node.position.x, y: node.position.y },
    })
    if (res.code !== 0) throw new Error(res.message)
    node.data = { ...node.data, version: res.data.node.version }
  } catch (err) {
    toast.warning('节点位置保存失败', getErrorMessage(err))
    await refresh(true)
  }
}

function openConfig(payload: any) {
  const node: Node | undefined = payload?.node
  if (!node) return
  selectedNodeId.value = node.id
  selectedEdgeId.value = null
  selectedRelationId.value = null
  editingNodeKey.value = String(node.data?.nodeType || '')
  const state = nodes.value.find((item) => item.id === node.id)
  if (!state) return
  editingNodeKey.value = String(state.data?.nodeType || '')
  editingVersion.value = Number(state.data?.version || 1)
  nodeNameForm.value = String(state.data?.name || '')
  configError.value = ''
  const meta = nodeMetas[editingNodeKey.value]
  Object.keys(configForm).forEach((key) => delete configForm[key])
  for (const param of meta?.params || []) {
    const raw = (state.data?.config || {})[param.key]
    if (param.type === 'json') {
      configForm[param.key] =
        raw === undefined ? '{}' : typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2)
    } else if (param.type === 'boolean') {
      configForm[param.key] = Boolean(raw)
    } else {
      configForm[param.key] = raw ?? param.default ?? ''
    }
  }
  configDrawer.value = true
}

function coerceParam(param: NodeParamSpec, raw: unknown): unknown {
  if (param.type === 'json') {
    if (raw === '' || raw === undefined) return {}
    if (typeof raw === 'object') return raw
    try {
      return JSON.parse(String(raw))
    } catch (err) {
      throw new Error(`参数「${param.label}」不是合法 JSON：${(err as Error).message}`, {
        cause: err,
      })
    }
  }
  if (param.type === 'number') {
    if (raw === '' || raw === undefined || raw === null) return undefined
    const value = Number(raw)
    if (Number.isNaN(value)) throw new Error(`参数「${param.label}」必须是数字`)
    return value
  }
  if (param.type === 'boolean') return Boolean(raw)
  return raw === undefined ? '' : String(raw)
}

async function saveConfig() {
  if (!canEdit.value || !editingNodeKey.value) return
  configError.value = ''
  const meta = editingMeta.value
  if (!meta) return
  const config: Record<string, unknown> = {}
  try {
    for (const param of meta.params) {
      const value = coerceParam(param, configForm[param.key])
      if (param.required && (value === undefined || value === '' || value === null)) {
        throw new Error(`参数「${param.label}」不能为空`)
      }
      if (value !== undefined) config[param.key] = value
    }
  } catch (err) {
    configError.value = getErrorMessage(err)
    return
  }

  savingConfig.value = true
  try {
    const targetKey = selectedNodeId.value
    if (!targetKey) return
    const res = await updateWorkflowNode(workflowId.value, targetKey, {
      base_version: editingVersion.value,
      name: nodeNameForm.value.trim() || meta.name,
      config,
    })
    if (res.code !== 0) throw new Error(res.message)
    const target = nodes.value.find((item) => item.id === targetKey)
    if (target) {
      target.data = {
        ...target.data,
        name: res.data.node.name,
        config: res.data.node.config,
        version: res.data.node.version,
      }
    }
    editingVersion.value = res.data.node.version
    configDrawer.value = false
    toast.success('节点参数已保存')
  } catch (err) {
    configError.value = getErrorMessage(err, '保存失败，请稍后再试')
  } finally {
    savingConfig.value = false
  }
}

async function onConnect(connection: Connection) {
  if (!canEdit.value) return
  if (!connection.source || !connection.target) return
  try {
    const res = await addWorkflowRelation(workflowId.value, {
      source_key: connection.source,
      source_port: connection.sourceHandle || 'out',
      target_key: connection.target,
      target_port: connection.targetHandle || 'in',
    })
    if (res.code !== 0) throw new Error(res.message)
    addEdges([buildEdge(res.data.relation)])
    toast.success('连线已添加')
  } catch (err) {
    toast.error('连线失败', getErrorMessage(err))
  }
}

function onNodeClick(payload: any) {
  const node: Node | undefined = payload?.node
  if (!node) return
  selectedNodeId.value = node.id
  selectedEdgeId.value = null
  selectedRelationId.value = null
  openConfig(payload)
}

function onEdgeClick(payload: any) {
  const edge: Edge | undefined = payload?.edge
  if (!edge) return
  selectedEdgeId.value = edge.id
  selectedRelationId.value = Number(edge.data?.relationId || 0) || null
  selectedNodeId.value = null
}

function clearSelection() {
  selectedNodeId.value = null
  selectedEdgeId.value = null
  selectedRelationId.value = null
}

async function deleteSelection() {
  if (!canEdit.value) return
  try {
    if (selectedNodeId.value) {
      const key = selectedNodeId.value
      const res = await deleteWorkflowNode(workflowId.value, key)
      if (res.code !== 0) throw new Error(res.message)
      nodes.value = nodes.value.filter((node) => node.id !== key)
      edges.value = edges.value.filter((edge) => edge.source !== key && edge.target !== key)
      selectedNodeId.value = null
      configDrawer.value = false
      toast.success('节点已删除')
    } else if (selectedRelationId.value) {
      const relationId = selectedRelationId.value
      const res = await deleteWorkflowRelation(workflowId.value, relationId)
      if (res.code !== 0) throw new Error(res.message)
      edges.value = edges.value.filter((edge) => Number(edge.data?.relationId) !== relationId)
      selectedEdgeId.value = null
      selectedRelationId.value = null
      toast.success('连线已删除')
    }
  } catch (err) {
    toast.error('删除失败', getErrorMessage(err))
  }
}

/* ---------------- 运行 ---------------- */
async function run() {
  if (!canEdit.value || running.value) return
  running.value = true
  try {
    const res = await runWorkflow(workflowId.value)
    if (res.code !== 0) throw new Error(res.message)
    runResult.value = res.data
    runModal.value = true
  } catch (err) {
    toast.error('运行失败', getErrorMessage(err))
  } finally {
    running.value = false
  }
}

/* ---------------- 导入 / 导出 ---------------- */
function triggerImport() {
  importInput.value?.click()
}

async function onImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!window.confirm('导入会覆盖当前工作流的节点与连线，是否继续？')) return

  importing.value = true
  try {
    const text = await file.text()
    const document = JSON.parse(text) as WorkflowDocument
    const res = await importWorkflow(workflowId.value, document)
    if (res.code !== 0) throw new Error(res.message)
    await applyState(res.data)
    toast.success('工作流已导入')
  } catch (err) {
    toast.error('导入失败', getErrorMessage(err))
  } finally {
    importing.value = false
  }
}

async function onExport() {
  try {
    const res = await exportWorkflow(workflowId.value)
    if (res.code !== 0) throw new Error(res.message)
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${workflow.value?.name || 'workflow'}.json`
    link.click()
    URL.revokeObjectURL(url)
    toast.success('已导出 JSON')
  } catch (err) {
    toast.error('导出失败', getErrorMessage(err))
  }
}

/* ---------------- 成员 ---------------- */
async function openMembers() {
  membersModal.value = true
  await refreshMembers()
}

async function refreshMembers() {
  try {
    const res = await getWorkflow(workflowId.value)
    if (res.code === 0) {
      workflow.value = res.data.workflow
      members.value = res.data.members ?? []
    }
  } catch {
    // 忽略
  }
}

async function submitMember() {
  if (!memberForm.username.trim()) return
  addingMember.value = true
  try {
    const res = await addWorkflowMember(workflowId.value, {
      username: memberForm.username.trim(),
      role: memberForm.role,
    })
    if (res.code !== 0) throw new Error(res.message)
    memberForm.username = ''
    toast.success('已添加协作者')
    await refresh(true)
  } catch (err) {
    toast.error('添加协作者失败', getErrorMessage(err))
  } finally {
    addingMember.value = false
  }
}

async function removeMember(member: WorkflowMember) {
  try {
    const res = await removeWorkflowMember(workflowId.value, member.user_id)
    if (res.code !== 0) throw new Error(res.message)
    toast.success('已移除协作者')
    await refresh(true)
  } catch (err) {
    toast.error('移除失败', getErrorMessage(err))
  }
}

/* ---------------- 键盘 ---------------- */
useEventListener(document, 'keydown', (event: KeyboardEvent) => {
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
  if (event.key === 'Escape') {
    paletteOpen.value = false
    configDrawer.value = false
    membersModal.value = false
    runModal.value = false
    return
  }
  if (
    (event.key === 'Delete' || event.key === 'Backspace') &&
    (selectedNodeId.value || selectedRelationId.value)
  ) {
    event.preventDefault()
    void deleteSelection()
  }
})

onBeforeUnmount(() => {
  // 清理下载与弹层状态（轮询由 useIntervalFn 自动停止）
})

/* ---------------- 初始化 ---------------- */
if (!Number.isFinite(workflowId.value) || workflowId.value <= 0) {
  pageError.value = '无效的工作流 ID'
  loading.value = false
} else {
  void refresh().then(() => {
    startPolling()
  })
}
</script>

<template>
  <div class="wf-editor">
    <div class="page-head">
      <div class="page-head-main">
        <div class="wf-title-row">
          <button
            class="icon-btn"
            type="button"
            title="返回列表"
            @click="router.push('/workflows')"
          >
            <AppIcon name="arrow-left" />
          </button>
          <h1 class="page-title wf-title">{{ workflow?.name || '工作流' }}</h1>
          <span v-if="workflow" class="badge badge-neutral">
            {{
              workflow.role === 'owner' ? '创建者' : workflow.role === 'editor' ? '可编辑' : '只读'
            }}
          </span>
        </div>
        <p class="page-desc">
          无限画布 · 拖拽节点连线 · 协作者同步
          <span v-if="syncing" class="subtle">（同步中…）</span>
        </p>
      </div>
      <div class="page-actions">
        <button
          class="btn btn-secondary btn-sm"
          type="button"
          :disabled="!canEdit"
          @click="deleteSelection"
        >
          <AppIcon name="trash" />删除选中
        </button>
        <button
          class="btn btn-secondary btn-sm"
          type="button"
          :disabled="importing"
          @click="triggerImport"
        >
          <AppIcon name="upload" />导入
        </button>
        <button class="btn btn-secondary btn-sm" type="button" @click="onExport">
          <AppIcon name="download" />导出
        </button>
        <button class="btn btn-secondary btn-sm" type="button" @click="openMembers">
          <AppIcon name="user" />协作
        </button>
        <button
          class="btn btn-primary btn-sm"
          type="button"
          :disabled="!canEdit || running"
          @click="run"
        >
          <AppIcon name="play" />{{ running ? '运行中…' : '运行' }}
        </button>
      </div>
    </div>

    <p v-if="pageError" class="field-error mb-3">{{ pageError }}</p>
    <p v-else-if="loading" class="muted mb-3">加载工作流…</p>

    <div v-else class="wf-canvas-shell">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :node-types="nodeTypes"
        :connection-mode="ConnectionMode.Strict"
        :snap-to-grid="true"
        :snap-grid="[16, 16]"
        :min-zoom="0.25"
        :max-zoom="2"
        :default-edge-options="{ type: 'smoothstep' }"
        fit-view-on-init
        @connect="onConnect"
        @node-drag-stop="onNodeDragStop"
        @node-click="onNodeClick"
        @edge-click="onEdgeClick"
        @pane-click="clearSelection"
      >
        <Background :gap="18" :pattern-color="patternColor" />
        <Controls />
        <MiniMap />
      </VueFlow>

      <div class="wf-canvas-toolbar">
        <button
          class="btn btn-primary btn-sm"
          type="button"
          :disabled="!canEdit"
          @click="togglePalette"
        >
          <AppIcon name="plus" />添加节点
        </button>
      </div>

      <aside v-if="paletteOpen" class="wf-palette">
        <div class="wf-palette-head">
          <strong>节点目录</strong>
          <button class="icon-btn" type="button" @click="paletteOpen = false">
            <AppIcon name="x" />
          </button>
        </div>
        <p class="wf-palette-hint">目录先加载，展开后才读取具体节点参数。</p>
        <button
          v-for="type in nodeCatalog"
          :key="type"
          class="wf-palette-item"
          type="button"
          @click="addNode(type)"
        >
          <span class="wf-palette-icon"><AppIcon name="workflow" /></span>
          <span class="wf-palette-main">
            <strong>{{ nodeMetas[type]?.name || type }}</strong>
            <small>{{ nodeMetas[type]?.description || '加载中…' }}</small>
          </span>
          <AppIcon name="plus" class="icon-sm" />
        </button>
      </aside>

      <div class="wf-canvas-status">
        <span class="status-dot is-ok" />
        {{ members.length }} 人可协作 · 事件 #{{ lastEventSeq }}
      </div>
    </div>

    <input
      ref="importInput"
      type="file"
      accept="application/json,.json"
      hidden
      @change="onImportFile"
    />

    <!-- 节点配置抽屉 -->
    <Teleport to="body">
      <div v-if="configDrawer" class="drawer">
        <div class="drawer-backdrop" @click="configDrawer = false" />
        <div class="drawer-panel">
          <div class="drawer-head">
            <div>
              <h3 class="modal-title">{{ editingMeta?.name || '节点配置' }}</h3>
              <p class="modal-sub">{{ editingNodeKey }} · 版本 v{{ editingVersion }}</p>
            </div>
            <button class="icon-btn" type="button" @click="configDrawer = false">
              <AppIcon name="x" />
            </button>
          </div>
          <div class="drawer-body">
            <div class="field">
              <label class="field-label" for="node-name">节点名称</label>
              <input id="node-name" v-model="nodeNameForm" class="input" />
            </div>
            <div v-for="param in editingMeta?.params || []" :key="param.key" class="field mt-4">
              <label class="field-label" :for="`param-${param.key}`">
                {{ param.label }}<span v-if="param.required" class="param-required">必填</span>
              </label>
              <textarea
                v-if="param.type === 'json' || param.type === 'textarea'"
                :id="`param-${param.key}`"
                v-model="configForm[param.key] as string"
                class="textarea"
                :rows="param.type === 'json' ? 5 : 4"
              />
              <select
                v-else-if="param.type === 'select'"
                :id="`param-${param.key}`"
                v-model="configForm[param.key]"
                class="select"
              >
                <option
                  v-for="option in param.options || []"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
              <label v-else-if="param.type === 'boolean'" class="switch">
                <input v-model="configForm[param.key]" type="checkbox" />
                <span class="switch-track" />
              </label>
              <input
                v-else
                :id="`param-${param.key}`"
                v-model="configForm[param.key]"
                class="input"
                :type="param.type === 'number' ? 'number' : 'text'"
              />
              <p v-if="param.help" class="field-help">{{ param.help }}</p>
            </div>
            <p v-if="configError" class="field-error mt-4">{{ configError }}</p>
          </div>
          <div class="drawer-foot">
            <button class="btn btn-secondary" type="button" @click="configDrawer = false">
              取消
            </button>
            <button
              class="btn"
              type="button"
              :disabled="!canEdit || savingConfig"
              @click="saveConfig"
            >
              {{ savingConfig ? '保存中…' : '保存参数' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 协作者 -->
    <Teleport to="body">
      <div v-if="membersModal" class="modal">
        <div class="modal-backdrop" @click="membersModal = false" />
        <div class="modal-card modal-sm">
          <div class="modal-head">
            <div>
              <h3 class="modal-title">协作成员</h3>
              <p class="modal-sub">被邀请成员可同时编辑；变更实时同步。</p>
            </div>
            <button class="icon-btn" type="button" @click="membersModal = false">
              <AppIcon name="x" />
            </button>
          </div>
          <div class="modal-body">
            <div v-for="member in members" :key="member.user_id" class="wf-member-row">
              <span class="avatar">{{ member.username.slice(0, 1).toUpperCase() }}</span>
              <span class="wf-member-name">{{ member.username }}</span>
              <span class="badge badge-neutral">
                {{
                  member.role === 'owner' ? '创建者' : member.role === 'editor' ? '可编辑' : '只读'
                }}
              </span>
              <button
                v-if="workflow?.role === 'owner' && member.role !== 'owner'"
                class="icon-btn"
                type="button"
                title="移除"
                @click="removeMember(member)"
              >
                <AppIcon name="trash" />
              </button>
            </div>
            <div v-if="workflow?.role === 'owner'" class="wf-member-add">
              <input v-model="memberForm.username" class="input" placeholder="按用户名邀请" />
              <select v-model="memberForm.role" class="select" style="width: 110px">
                <option value="editor">可编辑</option>
                <option value="viewer">只读</option>
              </select>
              <button
                class="btn btn-sm"
                type="button"
                :disabled="addingMember"
                @click="submitMember"
              >
                邀请
              </button>
            </div>
            <p v-else class="quiet-note">只有创建者可以邀请成员。</p>
          </div>
          <div class="modal-foot">
            <button class="btn btn-secondary btn-block" type="button" @click="membersModal = false">
              关闭
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 运行结果 -->
    <Teleport to="body">
      <div v-if="runModal" class="modal">
        <div class="modal-backdrop" @click="runModal = false" />
        <div class="modal-card">
          <div class="modal-head">
            <div>
              <h3 class="modal-title">运行结果</h3>
              <p class="modal-sub">
                {{ runResult?.status === 'success' ? '执行成功' : '执行失败' }} ·
                {{ runResult?.duration_ms }}ms
              </p>
            </div>
            <button class="icon-btn" type="button" @click="runModal = false">
              <AppIcon name="x" />
            </button>
          </div>
          <div class="modal-body">
            <p v-if="runResult?.error" class="field-error mb-3">{{ runResult.error }}</p>
            <div
              v-for="(step, index) in runResult?.steps || []"
              :key="step.node_key"
              class="wf-run-step"
            >
              <div class="wf-run-step-head">
                <span class="status-dot" :class="step.status === 'success' ? 'is-ok' : 'is-err'" />
                <strong>{{ index + 1 }}. {{ step.name }}</strong>
                <span class="subtle fs-xs">{{ step.node_type }} · {{ step.duration_ms }}ms</span>
              </div>
              <p v-if="step.error" class="field-error">{{ step.error }}</p>
              <pre v-if="step.output" class="wf-json">{{
                JSON.stringify(step.output, null, 2)
              }}</pre>
            </div>
          </div>
          <div class="modal-foot">
            <button class="btn btn-secondary btn-block" type="button" @click="runModal = false">
              关闭
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
