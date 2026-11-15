import request from './request'
import type { ApiResult } from './user'

export type WorkflowRole = 'owner' | 'editor' | 'viewer'

export interface WorkflowSummary {
  id: number
  name: string
  description: string
  owner_id: number
  owner_name: string
  role: WorkflowRole
  node_count: number | null
  created_at: string
  updated_at: string
}

export interface NodePort {
  id: string
  label: string
}

export interface NodeParamOption {
  value: string
  label: string
}

export interface NodeParamSpec {
  key: string
  label: string
  type: 'text' | 'textarea' | 'number' | 'boolean' | 'select' | 'json'
  required?: boolean
  default?: unknown
  help?: string
  options?: NodeParamOption[]
}

export interface NodeMeta {
  type: string
  name: string
  description: string
  category: string
  inputs: NodePort[]
  outputs: NodePort[]
  params: NodeParamSpec[]
}

export interface WorkflowNodeState {
  key: string
  node_type: string
  name: string
  position: { x: number; y: number }
  config: Record<string, unknown>
  version: number
  created_at: string
  updated_at: string
}

export interface WorkflowRelation {
  id: number
  source_key: string
  source_port: string
  target_key: string
  target_port: string
  created_at: string
}

export interface WorkflowMember {
  user_id: number
  username: string
  role: WorkflowRole
  created_at: string | null
}

export interface WorkflowEvent {
  id: number
  op: string
  payload: Record<string, unknown>
  actor_id: number | null
  actor_name: string
  created_at: string
}

export interface WorkflowState {
  workflow: {
    id: number
    name: string
    description: string
    owner_id: number
    owner_name: string
    role: WorkflowRole
    created_at: string
    updated_at: string
  }
  nodes: WorkflowNodeState[]
  relations: WorkflowRelation[]
  members: WorkflowMember[]
  last_event_seq: number
  node_types: string[]
}

export interface WorkflowDocumentNode {
  key: string
  type: string
  name: string
  position: { x: number; y: number }
  config: Record<string, unknown>
}

export interface WorkflowDocumentRelation {
  source: string
  source_port: string
  target: string
  target_port: string
}

export interface WorkflowDocument {
  format: string
  format_version: number
  name: string
  description: string
  nodes: WorkflowDocumentNode[]
  relations: WorkflowDocumentRelation[]
}

export interface RunStep {
  node_key: string
  node_type: string
  name: string
  status: 'success' | 'failed'
  error?: string
  output?: Record<string, unknown>
  logs?: string[]
  duration_ms?: number
}

export interface RunResult {
  status: 'success' | 'failed'
  error: string
  steps: RunStep[]
  output: Record<string, unknown>
  duration_ms: number
}

export function listWorkflows() {
  return request.get<any, ApiResult<{ total: number; workflows: WorkflowSummary[] }>>(
    '/workflow/workflows/',
  )
}

export function createWorkflow(payload: { name: string; description?: string }) {
  return request.post<any, ApiResult<{ workflow: WorkflowSummary }>>(
    '/workflow/workflows/',
    payload,
  )
}

export function getWorkflow(workflowId: number) {
  return request.get<any, ApiResult<WorkflowState>>(`/workflow/workflows/${workflowId}/`)
}

export function updateWorkflow(
  workflowId: number,
  payload: { name?: string; description?: string },
) {
  return request.patch<any, ApiResult<{ workflow: WorkflowSummary }>>(
    `/workflow/workflows/${workflowId}/`,
    payload,
  )
}

export function deleteWorkflow(workflowId: number) {
  return request.delete<any, ApiResult<{ id: number }>>(`/workflow/workflows/${workflowId}/`)
}

export function listWorkflowEvents(workflowId: number, after = 0, limit = 100) {
  return request.get<any, ApiResult<{ events: WorkflowEvent[]; last_event_seq: number }>>(
    `/workflow/workflows/${workflowId}/events/`,
    { params: { after, limit } },
  )
}

export function addWorkflowNode(
  workflowId: number,
  payload: {
    node_type: string
    name?: string
    position: { x: number; y: number }
    config?: Record<string, unknown>
  },
) {
  return request.post<any, ApiResult<{ node: WorkflowNodeState }>>(
    `/workflow/workflows/${workflowId}/nodes/`,
    payload,
  )
}

export function updateWorkflowNode(
  workflowId: number,
  nodeKey: string,
  payload: {
    base_version: number
    name?: string
    position?: { x: number; y: number }
    config?: Record<string, unknown>
  },
) {
  return request.patch<any, ApiResult<{ node: WorkflowNodeState }>>(
    `/workflow/workflows/${workflowId}/nodes/${nodeKey}/`,
    payload,
  )
}

export function deleteWorkflowNode(workflowId: number, nodeKey: string) {
  return request.delete<any, ApiResult<{ key: string }>>(
    `/workflow/workflows/${workflowId}/nodes/${nodeKey}/`,
  )
}

export function addWorkflowRelation(
  workflowId: number,
  payload: { source_key: string; source_port?: string; target_key: string; target_port?: string },
) {
  return request.post<any, ApiResult<{ relation: WorkflowRelation }>>(
    `/workflow/workflows/${workflowId}/edges/`,
    payload,
  )
}

export function deleteWorkflowRelation(workflowId: number, edgeId: number) {
  return request.delete<any, ApiResult<{ id: number }>>(
    `/workflow/workflows/${workflowId}/edges/${edgeId}/`,
  )
}

export function importWorkflow(workflowId: number, document: WorkflowDocument) {
  return request.post<any, ApiResult<WorkflowState>>(
    `/workflow/workflows/${workflowId}/import/`,
    document,
  )
}

export function exportWorkflow(workflowId: number) {
  return request.get<any, ApiResult<WorkflowDocument>>(`/workflow/workflows/${workflowId}/export/`)
}

export function runWorkflow(workflowId: number) {
  return request.post<any, ApiResult<RunResult>>(
    `/workflow/workflows/${workflowId}/run/`,
    {},
    { timeout: 120_000 },
  )
}

export function listWorkflowMembers(workflowId: number) {
  return request.get<any, ApiResult<WorkflowState>>(`/workflow/workflows/${workflowId}/members/`)
}

export function addWorkflowMember(
  workflowId: number,
  payload: { username: string; role: 'editor' | 'viewer' },
) {
  return request.post<any, ApiResult<{ members: WorkflowMember[] }>>(
    `/workflow/workflows/${workflowId}/members/`,
    payload,
  )
}

export function removeWorkflowMember(workflowId: number, userId: number) {
  return request.delete<any, ApiResult<{ members: WorkflowMember[] }>>(
    `/workflow/workflows/${workflowId}/members/${userId}/`,
  )
}

export function listNodeTypes() {
  return request.get<any, ApiResult<{ types: string[] }>>('/workflow/node-types/')
}

export function getNodeTypeMeta(nodeType: string) {
  return request.get<any, ApiResult<{ meta: NodeMeta }>>(`/workflow/node-types/${nodeType}/`)
}
