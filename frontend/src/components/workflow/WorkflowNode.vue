<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import AppIcon from '@/components/ui/AppIcon.vue'

interface WorkflowNodeData {
  name: string
  nodeType: string
  config: Record<string, unknown>
  version: number
  meta?: {
    name: string
    category: string
    inputs: { id: string; label: string }[]
    outputs: { id: string; label: string }[]
  }
}

const props = defineProps<{
  id: string
  data: WorkflowNodeData
  selected?: boolean
}>()

const ICONS: Record<string, string> = {
  start: 'play',
  llm: 'sparkles',
  http: 'globe',
  condition: 'branch',
}

const icon = computed(() => ICONS[props.data.nodeType] || 'workflow')
const inputs = computed(() => props.data.meta?.inputs ?? [{ id: 'in', label: '输入' }])
const outputs = computed(() => props.data.meta?.outputs ?? [{ id: 'out', label: '输出' }])

function portTop(index: number, total: number) {
  return `${Math.round(((index + 1) / (total + 1)) * 100)}%`
}
</script>

<template>
  <div class="wf-node" :class="{ 'is-selected': selected }">
    <div class="wf-node-head">
      <span class="wf-node-icon"><AppIcon :name="icon" /></span>
      <div class="wf-node-title">
        <strong>{{ data.name || data.meta?.name || data.nodeType }}</strong>
        <span>{{ data.meta?.category || data.nodeType }}</span>
      </div>
      <span class="wf-node-version">v{{ data.version }}</span>
    </div>

    <div class="wf-node-body">
      <span class="wf-node-type">{{ data.nodeType }}</span>
      <span>{{ Object.keys(data.config || {}).length }} 个参数</span>
    </div>

    <Handle
      v-for="(port, index) in inputs"
      :key="`in-${port.id}`"
      type="target"
      :id="port.id"
      :position="Position.Left"
      class="wf-handle"
      :style="{ top: portTop(index, inputs.length) }"
    />
    <span
      v-for="(port, index) in inputs"
      :key="`in-label-${port.id}`"
      class="wf-port-label is-input"
      :style="{ top: portTop(index, inputs.length) }"
    >
      {{ port.label }}
    </span>

    <Handle
      v-for="(port, index) in outputs"
      :key="`out-${port.id}`"
      type="source"
      :id="port.id"
      :position="Position.Right"
      class="wf-handle"
      :style="{ top: portTop(index, outputs.length) }"
    />
    <span
      v-for="(port, index) in outputs"
      :key="`out-label-${port.id}`"
      class="wf-port-label is-output"
      :style="{ top: portTop(index, outputs.length) }"
    >
      {{ port.label }}
    </span>
  </div>
</template>
