export interface OverviewData {
  total_requests_recorded: number
  total_cost_usd: number
  error_rate_percent: number
  avg_latency_ms: number
  total_tokens: number
}

export interface CircuitBreakerInfo {
  state: 'CLOSED' | 'OPEN' | 'HALF_OPEN'
  failure_count: number
  failure_threshold: number
  cooldown_seconds: number
  opened_at?: number | null
}

export interface CostBreakdown {
  total_usd: number
  groq_usd: number
  gemini_usd: number
  tokens_total: number
}

export interface AuditEntry {
  request_id: string

  timestamp: string
  ip: string
  api_key_prefix: string
  model_requested: string
  provider_used: string
  model_used: string
  fallback_triggered: boolean
  providers_tried: string[]
  status: string
  http_status: number
  latency_ms: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  estimated_cost_usd: number
  error?: string | null
}

export interface GatewayStatsResponse {
  overview: OverviewData
  circuit_breakers: Record<string, CircuitBreakerInfo>
  cost_breakdown: CostBreakdown
  config: Record<string, any>
  recent_audits: AuditEntry[]
  timestamp: string
}
