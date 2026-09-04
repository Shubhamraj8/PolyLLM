import React, { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'

interface DropdownOption {
  value: string
  label: string
}

interface DropdownProps {
  value: string
  onChange: (value: string) => void
  options: DropdownOption[]
  className?: string
  /** 'pill' = rounded-full compact, 'input' = rounded-xl taller (for settings) */
  variant?: 'pill' | 'input'
}

export const Dropdown: React.FC<DropdownProps> = ({
  value,
  onChange,
  options,
  className = '',
  variant = 'pill',
}) => {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const selected = options.find(o => o.value === value)

  const triggerClass =
    variant === 'pill'
      ? `flex items-center gap-1.5 bg-[#22242d] border border-white/10 rounded-full px-3 py-1.5 text-xs text-zinc-200 font-medium cursor-pointer hover:border-white/20 transition-colors select-none ${className}`
      : `flex items-center justify-between gap-2 bg-[#1c1e26] border border-white/10 rounded-xl px-3 py-2 text-xs text-zinc-100 font-medium cursor-pointer hover:border-white/20 transition-colors select-none w-full ${className}`

  return (
    <div ref={ref} className="relative">
      <div className={triggerClass} onClick={() => setOpen(o => !o)}>
        <span>{selected?.label ?? value}</span>
        <ChevronDown
          className={`w-3 h-3 text-zinc-400 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
        />
      </div>

      {open && (
        <div className="absolute z-50 mt-1.5 min-w-full right-0 bg-[#22242d] border border-white/10 rounded-xl shadow-2xl overflow-hidden animate-fade-in">
          {options.map(opt => (
            <div
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false) }}
              className={`px-3 py-2 text-xs cursor-pointer transition-colors font-medium whitespace-nowrap ${
                opt.value === value
                  ? 'bg-white/10 text-white'
                  : 'text-zinc-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
