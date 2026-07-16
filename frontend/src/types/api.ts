/** Types mirroring the FastAPI response models. */

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Part {
  part_key: string
  source_part_number: string | null
  source_system: string | null
  description: string | null
  category: string | null
  uom: string | null
  lifecycle_status: string | null
  procurement_type: string | null
  standard_cost: number | null
  lead_time_days: number | null
  primary_plant: string | null
}

export interface Issue {
  issue_id: string
  rule_id: string
  entity_type: string
  entity_key: string
  field: string | null
  severity: 'critical' | 'high' | 'medium' | 'low'
  domain: string
  status: string
  detected_at: string | null
}

export interface Evidence {
  evidence_id: string
  issue_id: string
  field: string | null
  failed_value: string | null
}

export interface Decision {
  decision_id: string
  issue_id: string
  reviewer: string
  decision: string
  reason: string
  before_status: string
  after_status: string
  decided_at: string
}

export interface Proposal {
  issue_id: string
  recommended_action: string
  surviving_record: string | null
  records_affected: string[]
  evidence_refs: string[]
  confidence: number
  risks: string[]
  human_review_required: boolean
  explanation: string
  provider: string
  model: string
  prompt_version: string
  created_at: string
}

export interface Impact {
  part_id: string
  affected_parent_assemblies: number
  downstream_components: number
  dependency_depth: number
  future_demand_qty_exposed: number
  inventory_value_exposed: number
  po_value_exposed: number
  production_orders_affected: number
  suppliers_affected: number
  plants_affected: number
  supplier_concentration: {
    components_in_tree: number
    single_source_components: number
    single_source_ratio: number
  }
  estimated_cost_exposure: number
  operational_priority: number
}

export interface BomNode {
  id: string
  description: string | null
  lifecycle_status: string | null
  category: string | null
  in_cycle: boolean
}

export interface BomEdge {
  parent: string
  child: string
  level: number
  quantity_per: number | null
}

export interface BomGraphData {
  root: string
  nodes: BomNode[]
  edges: BomEdge[]
  cycles: string[][]
}

export interface Scenario {
  scenario_id: string
  scenario_type: string
  parameters: Record<string, string>
  before: Record<string, unknown>
  after: Record<string, unknown>
  resolved_rules: string[]
  new_warnings: string[]
  approval_required: boolean
}

export interface QualityAnalytics {
  enterprise_quality_score: number
  weighted_issue_points: number
  open_issues: number
  parts_in_scope: number
  open_by_severity: Record<string, number>
  open_by_domain: Record<string, number>
  top_rules: { rule_id: string; n: number }[]
}

export interface BusinessImpact {
  total_inventory_value: number
  total_future_demand_qty: number
  entities_with_critical_issues: number
}

export interface RemediationAnalytics {
  decisions: Record<string, number>
  acceptance_rate: number | null
  backlog: number
}

export interface AIGovernance {
  calls: number
  by_provider?: Record<string, number>
  abstention_rate?: number
  validation_failure_rate?: number
  avg_latency_ms?: number
  avg_confidence?: number
  prompt_versions?: string[]
}

export interface Lineage {
  entity_id: string
  members: string[]
  fields: Record<
    string,
    {
      selected_value: unknown
      source_record: string
      source_system: string
      reason: string
      confidence: number
      alternatives: { value: unknown; source_record: string; score: number }[]
    }
  >
}
