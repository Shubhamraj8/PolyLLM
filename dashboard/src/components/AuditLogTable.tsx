import React, { useState, useMemo } from 'react'
import { Search, Database, Download, Filter } from 'lucide-react'
import type { AuditEntry } from '../types'
import { Dropdown } from './Dropdown'

interface AuditLogTableProps {
  audits: AuditEntry[]
}

export const AuditLogTable: React.FC<AuditLogTableProps> = ({ audits }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterProvider, setFilterProvider] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<'all' | 'success' | 'error'>('all')
  const [sortCol, setSortCol] = useState<'timestamp' | 'latency' | 'tokens' | 'cost'>('timestamp')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [page, setPage] = useState(1)
  const perPage = 10

  const providers = useMemo(() => Array.from(new Set(audits.map(a => a.provider_used).filter(Boolean))), [audits])

  const handleSort = (col: typeof sortCol) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
    setPage(1)
  }

  const filtered = useMemo(() => {
    return audits
      .filter(log => {
        const q = searchTerm.toLowerCase()
        const matchSearch = !q ||
          (log.request_id || '').toLowerCase().includes(q) ||
          (log.model_requested || '').toLowerCase().includes(q) ||
          (log.provider_used || '').toLowerCase().includes(q) ||
          (log.ip || '').includes(q)
        const matchProvider = filterProvider === 'all' || log.provider_used === filterProvider
        const isSuccess = log.http_status >= 200 && log.http_status < 300
        const matchStatus =
          filterStatus === 'all' ||
          (filterStatus === 'success' && isSuccess) ||
          (filterStatus === 'error' && !isSuccess)
        return matchSearch && matchProvider && matchStatus
      })
      .sort((a, b) => {
        let av: number, bv: number
        switch (sortCol) {
          case 'latency':  av = a.latency_ms;           bv = b.latency_ms;           break
          case 'tokens':   av = a.total_tokens || 0;    bv = b.total_tokens || 0;    break
          case 'cost':     av = a.estimated_cost_usd || 0; bv = b.estimated_cost_usd || 0; break
          default:         av = new Date(a.timestamp || 0).getTime(); bv = new Date(b.timestamp || 0).getTime()
        }
        return sortDir === 'asc' ? av - bv : bv - av
      })
  }, [audits, searchTerm, filterProvider, filterStatus, sortCol, sortDir])

  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage))
  const paged = filtered.slice((page - 1) * perPage, page * perPage)

  const SortArrow = ({ col }: { col: typeof sortCol }) => (
    sortCol === col
      ? <span className="ml-1 text-indigo-400">{sortDir === 'asc' ? '↑' : '↓'}</span>
      : <span className="ml-1 text-zinc-600">↕</span>
  )

  const handleExport = () => {
    const csv = [
      ['Timestamp', 'Request ID', 'Model', 'Provider', 'Fallback', 'Latency (ms)', 'Tokens', 'Cost ($)', 'Status'].join(','),
      ...filtered.map(l => [
        l.timestamp, l.request_id, l.model_requested || l.model_used, l.provider_used,
        l.fallback_triggered ? 'Yes' : 'No', l.latency_ms, l.total_tokens || 0,
        (l.estimated_cost_usd || 0).toFixed(6), l.http_status
      ].join(','))
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `audit_log_${Date.now()}.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="finpoint-card p-5 space-y-4">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Database className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-white">Request Audit Trail</h3>
          <span className="text-[11px] text-zinc-500 font-mono-code">({filtered.length} records)</span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Provider filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-zinc-500" />
            <Dropdown
              value={filterProvider}
              onChange={val => { setFilterProvider(val); setPage(1) }}
              options={[
                { value: 'all', label: 'All Providers' },
                ...providers.map(p => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) }))
              ]}
              variant="pill"
              className="bg-[#1c1e26] border-white/[0.06] rounded-xl px-3 py-1.5"
            />
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-0.5 bg-[#1c1e26] border border-white/[0.06] rounded-xl p-1">
            {(['all', 'success', 'error'] as const).map(s => (
              <button
                key={s}
                onClick={() => { setFilterStatus(s); setPage(1) }}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  filterStatus === s
                    ? s === 'success' ? 'bg-emerald-500/20 text-emerald-300'
                      : s === 'error' ? 'bg-rose-500/20 text-rose-300'
                      : 'bg-[#2e3040] text-white'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2 text-zinc-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={e => { setSearchTerm(e.target.value); setPage(1) }}
              placeholder="Search requests..."
              className="bg-[#1c1e26] border border-white/[0.06] focus:border-indigo-500/40 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white focus:outline-none font-mono-code w-48"
            />
          </div>

          {/* Export CSV */}
          <button
            onClick={handleExport}
            title="Export filtered results as CSV"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1c1e26] border border-white/[0.06] text-zinc-400 hover:text-white text-xs font-medium transition-all hover:border-white/10 active:scale-95"
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>
        </div>
      </div>

      {/* ── Table ── */}
      <div className="overflow-x-auto rounded-xl border border-white/[0.05]">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/[0.05] text-zinc-500 bg-[#1c1e26]">
              <th className="py-3 px-4 font-medium">Timestamp</th>
              <th className="py-3 px-4 font-medium">Request ID</th>
              <th className="py-3 px-4 font-medium">Model</th>
              <th className="py-3 px-4 font-medium">Provider</th>
              <th className="py-3 px-4 font-medium">Fallback</th>
              <th className="py-3 px-4 font-medium cursor-pointer select-none hover:text-zinc-300 transition-colors" onClick={() => handleSort('latency')}>
                Latency<SortArrow col="latency" />
              </th>
              <th className="py-3 px-4 font-medium cursor-pointer select-none hover:text-zinc-300 transition-colors" onClick={() => handleSort('tokens')}>
                Tokens<SortArrow col="tokens" />
              </th>
              <th className="py-3 px-4 font-medium cursor-pointer select-none hover:text-zinc-300 transition-colors" onClick={() => handleSort('cost')}>
                Cost<SortArrow col="cost" />
              </th>
              <th className="py-3 px-4 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04] font-mono-code">
            {paged.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-10 text-center text-zinc-600 text-xs font-sans-ui">
                  No records match your filters.
                </td>
              </tr>
            ) : (
              paged.map((log, idx) => {
                const isSuccess = log.http_status >= 200 && log.http_status < 300
                return (
                  <tr key={log.request_id || idx} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="py-3 px-4 text-zinc-500 whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '—'}
                    </td>
                    <td className="py-3 px-4 font-medium text-zinc-200 whitespace-nowrap">
                      {log.request_id ? log.request_id.slice(0, 13) + '…' : 'anon'}
                    </td>
                    <td className="py-3 px-4 text-zinc-300 whitespace-nowrap">
                      {log.model_requested || log.model_used || 'default'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border ${
                        log.provider_used === 'groq'
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                          : 'bg-blue-500/10 text-blue-300 border-blue-500/20'
                      }`}>
                        {log.provider_used || '—'}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {log.fallback_triggered ? (
                        <span className="text-amber-300 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">Triggered</span>
                      ) : (
                        <span className="text-zinc-600 text-[10px]">Direct</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-zinc-200 whitespace-nowrap">{log.latency_ms}ms</td>
                    <td className="py-3 px-4 text-zinc-400 whitespace-nowrap">{(log.total_tokens || 0).toLocaleString()}</td>
                    <td className="py-3 px-4 text-emerald-400 font-semibold whitespace-nowrap">
                      ${(log.estimated_cost_usd || 0).toFixed(5)}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                        isSuccess
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                      }`}>
                        {log.http_status || 200}
                      </span>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-zinc-500">
            Page {page} of {totalPages} · {filtered.length} total records
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg bg-[#1c1e26] border border-white/[0.06] text-xs text-zinc-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              ← Prev
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const p = Math.max(1, Math.min(page - 2, totalPages - 4)) + i
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-8 h-8 rounded-lg text-xs font-medium transition-all ${
                    page === p
                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                      : 'bg-[#1c1e26] border border-white/[0.06] text-zinc-400 hover:text-white'
                  }`}
                >
                  {p}
                </button>
              )
            })}
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 rounded-lg bg-[#1c1e26] border border-white/[0.06] text-xs text-zinc-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
