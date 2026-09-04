import type { GatewayStatsResponse } from './types'


export async function fetchStats(
  baseUrl: string,
  apiKey: string
): Promise<GatewayStatsResponse> {
  const url = `${baseUrl.replace(/\/$/, '')}/admin/stats`
  const res = await fetch(url, {
    method: 'GET',
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json',
    },
  })

  if (!res.ok) {
    throw new Error(`HTTP error ${res.status}: ${res.statusText}`)
  }

  return res.json()
}

export async function reloadConfig(
  baseUrl: string,
  apiKey: string
): Promise<{ status: string; timestamp: string }> {
  const url = `${baseUrl.replace(/\/$/, '')}/admin/reload`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json',
    },
  })

  if (!res.ok) {
    throw new Error(`HTTP error ${res.status}: ${res.statusText}`)
  }

  return res.json()
}

export function getMockStats(): GatewayStatsResponse {
  const now = new Date().toISOString()
  return {
    overview: {
      total_requests_recorded: 1248,
      total_cost_usd: 0.04182,
      error_rate_percent: 1.6,
      avg_latency_ms: 245.8,
      total_tokens: 458200,
    },
    circuit_breakers: {
      groq: {
        state: 'CLOSED',
        failure_count: 0,
        failure_threshold: 5,
        cooldown_seconds: 30,
        opened_at: null,
      },
      gemini: {
        state: 'CLOSED',
        failure_count: 0,
        failure_threshold: 5,
        cooldown_seconds: 30,
        opened_at: null,
      },
    },
    cost_breakdown: {
      total_usd: 0.04182,
      groq_usd: 0.0,
      gemini_usd: 0.04182,
      tokens_total: 458200,
    },
    config: {
      version: '1.0.0',
      routing: {
        default_chain: 'default',
        chains: {
          default: ['groq', 'gemini'],
          gemini_first: ['gemini', 'groq'],
        },
      },
      providers: {
        groq: {
          timeout_seconds: 10,
          models: ['mixtral-8x7b-32768', 'llama-3.1-8b-instant'],
          default_model: 'mixtral-8x7b-32768',
        },
        gemini: {
          timeout_seconds: 15,
          models: ['gemini-1.5-flash', 'gemini-1.5-flash-8b'],
          default_model: 'gemini-1.5-flash',
        },
      },
      circuit_breaker: {
        failure_threshold: 5,
        window_seconds: 60,
        cooldown_seconds: 30,
      },
      rate_limit: {
        per_api_key: { requests: 100, window_seconds: 60 },
        per_ip: { requests: 200, window_seconds: 60 },
      },
    },
    recent_audits: [
      {
        request_id: 'req-8f4b12c9',
        timestamp: new Date(Date.now() - 1000 * 12).toISOString(),
        ip: '192.168.1.10',
        api_key_prefix: 'dev-key...',
        model_requested: 'gpt-4',
        provider_used: 'groq',
        model_used: 'mixtral-8x7b-32768',
        fallback_triggered: false,
        providers_tried: ['groq'],
        status: 'success',
        http_status: 200,
        latency_ms: 215,
        prompt_tokens: 120,
        completion_tokens: 85,
        total_tokens: 205,
        estimated_cost_usd: 0.0,
      },
      {
        request_id: 'req-7a2e99f1',
        timestamp: new Date(Date.now() - 1000 * 45).toISOString(),
        ip: '192.168.1.14',
        api_key_prefix: 'dev-key...',
        model_requested: 'gpt-4',
        provider_used: 'gemini',
        model_used: 'gemini-1.5-flash',
        fallback_triggered: true,
        providers_tried: ['groq', 'gemini'],
        status: 'success',
        http_status: 200,
        latency_ms: 480,
        prompt_tokens: 350,
        completion_tokens: 180,
        total_tokens: 530,
        estimated_cost_usd: 0.00008,
      },
      {
        request_id: 'req-5c1d33a8',
        timestamp: new Date(Date.now() - 1000 * 90).toISOString(),
        ip: '10.0.0.5',
        api_key_prefix: 'dev-key...',
        model_requested: 'gpt-3.5-turbo',
        provider_used: 'groq',
        model_used: 'llama-3.1-8b-instant',
        fallback_triggered: false,
        providers_tried: ['groq'],
        status: 'success',
        http_status: 200,
        latency_ms: 142,
        prompt_tokens: 45,
        completion_tokens: 60,
        total_tokens: 105,
        estimated_cost_usd: 0.0,
      },
    ],
    timestamp: now,
  }
}
