import { type ReactNode } from 'react'

interface SidebarProps {
  children: ReactNode
  open?: boolean
  onClose?: () => void
}

export default function Sidebar({ children, open = true, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-20"
          onClick={onClose}
        />
      )}
      <aside
        className={`flex-shrink-0 liquid-glass overflow-hidden flex flex-col z-30 relative transition-all duration-200
          ${open
            ? 'w-[15rem] translate-x-0'
            : 'w-0 -translate-x-full lg:w-[15rem] lg:translate-x-0'
          }`}
      >
        <div className="w-[15rem] h-full">{children}</div>
      </aside>
    </>
  )
}
