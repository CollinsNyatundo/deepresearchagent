/**
 * Sidebar — thin container that wraps module-specific sidebar content.
 * Collapse/expand logic is owned by Layout.tsx (NavRail toggle).
 * This component is kept for backwards-compatible prop passing from modules.
 */
import { type ReactNode } from 'react'

interface SidebarProps {
  children: ReactNode
  /** @deprecated open/close is now controlled by NavRail in Layout.tsx */
  open?: boolean
  /** @deprecated */
  onClose?: () => void
}

export default function Sidebar({ children }: SidebarProps) {
  return (
    <div className="flex flex-col h-full">
      {children}
    </div>
  )
}
