import { apiGet, apiPost } from './client'
import type {
  AIGovernance,
  BomGraphData,
  BusinessImpact,
  Decision,
  Evidence,
  Impact,
  Issue,
  Lineage,
  Page,
  Part,
  Principal,
  Proposal,
  QualityAnalytics,
  RemediationAnalytics,
  Scenario,
} from '../types/api'

const V1 = '/api/v1'

export const fetchParts = (params: Record<string, string | number>) =>
  apiGet<Page<Part>>(`${V1}/parts`, params)
export const fetchPartLineage = (id: string) => apiGet<Lineage>(`${V1}/parts/${id}/lineage`)
export const fetchPartImpact = (id: string) => apiGet<Impact>(`${V1}/parts/${id}/impact`)

export const fetchIssues = (params: Record<string, string | number>) =>
  apiGet<Page<Issue>>(`${V1}/issues`, params)
export const fetchIssue = (id: string) => apiGet<Issue>(`${V1}/issues/${id}`)
export const fetchIssueEvidence = (id: string) => apiGet<Evidence[]>(`${V1}/issues/${id}/evidence`)
export const fetchIssueHistory = (id: string) => apiGet<Decision[]>(`${V1}/issues/${id}/history`)
export const generateRecommendation = (id: string) =>
  apiPost<Proposal>(`${V1}/issues/${id}/recommendations`)
/** The signed-in principal. Decisions are attributed to this identity server-side. */
export const fetchMe = () => apiGet<Principal>(`${V1}/me`)

// No reviewer argument: the API records the authenticated principal and ignores
// any client-supplied actor, so sending one would be misleading.
export const approveIssue = (id: string, reason: string) =>
  apiPost(`${V1}/issues/${id}/approve`, { reason })
export const rejectIssue = (id: string, reason: string) =>
  apiPost(`${V1}/issues/${id}/reject`, { reason })

export const fetchBomGraph = (id: string, depth: number) =>
  apiGet<BomGraphData>(`${V1}/bom/${id}/graph`, { depth })
export const fetchReverseDeps = (id: string) =>
  apiGet<{ part_id: string; reverse_dependencies: string[]; affected_assembly_count: number }>(
    `${V1}/bom/${id}/reverse-dependencies`,
  )

export const simulateMerge = (duplicate_id: string, surviving_id: string) =>
  apiPost<Scenario>(`${V1}/scenarios/merge`, { duplicate_id, surviving_id })
export const simulateFieldCorrection = (part_id: string, field: string, new_value: string) =>
  apiPost<Scenario>(`${V1}/scenarios/field-correction`, { part_id, field, new_value })
export const simulateReplacement = (
  parent_id: string,
  old_child_id: string,
  new_child_id: string,
) => apiPost<Scenario>(`${V1}/scenarios/component-replacement`, { parent_id, old_child_id, new_child_id })

export const fetchQualityAnalytics = () => apiGet<QualityAnalytics>(`${V1}/analytics/quality`)
export const fetchBusinessImpact = () => apiGet<BusinessImpact>(`${V1}/analytics/business-impact`)
export const fetchRemediationAnalytics = () =>
  apiGet<RemediationAnalytics>(`${V1}/analytics/remediation`)
export const fetchAIGovernance = () => apiGet<AIGovernance>(`${V1}/analytics/ai-governance`)
