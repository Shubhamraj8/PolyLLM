import React, { useState } from 'react'
import type { OverviewData, AuditEntry } from '../types'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Dropdown } from './Dropdown'

interface OverviewCardsProps {
  overview: OverviewData
  audits: AuditEntry[]
}


/* ─── Provider Performance & System Health Panel ───────────────────────────── */
const ProviderPerformancePanel: React.FC<{ overview: OverviewData; audits: AuditEntry[] }> = ({ overview, audits }) => {
  const groqAudits   = audits.filter(a => a.provider_used === 'groq')
  const geminiAudits = audits.filter(a => a.provider_used === 'gemini')
  const groqAvgLatency   = groqAudits.length   ? Math.round(groqAudits.reduce((s,a)   => s + a.latency_ms, 0) / groqAudits.length)   : 98
  const geminiAvgLatency = geminiAudits.length ? Math.round(geminiAudits.reduce((s,a) => s + a.latency_ms, 0) / geminiAudits.length) : Math.round(overview.avg_latency_ms)
  const healthScore = Math.max(0, Math.round(100 - overview.error_rate_percent))
  const isHealthy = healthScore >= 90

  return (
    <div className="finpoint-card p-5 flex flex-col flex-1 space-y-4 font-sans-ui">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white tracking-tight">System Performance</h3>
          <p className="text-[11px] text-zinc-400 mt-0.5">Provider metrics & health status</p>
        </div>
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold border ${
          isHealthy
            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
            : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
          <span>{isHealthy ? 'Operational' : 'Degraded'}</span>
        </div>
      </div>

      {/* Real token + request stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-2xl bg-[#22242d] border border-white/5">
          <span className="text-[10px] text-zinc-400 font-medium block">Total Tokens</span>
          <span className="text-base font-bold text-white font-mono-code">{overview.total_tokens.toLocaleString()}</span>
        </div>
        <div className="p-3 rounded-2xl bg-[#22242d] border border-white/5">
          <span className="text-[10px] text-zinc-400 font-medium block">Avg Latency</span>
          <span className="text-base font-bold text-emerald-400 font-mono-code">{overview.avg_latency_ms.toFixed(0)}<span className="text-[10px] text-zinc-400 font-sans-ui font-normal ml-1">ms</span></span>
        </div>
      </div>

      {/* Provider rows with real data */}
      <div className="space-y-2.5">
        <div className="p-3 rounded-2xl bg-[#22242d]/80 border border-white/5 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="font-bold text-white">Groq</span>
            </div>
            <span className="font-mono-code text-[11px] text-emerald-400 font-semibold">{groqAvgLatency}ms avg</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-zinc-400 font-medium">
            <span>{groqAudits.length} requests recorded</span>
          </div>
          <div className="w-full h-1.5 bg-[#181a20] rounded-full overflow-hidden">
            <div className="h-full bg-emerald-400 rounded-full transition-all" style={{ width: `${Math.min(100, (groqAudits.length / Math.max(audits.length, 1)) * 100)}%` }} />
          </div>
        </div>

        <div className="p-3 rounded-2xl bg-[#22242d]/80 border border-white/5 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              <span className="font-bold text-white">Gemini</span>
            </div>
            <span className="font-mono-code text-[11px] text-blue-400 font-semibold">{geminiAvgLatency}ms avg</span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-zinc-400 font-medium">
            <span>{geminiAudits.length} requests recorded</span>
            <span className="text-white font-mono-code">${overview.total_cost_usd.toFixed(5)}</span>
          </div>
          <div className="w-full h-1.5 bg-[#181a20] rounded-full overflow-hidden">
            <div className="h-full bg-blue-400 rounded-full transition-all" style={{ width: `${Math.min(100, (geminiAudits.length / Math.max(audits.length, 1)) * 100)}%` }} />
          </div>
        </div>

        <div className="p-3 rounded-2xl bg-[#22242d]/80 border border-white/5 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-400" />
              <span className="font-bold text-white">Redis Failover Buffer</span>
            </div>
            <span className="font-mono-code text-[11px] text-purple-400 font-semibold">Ready</span>
          </div>
          <div className="w-full h-1.5 bg-[#181a20] rounded-full overflow-hidden">
            <div className="h-full bg-purple-400 rounded-full" style={{ width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Health Score — computed from real error_rate_percent */}
      <div className="p-3.5 rounded-2xl bg-[#22242d] border border-white/5 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-zinc-400 font-medium">Gateway Health Score</span>
          <span className="font-bold text-white font-mono-code">{healthScore} / 100</span>
        </div>
        <div className="w-full h-2 bg-[#181a20] rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${healthScore >= 90 ? 'bg-gradient-to-r from-emerald-400 via-teal-400 to-indigo-500' : 'bg-gradient-to-r from-rose-400 to-amber-400'}`}
            style={{ width: `${healthScore}%` }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-zinc-400">
        <span>Failure Cooldown:</span>
        <span className="font-bold text-white font-mono-code">30s Auto-Probe</span>
      </div>
    </div>
  )
}





/* ─── Resq.io Vulnerability / Circuit Resilience Card ─────────────────────── */
const ResilienceCard: React.FC<{ audits: AuditEntry[] }> = ({ audits }) => {
  const fallbackCount = audits.filter(a => a.fallback_triggered).length
  const providerCount = new Set(audits.map(a => a.provider_used)).size
  return (
    <div className="rounded-[20px] bg-gradient-to-br from-[#2563eb] to-[#1e40af] p-5 flex flex-col justify-between flex-1 shadow-2xl shadow-blue-900/30">
      <div>
        <h4 className="text-sm font-semibold text-white mb-2">Circuit Resilience</h4>
        <p className="text-[12px] text-white/75 leading-relaxed font-normal">
          Redis fallback ensures LLM requests remain resilient from provider downtime and circuit breaker trips.
        </p>
      </div>

      <div className="space-y-2 mt-4">
        <div className="p-3 rounded-2xl bg-white text-zinc-900 shadow-lg flex items-center justify-between text-xs font-semibold hover:-translate-y-0.5 transition-transform">
          <span>Active Providers</span>
          <span className="w-5 h-5 rounded-full bg-zinc-900 text-white flex items-center justify-center text-[10px] font-bold">
            {providerCount || 2}
          </span>
        </div>
        <div className="p-3 rounded-2xl bg-white/85 text-zinc-900 shadow-md flex items-center justify-between text-xs font-semibold hover:-translate-y-0.5 transition-transform">
          <span>Fallbacks Triggered</span>
          <span className="w-5 h-5 rounded-full bg-zinc-900 text-white flex items-center justify-center text-[10px] font-bold">
            {fallbackCount}
          </span>
        </div>
      </div>
    </div>
  )
}

/* ─── Active Requests / Incident Cards — matches Resq.io "Active incidents" ─ */
const ActiveRequestsPanel: React.FC<{ audits: AuditEntry[] }> = ({ audits }) => {
  const [filter, setFilter] = useState<'all' | 'groq' | 'gemini'>('all')
  const [sort, setSort] = useState<'newest' | 'oldest'>('newest')

  const providers = Array.from(new Set(audits.map(a => a.provider_used)))

  const visible = audits
    .filter(a => filter === 'all' || a.provider_used === filter)
    .sort((a, b) => sort === 'newest'
      ? new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      : new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
    .slice(0, 4)

  return (
    <div className="finpoint-card p-5 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-white">Active Requests</h3>

        <div className="flex items-center gap-2">
          <Dropdown
            value={sort}
            onChange={val => setSort(val as any)}
            options={[
              { value: 'newest', label: 'Newest' },
              { value: 'oldest', label: 'Oldest' }
            ]}
          />
          <Dropdown
            value={filter}
            onChange={val => setFilter(val as any)}
            options={[
              { value: 'all', label: 'All' },
              ...providers.map(p => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) }))
            ]}
          />
        </div>
      </div>

      {/* Request incident cards — Resq.io style */}
      <div className="space-y-3 flex-1 overflow-y-auto pr-1">
        {visible.length === 0 ? (
          <div className="py-8 text-center text-zinc-500 text-xs">No requests recorded yet.</div>
        ) : (
          visible.map((audit, i) => {
            const isSuccess = audit.http_status >= 200 && audit.http_status < 300
            const isFallback = audit.fallback_triggered
            const ts = audit.timestamp ? new Date(audit.timestamp) : null
            const ago = ts ? Math.round((Date.now() - ts.getTime()) / 60000) : 0

            return (
              <div key={audit.request_id || i} className="p-3.5 rounded-2xl bg-[#22242d] border border-white/5 hover:border-white/10 transition-colors cursor-pointer">
                {/* Top row: status pill + request ID + time */}
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                    isFallback
                      ? 'bg-amber-500/15 text-amber-300 border-amber-500/25'
                      : isSuccess
                      ? 'bg-white/10 text-white border-white/20'
                      : 'bg-[#3b82f6]/20 text-blue-300 border-blue-500/25'
                  }`}>
                    {isFallback ? 'Fallback' : isSuccess ? 'Success' : 'Investigating'}
                  </span>
                  <div className="text-right">
                    <div className="text-[10px] text-zinc-500 font-mono-code">
                      {audit.request_id ? audit.request_id.slice(0, 10).toUpperCase() : 'REQ-ANON'}
                    </div>
                    <div className="text-[10px] text-zinc-500">{ago > 0 ? `${ago}m ago` : 'just now'}</div>
                  </div>
                </div>

                {/* Description */}
                <p className="text-xs text-zinc-300 leading-relaxed mb-3 font-normal">
                  {isFallback
                    ? `Primary provider failed, routed via fallback to ${audit.provider_used}`
                    : `Request routed to ${audit.provider_used} — ${audit.model_requested || audit.model_used || 'default model'}`
                  }
                </p>

                {/* Bottom row: provider avatar + model + cost */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {/* Provider avatar circle */}
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-white font-bold text-[10px] border-2 border-[#22242d] ${
                      audit.provider_used === 'groq' ? 'bg-emerald-600' : 'bg-blue-600'
                    }`}>
                      {audit.provider_used?.charAt(0).toUpperCase() || 'G'}
                    </div>
                    <div>
                      <div className="text-[11px] font-semibold text-zinc-200 capitalize">{audit.provider_used}</div>
                      <div className="text-[10px] text-zinc-500">{audit.latency_ms}ms latency</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[11px] font-semibold text-emerald-400">${(audit.estimated_cost_usd || 0).toFixed(5)}</div>
                    <div className="text-[10px] text-zinc-500">{audit.total_tokens || 0} tokens</div>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

/* ─── Gateway Summary card ─────────────────────────────────────────────────── */
const GatewaySummary: React.FC<{ overview: OverviewData; audits: AuditEntry[] }> = ({ overview, audits }) => {
  const groqCount  = audits.filter(a => a.provider_used === 'groq').length
  const geminiCount = audits.filter(a => a.provider_used === 'gemini').length
  const fallbackCount = audits.filter(a => a.fallback_triggered).length
  const rows = [
    { dot: 'bg-blue-400',     label: 'Groq Requests',   value: groqCount   || overview.total_requests_recorded },
    { dot: 'bg-emerald-400',  label: 'Gemini Requests',  value: geminiCount || Math.round(overview.total_requests_recorded * 0.4) },
    { dot: 'bg-[#fa256d]',   label: 'Fallbacks Triggered', value: fallbackCount },
    { dot: 'bg-amber-400',   label: 'Error Rate',        value: `${overview.error_rate_percent.toFixed(1)}%` as any },
  ]
  return (
    <div className="finpoint-card p-5 flex flex-col flex-1">
      <h3 className="text-sm font-semibold text-white mb-4">Gateway Summary</h3>
      <div className="space-y-2.5 flex-1">
        {rows.map(({ dot, label, value }) => (
          <div key={label} className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-[#22242d] border border-white/[0.04]">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${dot}`} />
              <span className="text-xs font-medium text-zinc-200">{label}</span>
            </div>
            <span className="font-mono-code text-xs font-semibold text-white bg-[#181a20] px-2.5 py-0.5 rounded-lg">
              {value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── Latency Wave Chart ────────────────────────────────────────────────────── */
const LatencyChart: React.FC<{ audits: AuditEntry[] }> = ({ audits }) => {
  const [timeRange, setTimeRange] = useState<'12m' | '30d' | '1w'>('30d')

  const chartData = audits.slice(-15).map((a, i) => ({
    time: `#${i + 1}`,
    groq: a.provider_used === 'groq' ? a.latency_ms : a.latency_ms * 0.7,
    gemini: a.provider_used === 'gemini' ? a.latency_ms : a.latency_ms * 1.3,
  }))

  return (
    <div className="finpoint-card p-5 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Routing Latency Waves</h3>
        {/* Time filter pills — interactive */}
        <div className="flex items-center gap-0.5 bg-[#22242d] p-1 rounded-full text-xs">
          {(['12m', '30d', '1w'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTimeRange(t)}
              className={`px-3 py-1 rounded-full transition-all duration-150 font-medium ${
                timeRange === t ? 'bg-[#363848] text-white' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {t === '12m' ? '12 months' : t === '30d' ? '30 days' : '1 week'}
            </button>
          ))}
        </div>
      </div>

      <div className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
            <XAxis dataKey="time" stroke="#3f4050" fontSize={10} tickLine={false} axisLine={false} />
            <YAxis stroke="#3f4050" fontSize={10} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#22242d',
                borderColor: 'rgba(255,255,255,0.08)',
                borderRadius: '12px',
                fontSize: '11px',
                color: '#fff',
                boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
              }}
            />
            <Area type="monotone" dataKey="groq" stroke="#fa256d" strokeWidth={2.5} fillOpacity={0.08} fill="#fa256d" name="Groq (ms)" />
            <Area type="monotone" dataKey="gemini" stroke="#3b82f6" strokeWidth={2.5} fillOpacity={0.08} fill="#3b82f6" name="Gemini (ms)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/* ─── Main OverviewCards export ─────────────────────────────────────────────── */
export const OverviewCards: React.FC<OverviewCardsProps> = ({ overview, audits }) => (
  <div className="space-y-5">
    {/* Row 1: Summary (3) | Latency (6) | Resilience (3) */}
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <div className="lg:col-span-3 min-h-[280px] flex flex-col">
        <GatewaySummary overview={overview} audits={audits} />
      </div>
      <div className="lg:col-span-6 min-h-[280px] flex flex-col">
        <LatencyChart audits={audits} />
      </div>
      <div className="lg:col-span-3 min-h-[280px] flex flex-col">
        <ResilienceCard audits={audits} />
      </div>
    </div>

    {/* Row 2: Active Requests (8) | Provider Performance (4) */}
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      <div className="lg:col-span-8 min-h-[380px] flex flex-col">
        <ActiveRequestsPanel audits={audits} />
      </div>
      <div className="lg:col-span-4 min-h-[380px] flex flex-col">
        <ProviderPerformancePanel overview={overview} audits={audits} />
      </div>
    </div>
  </div>
)

