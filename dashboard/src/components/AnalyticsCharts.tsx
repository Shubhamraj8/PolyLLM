import React, { useState } from 'react'
import type { AuditEntry, CostBreakdown } from '../types'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts'
import { BarChart2, ArrowUpRight } from 'lucide-react'

interface AnalyticsChartsProps {
  audits: AuditEntry[]
  costBreakdown: CostBreakdown
}

const RADIAN = Math.PI / 180
const renderLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return percent > 0.05 ? (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  ) : null
}

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({ audits, costBreakdown }) => {
  const [hoveredSegment, setHoveredSegment] = useState<string | null>(null)

  const chartData = audits.slice(-20).map((a, i) => ({
    name: `#${i + 1}`,
    latency: a.latency_ms,
    tokens: a.total_tokens || 0,
    cost: (a.estimated_cost_usd || 0) * 10000,
  }))

  const donutData = [
    { name: 'Gemini', value: Math.max(costBreakdown.gemini_usd || 0, 0.001), color: '#fa256d' },
    { name: 'Groq',   value: Math.max(costBreakdown.groq_usd || 0, 0.001),  color: '#3b82f6' },
  ].filter(d => d.value > 0)

  const totalCost = donutData.reduce((s, d) => s + d.value, 0)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
      {/* Latency Chart — 8 cols */}
      <div className="lg:col-span-8 finpoint-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">Request Latency (ms)</h3>
          </div>
          <span className="text-[11px] text-zinc-500 font-mono-code">Last {chartData.length} requests</span>
        </div>

        <div className="h-56">
          {chartData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-zinc-500 text-xs">No latency data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="latFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#3f4050" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#3f4050" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#22242d', borderColor: 'rgba(255,255,255,0.08)', borderRadius: '12px', fontSize: '11px', color: '#fff' }}
                  formatter={(v: any) => [`${v}ms`, 'Latency']}
                />
                <Area type="monotone" dataKey="latency" stroke="#10b981" strokeWidth={2.5} fillOpacity={1} fill="url(#latFill)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-3 pt-3 border-t border-white/[0.05]">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400">
            <span className="w-3 h-0.5 rounded-full bg-emerald-400 inline-block" /> Latency (ms)
          </div>
        </div>
      </div>

      {/* Routing Distribution Donut — 4 cols */}
      <div className="lg:col-span-4 finpoint-card p-5 flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-white">Routing Distribution</h3>
          <button className="w-7 h-7 rounded-full bg-[#22242d] border border-white/5 flex items-center justify-center text-zinc-400 hover:text-white transition-colors">
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex-1 flex items-center justify-center relative">
          <div className="w-full h-44 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%"
                  cy="50%"
                  innerRadius={48}
                  outerRadius={70}
                  paddingAngle={4}
                  dataKey="value"
                  labelLine={false}
                  label={renderLabel}
                  onMouseEnter={(_: any, i: number) => setHoveredSegment(donutData[i]?.name || null)}
                  onMouseLeave={() => setHoveredSegment(null)}
                >
                  {donutData.map((d, i) => (
                    <Cell
                      key={i}
                      fill={d.color}
                      opacity={hoveredSegment && hoveredSegment !== d.name ? 0.5 : 1}
                      style={{ cursor: 'pointer', transition: 'opacity 0.2s' }}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#22242d', borderColor: 'rgba(255,255,255,0.08)', borderRadius: '12px', fontSize: '11px', color: '#fff' }}
                  formatter={(v: any, name: any) => [`$${Number(v).toFixed(5)}`, String(name)]}
                />
              </PieChart>
            </ResponsiveContainer>

            {/* Center label */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xl font-bold text-white">${totalCost.toFixed(4)}</span>
              <span className="text-[10px] text-zinc-500">Total cost</span>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 gap-2 pt-3 border-t border-white/[0.05]">
          {donutData.map(d => (
            <div key={d.name} className="flex items-center gap-2 p-2 rounded-xl bg-[#22242d]">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
              <div>
                <div className="text-[10px] text-zinc-400 font-medium">{d.name}</div>
                <div className="text-xs font-semibold text-white">${d.value.toFixed(5)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
