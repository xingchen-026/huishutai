<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/ui/AppIcon.vue'
import { useToastStore } from '@/stores/toast'
import { createWorkflow, deleteWorkflow, listWorkflows, type WorkflowSummary } from '@/api/workflow'
import { getErrorMessage } from '@/utils/error'

const router = useRouter()
const toast = useToastStore()

const workflows = ref<WorkflowSummary[]>([])
const loading = ref(true)
const pageError = ref('')
const createOpen = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = reactive({ name: '', description: '' })

async function load() {
  loading.value = true
  pageError.value = ''
  try {
    const res = await listWorkflows()
    if (res.code !== 0) throw new Error(res.message)
    workflows.value = res.data.workflows
  } catch (err) {
    pageError.value = getErrorMessage(err, '加载工作流失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.name = ''
  createForm.description = ''
  createError.value = ''
  createOpen.value = true
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    createError.value = '请输入工作流名称'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const res = await createWorkflow({
      name: createForm.name.trim(),
      description: createForm.description.trim(),
    })
    if (res.code !== 0) throw new Error(res.message)
    createOpen.value = false
    toast.success('工作流已创建')
    await router.push(`/workflows/${res.data.workflow.id}`)
  } catch (err) {
    createError.value = getErrorMessage(err, '创建失败，请稍后再试')
  } finally {
    creating.value = false
  }
}

async function remove(workflow: WorkflowSummary) {
  if (!window.confirm(`确定删除工作流「${workflow.name}」吗？`)) return
  try {
    const res = await deleteWorkflow(workflow.id)
    if (res.code !== 0) throw new Error(res.message)
    toast.success('工作流已删除')
    await load()
  } catch (err) {
    toast.error('删除失败', getErrorMessage(err))
  }
}

function formatTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<template>
  <div class="page-head">
    <div class="page-head-main">
      <h1 class="page-title">工作流</h1>
      <p class="page-desc">用无限画布编排 AI 与 HTTP 能力。</p>
    </div>
    <div class="page-actions">
      <button class="btn btn-primary" type="button" @click="openCreate">
        <AppIcon name="plus" />新建工作流
      </button>
    </div>
  </div>

  <p v-if="pageError" class="field-error mb-3">{{ pageError }}</p>
  <p v-else-if="loading" class="muted mb-3">加载中…</p>

  <div v-else-if="workflows.length" class="wf-list-grid">
    <button
      v-for="workflow in workflows"
      :key="workflow.id"
      class="card wf-list-card"
      type="button"
      @click="router.push(`/workflows/${workflow.id}`)"
    >
      <div class="wf-list-head">
        <span class="wf-list-icon"><AppIcon name="workflow" /></span>
        <span class="wf-list-name">{{ workflow.name }}</span>
        <span class="badge" :class="workflow.role === 'owner' ? 'badge-info' : 'badge-neutral'">
          {{
            workflow.role === 'owner' ? '创建者' : workflow.role === 'editor' ? '可编辑' : '只读'
          }}
        </span>
      </div>
      <p class="wf-list-desc">{{ workflow.description || '暂无描述' }}</p>
      <div class="wf-list-meta">
        <span>{{ workflow.node_count ?? 0 }} 个节点</span>
        <span>更新于 {{ formatTime(workflow.updated_at) }}</span>
        <span class="spacer" />
        <span class="wf-list-actions">
          <button
            v-if="workflow.role === 'owner'"
            class="icon-btn"
            type="button"
            title="删除"
            @click.stop="remove(workflow)"
          >
            <AppIcon name="trash" />
          </button>
          <AppIcon name="arrow-right" class="icon-sm" />
        </span>
      </div>
    </button>
  </div>

  <div v-else class="empty" style="padding: 64px 24px">
    <span class="empty-icon"><AppIcon name="workflow" /></span>
    <h3>还没有工作流</h3>
    <p>新建一个工作流，拖入节点并连线即可开始编排。</p>
    <button class="btn btn-primary btn-sm" type="button" @click="openCreate">新建工作流</button>
  </div>

  <Teleport to="body">
    <div v-if="createOpen" class="modal">
      <div class="modal-backdrop" @click="createOpen = false" />
      <div class="modal-card modal-sm">
        <div class="modal-head">
          <div>
            <h3 class="modal-title">新建工作流</h3>
            <p class="modal-sub">创建后进入画布编辑器</p>
          </div>
          <button class="icon-btn" type="button" aria-label="关闭" @click="createOpen = false">
            <AppIcon name="x" />
          </button>
        </div>
        <div class="modal-body">
          <div class="field">
            <label class="field-label" for="wf-name">名称</label>
            <input
              id="wf-name"
              v-model="createForm.name"
              class="input"
              placeholder="例如：知识库问答流程"
            />
          </div>
          <div class="field mt-4">
            <label class="field-label" for="wf-desc">描述</label>
            <textarea
              id="wf-desc"
              v-model="createForm.description"
              class="textarea"
              rows="3"
              placeholder="选填"
            />
          </div>
          <p v-if="createError" class="field-error mt-4">{{ createError }}</p>
        </div>
        <div class="modal-foot">
          <button class="btn btn-secondary" type="button" @click="createOpen = false">取消</button>
          <button class="btn" type="button" :disabled="creating" @click="submitCreate">
            {{ creating ? '创建中…' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
