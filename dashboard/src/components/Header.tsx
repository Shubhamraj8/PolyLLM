import React, { useState } from 'react'
import { Zap, Globe, Key, RefreshCw, SlidersHorizontal, Sparkles } from 'lucide-react'
import type { OverviewData } from '../types'

/* ─── KPI Badge — pixel-perfect Resq.io replica ──────────────────────────────
   Structure (exactly as in Resq.io screenshot):
     • Colored gradient circle with mini trend SVG inside
     • Tiny overlapping percent pill badge at top-right corner
     • Large extralight number to the right
     • Muted label below that turns colored on hover
     • Hover tooltip
   ─────────────────────────────────────────────────────────────────────────── */
interface KpiBadgeProps {
  trend: 'up' | 'down'
  value: string
  unit?: string
  label: string
  tooltip: string
}

const KpiBadge: React.FC<KpiBadgeProps> = ({ trend, value, unit, label, tooltip }) => {
  const [hovered, setHovered] = useState(false)
  const isUp = trend === 'up'

  return (
    <div
      className="relative flex items-center gap-4 cursor-pointer group"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Colored gradient circle with chart icon */}
      <div className="relative shrink-0">
        <div
          className={`w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-all duration-200 group-hover:scale-110 group-hover:shadow-xl ${
            isUp
              ? 'bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-emerald-500/20'
              : 'bg-gradient-to-br from-rose-400 to-rose-600 shadow-rose-500/20'
          }`}
        >
          {isUp ? (
            <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
              <polyline points="16 7 22 7 22 13" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" />
              <polyline points="16 17 22 17 22 11" />
            </svg>
          )}
        </div>
      </div>

      {/* Number + label */}
      <div>
        <div className="text-[30px] leading-none font-extralight text-white tracking-tight group-hover:text-white/90 transition-colors">
          {value}
          {unit && <span className="text-sm text-zinc-500 font-normal ml-1">{unit}</span>}
        </div>
        <span className={`text-xs font-medium block mt-1 transition-colors duration-150 ${
          hovered ? (isUp ? 'text-emerald-400' : 'text-rose-400') : 'text-zinc-400'
        }`}>
          {label}
        </span>
      </div>

      {/* Tooltip */}
      {hovered && (
        <div className="absolute bottom-full left-0 mb-2.5 px-3 py-1.5 bg-[#22242d] text-zinc-300 text-[11px] font-medium rounded-xl border border-white/10 whitespace-nowrap shadow-2xl z-50 pointer-events-none">
          {tooltip}
          <div className="absolute top-full left-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-[#22242d]" />
        </div>
      )}
    </div>
  )
}

/* ─── Header ─────────────────────────────────────────────────────────────── */
interface HeaderProps {
  baseUrl: string
  setBaseUrl: (url: string) => void
  apiKey: string
  setApiKey: (key: string) => void
  isLiveMode: boolean
  isAutoRefresh: boolean
  setIsAutoRefresh: (val: boolean) => void
  refreshIntervalSecs: number
  setRefreshIntervalSecs: (secs: number) => void
  onRefresh: () => void
  isFetching: boolean
  isMockData: boolean
  lastUpdated: string | null
  onToggleMockMode: () => void
  activeTab: string
  setActiveTab: (tab: any) => void
  breakerCount: number
  overview: OverviewData
}

