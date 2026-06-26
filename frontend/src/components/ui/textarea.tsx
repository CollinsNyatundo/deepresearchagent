import * as React from "react"
import { cn } from "../../lib/utils"

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[60px] w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-sm text-[#e0e0e0] shadow-sm placeholder:text-[#555] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#c8956c] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = "Textarea"

export { Textarea }
