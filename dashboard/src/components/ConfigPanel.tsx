import React, { useState } from 'react'
import {
  CheckCircle2,
  AlertCircle,
  FileCode,
  Play,
  Copy,
  Check,
  Bot,
  Sparkles,
  Zap,
  RotateCcw,
  Download,
} from 'lucide-react'
import { reloadConfig } from '../api'

interface ConfigPanelProps {
  config: Record<string, any>
  baseUrl: string
  apiKey: string
  onReloadSuccess: () => void
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({
  config,
  baseUrl,
  apiKey,
  onReloadSuccess,
}) => {
  const [isReloading, setIsReloading] = useState(false)
  const [reloadMsg, setReloadMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [copied, setCopied] = useState(false)
  const [promptText, setPromptText] = useState('')

  const handleHotReload = async () => {
    setIsReloading(true)
    setReloadMsg(null)
    try {
      const res = await reloadConfig(baseUrl, apiKey)
      setReloadMsg({
        type: 'success',
        text: `Gateway configuration hot-reloaded cleanly at ${new Date(res.timestamp).toLocaleTimeString()}`,
      })
      onReloadSuccess()
    } catch (err: any) {
      setReloadMsg({
        type: 'error',
        text: `Reload failed: ${err.message || 'Check gateway connection.'}`,
      })
    } finally {
      setIsReloading(false)
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(config, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 font-sans-ui">
      {/* Config Editor Window (7 Cols) */}
      <div className="lg:col-span-7 bg-[#181a20] border border-white/5 rounded-[24px] p-6 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <FileCode className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Runtime Gateway Configuration
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5 font-medium">
                Active parameters from <code className="font-mono-code text-white bg-white/5 px-1.5 py-0.5 rounded">config.yaml</code>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-4 py-2 rounded-2xl bg-[#22242d] hover:bg-white/10 border border-white/10 text-white text-xs font-semibold transition-all"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 text-zinc-400" />}
              <span>{copied ? 'Copied' : 'Copy JSON'}</span>
            </button>

            <button
              onClick={handleHotReload}
              disabled={isReloading}
              className="flex items-center gap-2 px-5 py-2 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
            >
              <Play className={`w-4 h-4 fill-current ${isReloading ? 'animate-spin' : ''}`} />
              <span>{isReloading ? 'Reloading...' : 'Hot-Reload Config'}</span>
            </button>
          </div>
        </div>

        {reloadMsg && (
          <div
            className={`p-3.5 rounded-2xl text-xs flex items-center gap-2 border font-medium ${
              reloadMsg.type === 'success'
                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
            }`}
          >
            {reloadMsg.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{reloadMsg.text}</span>
          </div>
        )}

        <div className="bg-[#101116] rounded-2xl p-5 border border-white/5 font-mono-code text-xs text-emerald-300 overflow-x-auto max-h-96">
          <pre>{JSON.stringify(config, null, 2)}</pre>
        </div>
      </div>

      {/* Resq.io Quick Action Assistance Box ("Hi, Developer 👋 How can I help you?") (5 Cols) */}
      <div className="lg:col-span-5 bg-[#181a20] border border-white/5 rounded-[24px] p-6 flex flex-col justify-between space-y-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Bot className="w-5 h-5 text-purple-400" />
            <h3 className="text-base font-bold text-white tracking-tight">
              Hi, Developer 👋
            </h3>
          </div>
          <p className="text-xs text-zinc-400 font-medium mb-4">
            How can I help you manage the PolyLLM Gateway today?
          </p>

          {/* Quick Action Grid (Matches Resq.io 4 Buttons) */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <button
              onClick={handleHotReload}
              className="p-3.5 rounded-2xl bg-[#22242d] hover:bg-[#2b2d37] border border-white/5 text-left text-zinc-200 font-semibold flex items-center gap-2 transition-all"
            >
              <Zap className="w-4 h-4 text-amber-400" />
              <span>Hot-Reload</span>
            </button>

            <button
              onClick={handleCopy}
              className="p-3.5 rounded-2xl bg-[#22242d] hover:bg-[#2b2d37] border border-white/5 text-left text-zinc-200 font-semibold flex items-center gap-2 transition-all"
            >
              <Copy className="w-4 h-4 text-blue-400" />
              <span>Copy Config</span>
            </button>

            <button
              onClick={onReloadSuccess}
              className="p-3.5 rounded-2xl bg-[#22242d] hover:bg-[#2b2d37] border border-white/5 text-left text-zinc-200 font-semibold flex items-center gap-2 transition-all"
            >
              <RotateCcw className="w-4 h-4 text-emerald-400" />
              <span>Sync Redis</span>
            </button>

            <button
              onClick={() => {
                const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'config.json'
                a.click()
              }}
              className="p-3.5 rounded-2xl bg-[#22242d] hover:bg-[#2b2d37] border border-white/5 text-left text-zinc-200 font-semibold flex items-center gap-2 transition-all"
            >
              <Download className="w-4 h-4 text-purple-400" />
              <span>Export Config</span>
            </button>
          </div>
        </div>

        {/* Bottom Resq.io Prompt Bar */}
        <div className="relative">
          <input
            type="text"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder="Ask something... ✦"
            className="w-full bg-[#22242d] border border-white/10 rounded-2xl px-4 py-3 text-xs text-white placeholder-zinc-500 focus:outline-none font-sans-ui pr-10"
          />
          <Sparkles className="w-4 h-4 text-purple-400 absolute right-3.5 top-3.5" />
        </div>
      </div>
    </div>
  )
}
