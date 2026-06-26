import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../../lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md border border-white/[0.06] px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-[#c8956c] focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-white/[0.06] text-[#e0e0e0] hover:bg-white/[0.09]",
        secondary:
          "border-transparent bg-[#c8956c]/10 text-[#c8956c] hover:bg-[#c8956c]/20",
        destructive:
          "border-transparent bg-[#c45a5a]/10 text-[#c45a5a] hover:bg-[#c45a5a]/20",
        outline: "text-[#e0e0e0]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