export const Header: React.FC<HeaderProps> = ({
  baseUrl, setBaseUrl, apiKey, setApiKey,
  isAutoRefresh, setIsAutoRefresh, refreshIntervalSecs, setRefreshIntervalSecs,
  onRefresh, isFetching, isMockData, lastUpdated,
  onToggleMockMode, activeTab, setActiveTab,
  breakerCount, overview,
}) => {
  const [showSettings, setShowSettings] = useState(false)

  return (
    <header className="bg-[#121318] border-b border-white/[0.06] px-6 py-4">

      {/* ── Navbar row ── */}
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
        
        {/* Left Side: Logo */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Zap className="w-4 h-4 text-white fill-current" />
          </div>
          <div>
            <h1 className="text-[15px] font-semibold tracking-tight text-white leading-tight">PolyLLM</h1>
            <span className="text-[10px] text-zinc-500 font-medium">Gateway Admin</span>
          </div>
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setActiveTab(activeTab === 'config' ? 'overview' : 'config')}
            title="Gateway Configuration"
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors ${
              activeTab === 'config' 
                ? 'bg-[#2e3040] text-white shadow-sm' 
                : 'bg-[#1c1e26] border border-white/[0.06] text-zinc-400 hover:text-white hover:bg-white/5'
            }`}
          >
            {activeTab === 'config' ? 'Back to Dashboard' : 'Config'}
          </button>

          <button
            onClick={onRefresh}
            disabled={isFetching}
            title="Refresh data from gateway"
            className="w-8 h-8 rounded-full bg-[#1c1e26] border border-white/[0.06] flex items-center justify-center text-zinc-400 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setShowSettings(s => !s)}
            title="Connection settings"
            className={`w-8 h-8 rounded-full border border-white/[0.06] flex items-center justify-center transition-colors ${
              showSettings ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' : 'bg-[#1c1e26] text-zinc-400 hover:text-white'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onToggleMockMode}
            title={isMockData ? 'Click to try live gateway connection' : 'Click to use demo data'}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
              isMockData
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/20 hover:bg-amber-500/20'
                : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20 hover:bg-emerald-500/20'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isMockData ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'}`} />
            {isMockData ? 'Demo' : 'Live'}
          </button>
        </div>
      </div>

      {/* ── Settings drawer ── */}
      {showSettings && (
        <div className="max-w-7xl mx-auto mt-4 pt-4 border-t border-white/[0.06] grid grid-cols-1 md:grid-cols-3 gap-4 text-xs animate-fade-in">
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 font-medium flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-zinc-500" /> Gateway URL
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={e => setBaseUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="bg-[#1c1e26] border border-white/10 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500/50 font-mono-code text-xs"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 font-medium flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-zinc-500" /> API Key (X-API-Key)
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="dev-key"
              className="bg-[#1c1e26] border border-white/10 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500/50 font-mono-code text-xs"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-zinc-400 font-medium flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-zinc-500" /> Auto-refresh Interval
            </label>
            <select
              value={isAutoRefresh ? refreshIntervalSecs : 0}
              onChange={e => {
                const val = Number(e.target.value)
                if (val === 0) setIsAutoRefresh(false)
                else { setIsAutoRefresh(true); setRefreshIntervalSecs(val) }
              }}
              className="bg-[#1c1e26] border border-white/10 rounded-xl px-3 py-2 text-zinc-100 focus:outline-none focus:border-indigo-500/50 text-xs"
            >
              <option value={0}>Disabled</option>
              <option value={3}>Every 3s</option>
              <option value={5}>Every 5s</option>
              <option value={10}>Every 10s</option>
            </select>
          </div>
        </div>
      )}

      {/* ── Sub-header: Welcome + Progress Bars + KPI Badges ── */}
      <div className="max-w-7xl mx-auto mt-6 pt-5 border-t border-white/[0.06] flex flex-col md:flex-row items-start md:items-center justify-between gap-6">

        {/* Left: "Welcome in, Developer" + fill bars (now wired to real stats) */}
        <div className="space-y-3">
          <h2 className="text-[22px] font-semibold tracking-tight leading-tight">
            Welcome in,{' '}
            <span className="text-[#9496a1] font-normal">Developer</span>
          </h2>

          <div className="flex flex-wrap items-end gap-4">
            {/* Real data-driven progress bars */}
            <div className="flex flex-col gap-1.5 min-w-[80px]">
              <span className="text-[11px] text-zinc-400 font-medium">Gateway Health</span>
              <div className="relative h-7 rounded-full overflow-hidden bg-[#252830]">
                <div className="h-full rounded-full transition-all duration-700 bg-emerald-500" style={{ width: `${Math.max(0, 100 - overview.error_rate_percent)}%` }} />
                <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-white mix-blend-screen">{Math.max(0, 100 - overview.error_rate_percent).toFixed(0)}%</span>
              </div>
            </div>
            
            <div className="flex flex-col gap-1.5 min-w-[80px]">
              <span className="text-[11px] text-zinc-400 font-medium">Error Rate</span>
              <div className="relative h-7 rounded-full overflow-hidden bg-[#252830]">
                <div className="h-full rounded-full transition-all duration-700 bg-rose-500" style={{ width: `${Math.min(100, overview.error_rate_percent * 5)}%` }} />
                <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-white mix-blend-screen">{overview.error_rate_percent.toFixed(1)}%</span>
              </div>
            </div>

            <div className="flex flex-col gap-1.5 min-w-[80px]">
              <span className="text-[11px] text-zinc-400 font-medium">Latency SLA</span>
              <div className="relative h-7 rounded-full overflow-hidden bg-[#1e202a]">
                <div className="h-full rounded-full transition-all duration-700 bg-indigo-500" style={{ width: `${Math.min(100, (overview.avg_latency_ms / 1000) * 100)}%` }} />
                <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-white mix-blend-screen">{overview.avg_latency_ms.toFixed(0)}ms</span>
              </div>
            </div>

            <div className="flex flex-col gap-1.5 min-w-[80px]">
              <span className="text-[11px] text-zinc-400 font-medium">Active Breakers</span>
              <div className="relative h-7 rounded-full overflow-hidden bg-[#252832]">
                <div className="h-full rounded-full transition-all duration-700 bg-amber-500 stripe-pattern" style={{ width: `${breakerCount > 0 ? 100 : 0}%` }} />
                <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-white mix-blend-screen">{breakerCount}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: KPI badges — pixel-perfect Resq.io circles */}
        <div className="flex items-center gap-8 flex-wrap">
          <KpiBadge
            trend="up"
            value={overview.total_requests_recorded.toLocaleString()}
            label="Critical requests"
            tooltip="Total LLM requests routed through the gateway"
          />
          <KpiBadge
            trend="up"
            value={overview.total_cost_usd.toFixed(2)}
            label="Cost (USD)"
            tooltip="Cumulative spend across all LLM providers"
          />
          <KpiBadge
            trend="down"
            value={overview.avg_latency_ms.toFixed(0)}
            unit="ms"
            label="Avg latency"
            tooltip="Mean end-to-end latency per request"
          />
        </div>
      </div>

      {lastUpdated && (
        <div className="max-w-7xl mx-auto mt-1.5 text-[10px] text-zinc-600 font-mono-code text-right">
          Last synced: {new Date(lastUpdated).toLocaleTimeString()}
        </div>
      )}
    </header>
  )
}
