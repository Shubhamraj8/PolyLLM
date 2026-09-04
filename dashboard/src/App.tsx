import { useState, useEffect, useCallback } from 'react'
import { Header } from './components/Header'
import { OverviewCards } from './components/OverviewCards'
import { CircuitBreakerCards } from './components/CircuitBreakerCards'
import { AuditLogTable } from './components/AuditLogTable'
import { ConfigPanel } from './components/ConfigPanel'
import { fetchStats, getMockStats } from './api'
import type { GatewayStatsResponse } from './types'

export function App() {
  const [baseUrl, setBaseUrl] = useState('http://localhost:8000')
  const [apiKey, setApiKey] = useState('dev-key')
  const [isAutoRefresh, setIsAutoRefresh] = useState(true)
  const [refreshIntervalSecs, setRefreshIntervalSecs] = useState(5)
  const [activeTab, setActiveTab] = useState<'overview' | 'breakers' | 'analytics' | 'audits' | 'config'>('overview')

  const [stats, setStats] = useState<GatewayStatsResponse>(getMockStats())
  const [isFetching, setIsFetching] = useState(false)
  const [isMockData, setIsMockData] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setIsFetching(true)
    try {
      const data = await fetchStats(baseUrl, apiKey)
      setStats(data)
      setIsMockData(false)
      setLastUpdated(new Date().toISOString())
    } catch (err) {
      setIsMockData(true)
    } finally {
      setIsFetching(false)
    }
  }, [baseUrl, apiKey])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    if (!isAutoRefresh) return
    const interval = setInterval(() => {
      loadData()
    }, refreshIntervalSecs * 1000)

    return () => clearInterval(interval)
  }, [isAutoRefresh, refreshIntervalSecs, loadData])

  const handleSimulateErrorSpike = (provider: string) => {
    setStats((prev) => ({
      ...prev,
      circuit_breakers: {
        ...prev.circuit_breakers,
        [provider]: {
          ...prev.circuit_breakers[provider],
          state: 'OPEN',
          failure_count: prev.circuit_breakers[provider]?.failure_threshold || 5,
          opened_at: Date.now() / 1000,
        },
      },
    }))
  }

  const handleResetBreaker = (provider: string) => {
    setStats((prev) => ({
      ...prev,
      circuit_breakers: {
        ...prev.circuit_breakers,
        [provider]: {
          ...prev.circuit_breakers[provider],
          state: 'CLOSED',
          failure_count: 0,
          opened_at: null,
        },
      },
    }))
  }

  return (
    <div className="min-h-screen bg-[#0b0c10] text-white font-sans-ui flex flex-col antialiased">
      {/* FinPoint Header Navigation */}
      <Header
        baseUrl={baseUrl}
        setBaseUrl={setBaseUrl}
        apiKey={apiKey}
        setApiKey={setApiKey}
        isLiveMode={!isMockData}
        isAutoRefresh={isAutoRefresh}
        setIsAutoRefresh={setIsAutoRefresh}
        refreshIntervalSecs={refreshIntervalSecs}
        setRefreshIntervalSecs={setRefreshIntervalSecs}
        onRefresh={loadData}
        isFetching={isFetching}
        isMockData={isMockData}
        lastUpdated={lastUpdated}
        onToggleMockMode={() => setIsMockData(!isMockData)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        breakerCount={Object.keys(stats.circuit_breakers).length}
        overview={stats.overview}
      />


      {/* Main Container Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="space-y-8 animate-in fade-in duration-200">
            <OverviewCards overview={stats.overview} audits={stats.recent_audits} />

            <div className="space-y-4 pt-2">
              <h3 className="text-lg font-bold text-white tracking-tight">
                Circuit Breakers & Provider Health
              </h3>
              <CircuitBreakerCards
                circuitBreakers={stats.circuit_breakers}
                onSimulateErrorSpike={handleSimulateErrorSpike}
                onResetBreaker={handleResetBreaker}
              />
            </div>

            <AuditLogTable audits={stats.recent_audits} />
          </div>
        )}

        {/* Tab 2: Config */}
        {activeTab === 'config' && (
          <div className="space-y-6 animate-in fade-in duration-200">
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Config Management & Hot-Reload
              </h2>
              <p className="text-xs text-zinc-400 mt-1">
                View active gateway configuration and trigger zero-downtime hot-reloads via POST /admin/reload.
              </p>
            </div>
            <ConfigPanel
              config={stats.config}
              baseUrl={baseUrl}
              apiKey={apiKey}
              onReloadSuccess={loadData}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 px-6 py-5 mt-auto text-xs text-zinc-500 bg-[#0e0f14]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 font-sans-ui">
          <span>PolyLLM Gateway Admin Dashboard © 2026</span>
          <div className="flex items-center gap-4 font-mono-code text-[11px]">
            <span>FastAPI Engine</span>
            <span>•</span>
            <span>Redis 7.4</span>
            <span>•</span>
            <span>React + Vite</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
