import React, { useState } from 'react'
import type { CircuitBreakerInfo } from '../types'
import { Server, AlertTriangle, Clock, ZapOff, RefreshCw, CheckCircle2, Activity } from 'lucide-react'

interface CircuitBreakerCardsProps {
  circuitBreakers: Record<string, CircuitBreakerInfo>
  onSimulateErrorSpike?: (provider: string) => void
  onResetBreaker?: (provider: string) => void
}

export const CircuitBreakerCards: React.FC<CircuitBreakerCardsProps> = ({
  circuitBreakers,
  onSimulateErrorSpike,
  onResetBreaker,
}) => {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)

  const providers = Object.keys(circuitBreakers)

  const handleAction = async (key: string, fn?: (p: string) => void, provider?: string) => {
    if (!fn || !provider) return
    setLoadingAction(key)
    fn(provider)
    // Simulate brief loading feedback
    setTimeout(() => setLoadingAction(null), 600)
  }

  if (providers.length === 0) {
    return (
      <div className="finpoint-card p-8 text-center">
        <Activity className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
        <p className="text-zinc-500 text-sm">No circuit breaker state available.</p>
        <p className="text-zinc-600 text-xs mt-1">Connect to a live gateway to see breaker states.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {providers.map(provider => {
        const info = circuitBreakers[provider]
        const state = info.state || 'CLOSED'
        const failures = info.failure_count || 0
        const threshold = info.failure_threshold || 5

        const isClosed = state === 'CLOSED'
        const isOpen = state === 'OPEN'
        const isHalfOpen = state === 'HALF_OPEN'

        const tripKey = `trip-${provider}`
        const resetKey = `reset-${provider}`

        return (
          <div key={provider} className="finpoint-card p-5 space-y-4">
            {/* ── Header ── */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
                  isOpen
                    ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                    : isHalfOpen
                    ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                    : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                }`}>
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white capitalize tracking-tight">
                    {provider.charAt(0).toUpperCase() + provider.slice(1)} Provider
                  </h3>
                  <p className="text-[11px] text-zinc-500">Distributed Redis State Machine</p>
                </div>
              </div>

              {/* State badge */}
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold border ${
                isOpen
                  ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                  : isHalfOpen
                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                  : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
              }`}>
                {isOpen ? (
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping" />
                ) : isHalfOpen ? (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                )}
                {isClosed ? 'CLOSED' : isOpen ? 'OPEN' : 'HALF_OPEN'}
              </div>
            </div>

            {/* ── Failure tracker ── */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-zinc-500" />
                  Rolling Window Failures:
                </span>
                <span className="font-mono-code font-semibold text-white">{failures} / {threshold}</span>
              </div>

              {/* Progress bar */}
              <div className="w-full h-1.5 rounded-full bg-[#252732] overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isOpen ? 'bg-rose-500' : isHalfOpen ? 'bg-amber-400' : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min((failures / threshold) * 100, 100)}%` }}
                />
              </div>

              {/* Tick boxes */}
              <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${threshold}, 1fr)` }}>
                {Array.from({ length: threshold }).map((_, i) => (
                  <div
                    key={i}
                    className={`h-2 rounded-sm transition-colors duration-300 ${
                      i < failures
                        ? isOpen ? 'bg-rose-500' : 'bg-amber-400'
                        : 'bg-[#252732]'
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* ── Config details ── */}
            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-white/[0.05]">
              <div className="bg-[#1c1e26] rounded-xl p-3 border border-white/[0.04]">
                <span className="text-[10px] text-zinc-500 font-medium block mb-1">Failure Threshold</span>
                <span className="text-xs font-semibold text-white">{threshold} consecutive errors</span>
              </div>
              <div className="bg-[#1c1e26] rounded-xl p-3 border border-white/[0.04]">
                <span className="text-[10px] text-zinc-500 font-medium flex items-center gap-1 mb-1">
                  <Clock className="w-3 h-3" /> Cooldown Period
                </span>
                <span className="text-xs font-semibold text-white">{info.cooldown_seconds || 30}s auto-probe</span>
              </div>
            </div>

            {/* ── Action buttons — fully working ── */}
            <div className="flex items-center justify-between pt-3 border-t border-white/[0.05]">
              <span className="text-[11px] text-zinc-500 font-medium">Live State Tester:</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleAction(tripKey, onSimulateErrorSpike, provider)}
                  disabled={loadingAction === tripKey || isOpen}
                  title={isOpen ? 'Breaker already OPEN' : 'Simulate 5 consecutive failures to trip this breaker'}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                    isOpen
                      ? 'bg-[#1c1e26] border-white/5 text-zinc-600 cursor-not-allowed'
                      : 'bg-rose-500/10 hover:bg-rose-500/20 border-rose-500/20 text-rose-300 hover:text-rose-200 active:scale-95'
                  }`}
                >
                  {loadingAction === tripKey ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <ZapOff className="w-3.5 h-3.5" />
                  )}
                  Trip Breaker
                </button>

                <button
                  onClick={() => handleAction(resetKey, onResetBreaker, provider)}
                  disabled={loadingAction === resetKey || isClosed}
                  title={isClosed ? 'Breaker already CLOSED' : 'Reset breaker back to CLOSED (healthy) state'}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                    isClosed
                      ? 'bg-[#1c1e26] border-white/5 text-zinc-600 cursor-not-allowed'
                      : 'bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/20 text-emerald-300 hover:text-emerald-200 active:scale-95'
                  }`}
                >
                  {loadingAction === resetKey ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5" />
                  )}
                  Reset
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
